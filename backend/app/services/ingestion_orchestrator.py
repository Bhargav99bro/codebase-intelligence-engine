import asyncio
import collections
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select

from app.analyzers import analyzer_registry
from app.analyzers.base import ExtractedSymbol
from app.core.database import AsyncSessionLocal
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.dependency import Dependency, FileDependencyMetric
from app.models.duplication import CodeDuplicate, GitChurnMetric
from app.models.file import RepositoryFile
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.models.metrics import FileMetric, SymbolMetric
from app.models.repository import Repository
from app.models.symbol import Symbol
from app.dependencies.extractors import JsTsDependencyExtractor, PythonDependencyExtractor
from app.dependencies.resolvers import JsTsDependencyResolver, PythonDependencyResolver
from app.dependencies.graph import DirectedDependencyGraph
from app.health import HealthCalculator, RecommendationEngine
from app.metrics import metrics_registry
from app.metrics.aggregates import calculate_repository_metrics
from app.metrics.base import FileMetrics
from app.rules import RuleContext, RulesEngine
from app.services.cancellation_manager import AnalysisCancelledException, check_checkpoint
from app.services.clone_detector import CloneDetector
from app.services.cloner import ClonedRepository, clone_repository
from app.services.event_streamer import publish_pipeline_event
from app.services.file_discovery import discover_files
from app.services.git_churn import GitChurnAnalyzer
from app.services.quality_gate_engine import QualityGateEngine
from app.services.url_validator import validate_and_normalize_github_url

logger = logging.getLogger(__name__)


async def execute_ingestion_pipeline(analysis_id_str: str) -> None:
    """Executes the full repository ingestion and code structure analysis pipeline."""
    analysis_uuid = uuid.UUID(analysis_id_str)
    cloned_repo: Optional[ClonedRepository] = None

    async with AsyncSessionLocal() as session:
        # Fetch analysis job and its associated repository
        stmt = select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            logger.error("Analysis job %s not found in database.", analysis_id_str)
            return

        repo_stmt = select(Repository).where(Repository.id == job.repository_id)
        repo_res = await session.execute(repo_stmt)
        repository = repo_res.scalar_one_or_none()

        if not repository:
            logger.error("Associated repository for analysis job %s not found.", analysis_id_str)
            job.status = AnalysisStatus.FAILED.value
            job.stage = "failed"
            job.error_message = "Associated repository record not found."
            await session.commit()
            return

        try:
            # Checkpoint 1: Initial check
            check_checkpoint(analysis_id_str, "cloning")

            # Stage 1: Validate & clone
            job.status = AnalysisStatus.CLONING.value
            job.stage = "cloning"
            job.progress = 15
            job.message = f"Cloning repository {repository.owner}/{repository.name}..."
            job.started_at = datetime.now(timezone.utc)
            await session.commit()
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            validated_url = validate_and_normalize_github_url(repository.url)
            cloned_repo = clone_repository(validated_url)

            # Checkpoint 2: After cloning
            check_checkpoint(analysis_id_str, "file_discovery")

            # Update Git metadata
            job.commit_hash = cloned_repo.commit_hash
            job.commit_message = cloned_repo.commit_message
            job.commit_author = cloned_repo.commit_author
            job.commit_date = cloned_repo.commit_date
            job.metadata_json = {
                "branch": cloned_repo.default_branch,
                "commit_hash": cloned_repo.commit_hash,
                "commit_author": cloned_repo.commit_author,
                "commit_date": cloned_repo.commit_date.isoformat() if cloned_repo.commit_date else None,
            }
            if cloned_repo.default_branch and cloned_repo.default_branch != repository.default_branch:
                repository.default_branch = cloned_repo.default_branch

            # Stage 2: File discovery
            job.status = AnalysisStatus.DISCOVERING.value
            job.stage = "file_discovery"
            job.progress = 30
            job.message = "Scanning workspace and detecting programming languages..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            discovery_result = discover_files(cloned_repo.temp_dir)

            # Checkpoint 3: Before parsing
            check_checkpoint(analysis_id_str, "parsing")

            # Stage 3: Code Parsing
            job.status = AnalysisStatus.PARSING.value
            job.stage = "parsing"
            job.progress = 45
            job.message = f"Initializing static parsers for {discovery_result.analyzable_files} source files..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            # Stage 4: Symbol Extraction
            job.status = AnalysisStatus.EXTRACTING_SYMBOLS.value
            job.stage = "extracting_symbols"
            job.progress = 60
            job.message = "Extracting AST symbols, functions, classes, imports, and exports..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            parsed_files_data = []
            symbol_distribution: Dict[str, int] = collections.defaultdict(int)
            total_symbols_count = 0

            for df in discovery_result.files:
                analyzer = analyzer_registry.get_analyzer_for_file(df.path, df.language)
                file_full_path = os.path.join(cloned_repo.temp_dir, df.path)
                file_content: Optional[str] = None
                ast_tree: Any = None

                if not df.is_analyzable or analyzer is None:
                    parser_status = "unsupported"
                    parser_error = None
                    file_symbols: List[ExtractedSymbol] = []
                else:
                    try:
                        # Safely read file content
                        with open(file_full_path, "r", encoding="utf-8", errors="replace") as f:
                            file_content = f.read()

                        analysis_res = analyzer.analyze(df.path, file_content)
                        parser_status = analysis_res.parser_status
                        parser_error = analysis_res.parser_error
                        file_symbols = analysis_res.symbols
                        ast_tree = getattr(analysis_res, "ast_tree", None)

                    except Exception as parse_exc:
                        # Strict error isolation: single file error must never abort overall analysis
                        logger.warning("Failed to analyze file %s: %s", df.path, parse_exc)
                        parser_status = "failed"
                        parser_error = str(parse_exc)
                        file_symbols = []
                        ast_tree = None

                # Tally symbols
                for sym in file_symbols:
                    symbol_distribution[sym.symbol_type] += 1
                total_symbols_count += len(file_symbols)

                parsed_files_data.append({
                    "df": df,
                    "content": file_content,
                    "parser_status": parser_status,
                    "parser_error": parser_error,
                    "symbol_count": len(file_symbols),
                    "symbols": file_symbols,
                    "ast_tree": ast_tree,
                })

            # Milestone commit after symbol extraction
            job.total_symbols = total_symbols_count
            await session.commit()

            # Checkpoint 4: Before metrics calculation
            check_checkpoint(analysis_id_str, "calculating_metrics")

            # Stage 5: Code Complexity & Quality Analysis
            job.status = AnalysisStatus.CALCULATING_METRICS.value
            job.stage = "calculating_metrics"
            job.progress = 80
            job.message = "Calculating cyclomatic complexity, nesting depth, and quality metrics..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            file_metrics_map: Dict[str, FileMetrics] = {}
            for item in parsed_files_data:
                df = item["df"]
                content = item.get("content")
                file_symbols = item["symbols"]
                m_analyzer = metrics_registry.get_metrics_analyzer_for_file(df.path, df.language)

                if not df.is_analyzable or m_analyzer is None or content is None:
                    fm = FileMetrics(
                        file_path=df.path,
                        language=df.language,
                        total_lines=df.line_count or 0,
                        sloc=df.line_count or 0,
                        symbol_count=len(file_symbols),
                        metric_status="unsupported",
                    )
                else:
                    try:
                        fm = m_analyzer.calculate(df.path, content, file_symbols, ast_tree=item.get("ast_tree"))
                    except Exception as m_exc:
                        logger.warning("Failed to calculate metrics for %s: %s", df.path, m_exc)
                        fm = FileMetrics(
                            file_path=df.path,
                            language=df.language,
                            total_lines=df.line_count or 0,
                            sloc=df.line_count or 0,
                            symbol_count=len(file_symbols),
                            metric_status="failed",
                            metric_error=str(m_exc),
                        )

                file_metrics_map[df.path] = fm

            # Repository-wide summary metrics aggregation
            summary_metrics = calculate_repository_metrics(list(file_metrics_map.values()))

            # Pre-assign file IDs so dependency resolvers can map imports to target file IDs
            file_id_map: Dict[str, uuid.UUID] = {
                item["df"].path: uuid.uuid4() for item in parsed_files_data
            }

            # Checkpoint 5: Before dependency analysis
            check_checkpoint(analysis_id_str, "analyzing_dependencies")

            # Stage 6: Dependency & Architecture Analysis
            job.status = AnalysisStatus.ANALYZING_DEPENDENCIES.value
            job.stage = "analyzing_dependencies"
            job.progress = 88
            job.message = "Analyzing dependencies, architecture coupling, and circular imports..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            py_extractor = PythonDependencyExtractor()
            py_resolver = PythonDependencyResolver(file_id_map)
            jsts_extractor = JsTsDependencyExtractor()
            jsts_resolver = JsTsDependencyResolver(file_id_map)
            graph = DirectedDependencyGraph()

            for item in parsed_files_data:
                df = item["df"]
                fid = file_id_map[df.path]
                graph.add_file_node(fid, df.path, df.language)

            all_resolved_dependencies = []
            for item in parsed_files_data:
                df = item["df"]
                content = item.get("content")
                fid = file_id_map[df.path]
                if not df.is_analyzable or content is None:
                    continue

                lang = (df.language or "").lower()
                try:
                    ast_tree = item.get("ast_tree")
                    if lang == "python":
                        raw_deps = py_extractor.extract(df.path, content, ast_tree=ast_tree)
                        for raw in raw_deps:
                            resolved = py_resolver.resolve(raw, source_file_id=fid)
                            all_resolved_dependencies.append(resolved)
                            graph.process_resolved_dependency(resolved)
                    elif lang in ("javascript", "typescript"):
                        raw_deps = jsts_extractor.extract(df.path, content, ast_tree=ast_tree)
                        for raw in raw_deps:
                            resolved = jsts_resolver.resolve(raw, source_file_id=fid)
                            all_resolved_dependencies.append(resolved)
                            graph.process_resolved_dependency(resolved)
                except Exception as dep_exc:
                    logger.warning("Dependency extraction error on %s: %s", df.path, dep_exc)

            graph.compute_metrics()
            graph.detect_cycles(max_cycles=100)
            dependency_summary = graph.get_summary_metrics()

            # Checkpoint 6a: Git Churn Analysis
            check_checkpoint(analysis_id_str, "analyzing_git_churn")

            # Stage 6a: Git Churn Analysis
            job.status = AnalysisStatus.ANALYZING_GIT_CHURN.value
            job.stage = "analyzing_git_churn"
            job.progress = 85
            job.message = "Analyzing git commit churn, author distribution, and code change history..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            churn_analyzer = GitChurnAnalyzer()
            repo_temp_path = cloned_repo.temp_dir if cloned_repo else ""
            churn_result = churn_analyzer.analyze_churn(repo_temp_path)

            # Checkpoint 6b: Code Duplication Detection
            check_checkpoint(analysis_id_str, "detecting_duplication")

            # Stage 6b: Code Duplication Detection
            job.status = AnalysisStatus.DETECTING_DUPLICATION.value
            job.stage = "detecting_duplication"
            job.progress = 90
            job.message = "Detecting Type-1 and Type-2 code clones and computing duplication ratios..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            files_content_map = {
                item["df"].path: item["content"]
                for item in parsed_files_data
                if item.get("content") is not None and item["df"].is_analyzable
            }
            total_sloc = sum(fm.sloc for fm in file_metrics_map.values())
            clone_detector = CloneDetector()
            duplication_result = clone_detector.detect_clones(files_content_map, total_sloc=total_sloc)

            # Checkpoint 7: Before health & quality gate evaluation
            check_checkpoint(analysis_id_str, "evaluating_health")

            # Stage 7: Diagnostic Rules, Health Evaluation & Quality Gate
            job.status = AnalysisStatus.EVALUATING_HEALTH.value
            job.stage = "evaluating_health"
            job.progress = 94
            job.message = "Evaluating diagnostic rules, architectural anti-patterns, and health score..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            rule_context = RuleContext(
                parsed_files_data=parsed_files_data,
                file_metrics_map=file_metrics_map,
                graph=graph,
                file_id_map=file_id_map,
                code_duplicates=duplication_result.duplicates,
            )
            rules_engine = RulesEngine()
            detected_issues = rules_engine.run(rule_context)

            health_calculator = HealthCalculator()
            health_breakdown = health_calculator.compute(
                file_metrics_map=file_metrics_map,
                parsed_files_data=parsed_files_data,
                graph=graph,
                issues=detected_issues,
                duplication_ratio=duplication_result.duplication_ratio,
                duplicate_blocks_count=duplication_result.duplicate_blocks_count,
                duplicate_lines_count=duplication_result.duplicate_lines_count,
            )

            rec_engine = RecommendationEngine(health_calculator)
            recommendations = rec_engine.generate_recommendations(
                current_health=health_breakdown,
                file_metrics_map=file_metrics_map,
                parsed_files_data=parsed_files_data,
                graph=graph,
                issues=detected_issues,
                max_recommendations=5,
            )
            recommendations_data = [r.to_dict() for r in recommendations]

            # Quality Gate Evaluation
            avg_mi = summary_metrics.get("average_maintainability_score", 100.0) if summary_metrics else 100.0
            crit_func_count = sum(
                1 for fm in file_metrics_map.values() for sm in fm.symbols_metrics if sm.cyclomatic_complexity >= 20
            )
            qg_result = QualityGateEngine.evaluate(
                overall_score=health_breakdown.overall_score,
                blocker_count=health_breakdown.blocker_count,
                critical_count=health_breakdown.critical_count,
                circular_dependencies_count=len(graph.cycles) if graph else 0,
                average_maintainability_index=avg_mi,
                critical_complexity_functions_count=crit_func_count,
            )
            job.quality_gate_status = qg_result.status
            job.quality_gate_details = qg_result.to_dict()

            # Release raw content, AST trees, and clone detector data before heavy database persistence
            for item in parsed_files_data:
                item["content"] = None
                item["ast_tree"] = None
            files_content_map.clear()
            del clone_detector
            import gc
            gc.collect()

            # Checkpoint 7: Before database persistence
            check_checkpoint(analysis_id_str, "persisting")

            # Stage 8: Batch Persist
            job.status = AnalysisStatus.PERSISTING.value
            job.stage = "persisting"
            job.progress = 97
            job.message = f"Persisting {len(parsed_files_data)} files, {total_symbols_count} symbols, metrics, dependencies, and health score..."
            publish_pipeline_event(analysis_id_str, "stage", {"status": job.status, "stage": job.stage, "progress": job.progress, "message": job.message})

            files_to_insert: List[RepositoryFile] = []
            symbols_to_insert: List[Symbol] = []
            file_metrics_to_insert: List[FileMetric] = []
            symbol_metrics_to_insert: List[SymbolMetric] = []
            dependencies_to_insert: List[Dependency] = []
            file_dep_metrics_to_insert: List[FileDependencyMetric] = []
            issues_to_insert: List[AnalysisIssue] = []
            seen_metric_symbol_ids: set[uuid.UUID] = set()

            for iss in detected_issues:
                issues_to_insert.append(
                    AnalysisIssue(
                        id=iss.id,
                        analysis_id=job.id,
                        file_id=iss.file_id,
                        rule_id=iss.rule_id,
                        rule_name=iss.rule_name,
                        category=iss.category,
                        severity=iss.severity,
                        title=iss.title,
                        description=iss.description,
                        line_number=iss.line_number,
                        end_line_number=iss.end_line_number,
                        symbol_name=iss.symbol_name,
                        remediation_effort_minutes=iss.remediation_effort_minutes,
                        metadata_json=iss.metadata_json,
                    )
                )

            health_score_db = AnalysisHealthScore(
                id=uuid.uuid4(),
                analysis_id=job.id,
                overall_score=health_breakdown.overall_score,
                grade=health_breakdown.grade,
                maintainability_score=health_breakdown.maintainability_score,
                complexity_score=health_breakdown.complexity_score,
                architecture_score=health_breakdown.architecture_score,
                hygiene_score=health_breakdown.hygiene_score,
                duplication_score=health_breakdown.duplication_score,
                duplication_ratio=health_breakdown.duplication_ratio,
                duplicate_blocks_count=health_breakdown.duplicate_blocks_count,
                duplicate_lines_count=health_breakdown.duplicate_lines_count,
                technical_debt_minutes=health_breakdown.technical_debt_minutes,
                debt_ratio_hours_per_ksloc=health_breakdown.debt_ratio_hours_per_ksloc,
                total_issues_count=health_breakdown.total_issues_count,
                blocker_count=health_breakdown.blocker_count,
                critical_count=health_breakdown.critical_count,
                major_count=health_breakdown.major_count,
                minor_count=health_breakdown.minor_count,
                info_count=health_breakdown.info_count,
                category_scores_json=health_breakdown.category_scores,
                recommendations_json=recommendations_data,
            )

            # Prepare dependencies to insert with deduplication
            seen_dep_keys = set()
            for r in all_resolved_dependencies:
                dep_key = (job.id, r.source_file_id, r.target_module, r.line_number)
                if dep_key not in seen_dep_keys:
                    seen_dep_keys.add(dep_key)
                    dependencies_to_insert.append(
                        Dependency(
                            id=uuid.uuid4(),
                            analysis_id=job.id,
                            source_file_id=r.source_file_id,
                            target_file_id=r.target_file_id,
                            target_module=r.target_module,
                            dependency_type=r.dependency_type,
                            imported_symbols=r.imported_symbols,
                            line_number=r.line_number,
                            resolution_status=r.resolution_status,
                            is_type_only=r.is_type_only,
                        )
                    )

            # Prepare file dependency metrics to insert
            for fid, gnode in graph.nodes.items():
                file_dep_metrics_to_insert.append(
                    FileDependencyMetric(
                        id=uuid.uuid4(),
                        analysis_id=job.id,
                        file_id=fid,
                        fan_in=gnode.fan_in,
                        fan_out=gnode.fan_out,
                        internal_dependencies_count=gnode.internal_dependencies_count,
                        external_dependencies_count=gnode.external_dependencies_count,
                        unresolved_dependencies_count=gnode.unresolved_dependencies_count,
                        instability=gnode.instability,
                        in_cycle=gnode.in_cycle,
                        cycle_count=gnode.cycle_count,
                    )
                )

            for item in parsed_files_data:
                df = item["df"]
                file_id = file_id_map[df.path]
                rf = RepositoryFile(
                    id=file_id,
                    analysis_id=job.id,
                    path=df.path,
                    filename=df.filename,
                    extension=df.extension,
                    language=df.language,
                    size_bytes=df.size_bytes,
                    line_count=df.line_count,
                    is_analyzable=df.is_analyzable,
                    parser_status=item["parser_status"],
                    parser_error=item["parser_error"],
                    symbol_count=item["symbol_count"],
                )
                files_to_insert.append(rf)

                # Persist FileMetric
                fm = file_metrics_map[df.path]
                fm_db = FileMetric(
                    id=uuid.uuid4(),
                    analysis_id=job.id,
                    file_id=file_id,
                    total_lines=fm.total_lines,
                    sloc=fm.sloc,
                    comment_lines=fm.comment_lines,
                    blank_lines=fm.blank_lines,
                    statement_count=fm.statement_count,
                    symbol_count=fm.symbol_count,
                    function_count=fm.function_count,
                    class_count=fm.class_count,
                    method_count=fm.method_count,
                    import_count=fm.import_count,
                    export_count=fm.export_count,
                    max_nesting_depth=fm.max_nesting_depth,
                    average_nesting_depth=fm.average_nesting_depth,
                    total_cyclomatic_complexity=fm.total_cyclomatic_complexity,
                    average_cyclomatic_complexity=fm.average_cyclomatic_complexity,
                    max_cyclomatic_complexity=fm.max_cyclomatic_complexity,
                    maintainability_score=fm.maintainability_score,
                    metric_status=fm.metric_status,
                    metric_error=fm.metric_error,
                    quality_flags=fm.quality_flags,
                )
                file_metrics_to_insert.append(fm_db)

                # First pass for symbols: create IDs and build name -> id map for parent resolution
                file_symbols = item["symbols"]
                parent_map: Dict[str, uuid.UUID] = {}
                pending_symbols = []

                for sym in file_symbols:
                    sym_id = uuid.uuid4()
                    if sym.symbol_type in ("class", "function", "interface"):
                        parent_map[sym.name] = sym_id
                    pending_symbols.append((sym_id, sym))

                for sym_id, sym in pending_symbols:
                    parent_id = parent_map.get(sym.parent_name) if sym.parent_name else None
                    db_sym = Symbol(
                        id=sym_id,
                        analysis_id=job.id,
                        file_id=file_id,
                        name=sym.name,
                        symbol_type=sym.symbol_type,
                        qualified_name=sym.qualified_name,
                        start_line=sym.start_line,
                        start_column=sym.start_column,
                        end_line=sym.end_line,
                        end_column=sym.end_column,
                        parent_symbol_id=parent_id,
                        signature=sym.signature,
                        metadata_json=sym.metadata_json,
                    )
                    symbols_to_insert.append(db_sym)

                # Correlate and link SymbolMetric records ensuring 1:1 uniqueness
                eligible_symbols = [
                    (sym_id, sym)
                    for sym_id, sym in pending_symbols
                    if sym.symbol_type in ("function", "method")
                ]
                sym_by_exact = {
                    (sym.name, sym.start_line): sym_id
                    for sym_id, sym in eligible_symbols
                }

                for sm in fm.symbols_metrics:
                    matched_sym_id: Optional[uuid.UUID] = None

                    # 1. Exact match on name and start_line
                    exact_id = sym_by_exact.get((sm.name, sm.start_line))
                    if exact_id and exact_id not in seen_metric_symbol_ids:
                        matched_sym_id = exact_id
                    else:
                        # 2. Proximity match for same name within +/- 5 lines (e.g. decorators)
                        candidates = [
                            (sym_id, sym)
                            for sym_id, sym in eligible_symbols
                            if sym.name == sm.name and sym_id not in seen_metric_symbol_ids
                        ]
                        if candidates:
                            candidates.sort(key=lambda c: abs(c[1].start_line - sm.start_line))
                            best_sym_id, best_sym = candidates[0]
                            if abs(best_sym.start_line - sm.start_line) <= 5 or len(candidates) == 1:
                                matched_sym_id = best_sym_id

                    if matched_sym_id and matched_sym_id not in seen_metric_symbol_ids:
                        seen_metric_symbol_ids.add(matched_sym_id)
                        sm_db = SymbolMetric(
                            id=uuid.uuid4(),
                            symbol_id=matched_sym_id,
                            analysis_id=job.id,
                            file_id=file_id,
                            lines_of_code=sm.lines_of_code,
                            cyclomatic_complexity=sm.cyclomatic_complexity,
                            nesting_depth=sm.nesting_depth,
                            parameter_count=sm.parameter_count,
                            return_count=sm.return_count,
                            branch_count=sm.branch_count,
                            loop_count=sm.loop_count,
                            exception_handler_count=sm.exception_handler_count,
                            boolean_condition_count=sm.boolean_condition_count,
                            quality_flags=sm.quality_flags,
                            metric_status=sm.metric_status,
                            metric_error=sm.metric_error,
                        )
                        symbol_metrics_to_insert.append(sm_db)

            # Insert files
            session.add_all(files_to_insert)
            await session.flush()

            # Topological layered insert for self-referencing parent_symbol_id foreign key
            inserted_ids = set()
            remaining = list(symbols_to_insert)
            while remaining:
                batch = [s for s in remaining if s.parent_symbol_id is None or s.parent_symbol_id in inserted_ids]
                if not batch:
                    # Fallback for circular or missing parents: clear parent_symbol_id to prevent FK violation
                    for s in remaining:
                        s.parent_symbol_id = None
                    batch = remaining

                session.add_all(batch)
                await session.flush()
                inserted_ids.update(s.id for s in batch)
                remaining = [s for s in remaining if s.id not in inserted_ids]

            # Insert file_metrics and symbol_metrics
            session.add_all(file_metrics_to_insert)
            session.add_all(symbol_metrics_to_insert)

            # Insert dependencies and file_dependency_metrics
            session.add_all(dependencies_to_insert)
            session.add_all(file_dep_metrics_to_insert)

            # Insert issues and health_score
            session.add_all(issues_to_insert)
            session.add(health_score_db)

            # Insert code duplicates
            duplicates_to_insert: List[CodeDuplicate] = []
            for d in duplication_result.duplicates:
                src_fid = file_id_map.get(d.source_file_path)
                tgt_fid = file_id_map.get(d.target_file_path)
                duplicates_to_insert.append(
                    CodeDuplicate(
                        id=uuid.uuid4(),
                        analysis_id=job.id,
                        source_file_id=src_fid,
                        target_file_id=tgt_fid,
                        source_file_path=d.source_file_path,
                        target_file_path=d.target_file_path,
                        clone_type="TYPE_1" if d.clone_type == 1 else "TYPE_2",
                        line_count=d.line_count,
                        token_count=d.token_count,
                        source_start_line=d.source_start_line,
                        source_end_line=d.source_end_line,
                        target_start_line=d.target_start_line,
                        target_end_line=d.target_end_line,
                        similarity_score=1.0 if d.clone_type == 1 else 0.85,
                        fragment_hash=d.checksum,
                    )
                )
            session.add_all(duplicates_to_insert)

            # Insert git churn metrics
            churn_metrics_to_insert: List[GitChurnMetric] = []
            for fpath, cm in churn_result.metrics.items():
                fid = file_id_map.get(fpath)
                churn_metrics_to_insert.append(
                    GitChurnMetric(
                        id=uuid.uuid4(),
                        analysis_id=job.id,
                        file_id=fid,
                        file_path=fpath,
                        commit_count=cm.commit_count,
                        insertions=cm.added_lines,
                        deletions=cm.deleted_lines,
                        author_count=cm.author_count,
                        churn_score=cm.relative_churn,
                    )
                )
            session.add_all(churn_metrics_to_insert)

            # Finalize job metrics
            job.status = AnalysisStatus.COMPLETED.value
            job.stage = "completed"
            job.progress = 100
            job.health_summary = {
                "overall_score": health_breakdown.overall_score,
                "grade": health_breakdown.grade,
                "maintainability_score": health_breakdown.maintainability_score,
                "complexity_score": health_breakdown.complexity_score,
                "architecture_score": health_breakdown.architecture_score,
                "hygiene_score": health_breakdown.hygiene_score,
                "duplication_score": health_breakdown.duplication_score,
                "duplication_ratio": health_breakdown.duplication_ratio,
                "duplicate_blocks_count": health_breakdown.duplicate_blocks_count,
                "duplicate_lines_count": health_breakdown.duplicate_lines_count,
                "total_issues_count": health_breakdown.total_issues_count,
                "technical_debt_minutes": health_breakdown.technical_debt_minutes,
            }
            job.message = (
                f"Analysis complete: {discovery_result.total_files} files "
                f"({discovery_result.analyzable_files} analyzable), "
                f"{total_symbols_count} symbols, {len(symbol_metrics_to_insert)} function metrics, "
                f"{len(dependencies_to_insert)} dependencies, {len(issues_to_insert)} issues, "
                f"health score {health_breakdown.overall_score:.1f} ({health_breakdown.grade})"
            )
            job.total_files = discovery_result.total_files
            job.analyzable_files = discovery_result.analyzable_files
            job.total_lines = discovery_result.total_lines
            job.total_bytes = discovery_result.total_bytes
            job.language_distribution = discovery_result.language_distribution
            job.total_symbols = total_symbols_count
            job.symbol_distribution = dict(symbol_distribution)
            job.summary_metrics = summary_metrics
            job.dependency_summary = dependency_summary
            job.completed_at = datetime.now(timezone.utc)

            await session.commit()
            publish_pipeline_event(
                analysis_id_str,
                "complete",
                {
                    "status": "completed",
                    "overall_score": health_breakdown.overall_score,
                    "grade": health_breakdown.grade,
                    "quality_gate_status": qg_result.status,
                    "total_files": discovery_result.total_files,
                    "total_symbols": total_symbols_count,
                    "total_issues": len(issues_to_insert),
                    "message": job.message,
                },
            )
            logger.info(
                "Successfully analyzed repository %s: %d files, %d symbols (analysis %s)",
                repository.url,
                discovery_result.total_files,
                total_symbols_count,
                analysis_id_str,
            )

        except AnalysisCancelledException as cancel_exc:
            logger.info("Analysis %s was cancelled: %s", analysis_id_str, cancel_exc)
            await session.rollback()
            job.status = AnalysisStatus.CANCELLED.value
            job.stage = "cancelled"
            job.is_cancelled = True
            job.message = "Analysis cancelled by user."
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            publish_pipeline_event(
                analysis_id_str,
                "cancelled",
                {"status": "cancelled", "message": "Analysis cancelled by user."},
            )

        except Exception as exc:
            logger.exception("Failed to analyze repository for analysis %s: %s", analysis_id_str, exc)
            await session.rollback()
            job.status = AnalysisStatus.FAILED.value
            job.stage = "failed"
            job.error_message = str(exc)
            job.message = f"Analysis failed: {exc}"[:1000]
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            publish_pipeline_event(
                analysis_id_str,
                "error",
                {"status": "failed", "error": str(exc)},
            )

        finally:
            # Stage 7: Guaranteed workspace cleanup
            if cloned_repo:
                cloned_repo.cleanup()


async def _run_with_engine_cleanup(analysis_id: str) -> None:
    from app.core.database import async_engine
    try:
        await execute_ingestion_pipeline(analysis_id)
    finally:
        await async_engine.dispose()


def run_ingestion_pipeline(analysis_id: str) -> None:
    """Synchronous entrypoint called by Celery workers."""
    asyncio.run(_run_with_engine_cleanup(analysis_id))

