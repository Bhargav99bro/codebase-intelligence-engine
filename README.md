# Codebase Intelligence Engine

> A **production-hardened deterministic codebase intelligence platform** that analyzes software repositories and delivers actionable engineering intelligence through concrete AST parsing, dependency graph synthesis, code hotspots, and transparent software health scoring.

[![Tests: 229 Passed](https://img.shields.io/badge/Tests-229%2F229%20Passed-brightgreen.svg)](./)
[![Frontend: TypeScript Strict](https://img.shields.io/badge/Frontend-TypeScript%20Strict-blue.svg)](./frontend)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI: Async ASGI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Docker: Multi--Stage](https://img.shields.io/badge/Docker-Compose%20Prod-2496ED.svg)](./docker-compose.prod.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 1. Problem Being Solved

Modern engineering teams inherit and maintain codebases that grow in complexity over time. Technical debt accumulates silently:
* **Hidden Architectural Coupling**: Circular import chains and tight efferent coupling create brittle architectures where localized changes cause cascading failures.
* **Unobserved Duplication**: Copy-paste programming replicates logic, bugs, and security flaws across multiple files without detection.
* **Defect Hotspot Blindspots**: High-churn files undergoing frequent changes often coincide with high cyclomatic complexity, forming disproportionate defect attractors.
* **Opaque Software Metrics**: Traditional code scanners produce black-box "quality ratings" with obscure formulas that engineers cannot reproduce, audit, or act upon.
* **Security & Ingestion Overhead**: Existing analysis pipelines often execute arbitrary build scripts or load untrusted repository code in CI environments, introducing supply chain and code-execution risks.

The **Codebase Intelligence Engine** solves these challenges by providing a transparent, deterministic static analysis platform that runs in an isolated zero-execution sandbox, exposes exact mathematical scoring models, and provides automated PR Quality Gates and industry-standard exports.

---

## 2. Key Capabilities

* **Zero-Execution Static Analysis**: Extracts structural AST trees without executing, building, or importing repository code.
* **Multilingual AST Parsing**: Concrete language parsing via Tree-sitter (Python, JavaScript, TypeScript, Go, Rust, Java, C/C++) alongside native Python AST parsing.
* **5-Pillar Explainable Health Scoring**: Evaluates maintainability, duplication, architecture, volatility, and code quality using clear, auditable formulas.
* **Dependency Graph & Circular Dependency Detection**: Synthesizes directed file dependency graphs, calculates afferent/efferent coupling and instability, and uses Tarjan's Strongly Connected Components algorithm to identify circular import cycles.
* **Karp-Rabin Code Clone Detection**: Type-1 and Type-2 code clone detection using 64-bit polynomial rolling hashes with bounded bucket guards.
* **Git Churn & Hotspot Fusion**: Analyzes commit history velocity, churn volume, and author spread to prioritize refactoring candidates ($H_{\text{defect}}$).
* **Automated PR Quality Gates & Timeline Trajectory**: Compares two analysis runs of a repository to evaluate quality gate rules (`PASSED`, `WARNING`, `FAILED`), compute delta metrics, track issue lifecycles with canonical fingerprints, and chart longitudinal health trends.
* **Standardized Production Exports**: Exports reports in OASIS SARIF v2.1.0 (for GitHub Code Scanning), human-readable executive Markdown, and consolidated JSON snapshots.
* **Real-time SSE Streaming & Cancellation**: Server-Sent Events deliver live ingestion progress with clean cancellation handling and zero orphaned storage leaks.

---

## 3. System Architecture

The engine uses a **Clean / Layered Architecture** with strict boundary separation between presentation, API routing, background task orchestration, pluggable static analyzers, and persistence:

```
                      [ Client Browser: React 18 + Vite ]
                                       │
                         (HTTP REST / SSE Streaming)
                                       ▼
                   [ Ingress / Nginx Hardened Reverse Proxy ]
                                       │
                                (Port 8000)
                                       ▼
                     [ Backend: FastAPI Async ASGI Engine ]
                      ├── CorrelationIdMiddleware (X-Request-ID)
                      ├── SecurityHeadersMiddleware (CSP, HSTS, DENY)
                      ├── Distributed RateLimiter (Redis / Degraded Memory)
                      └── Standardized Exception Handler
                             │                    │
          (Enqueue Analysis) │                    │ (Async SQLAlchemy 2.0)
                             ▼                    ▼
               [ Redis 7 Message Broker ]   [ PostgreSQL 16 DB ]
                             │                    ▲
                             ▼                    │ (Persist Metrics & Issues)
               [ Celery Asynchronous Worker ] ────┘
                 ├── Shallow Sandbox Clone (`git clone --depth 100`)
                 ├── File Discovery & Language Classifier
                 ├── Tree-sitter & AST Symbol Extraction
                 ├── Cyclomatic Complexity & Halstead Engine
                 ├── Dependency Synthesizer & Tarjan's Cycles
                 ├── Karp-Rabin Clone Detector (DUP-001)
                 ├── Git Churn Analyzer & Defect Hotspot Fusion
                 └── 5-Pillar Health Score Calculator
```

---

## 4. Technology Stack

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | **React 18 + TypeScript + Vite** | High-performance modular component hierarchy, strict compile-time types matching backend DTO schemas, fast HMR. |
| **Design System** | **Tailwind CSS + Lucide Icons** | Linear/GitHub-inspired developer console aesthetic, high-contrast dark palette (`#0B0F19`), zero runtime CSS overhead. |
| **API Backend** | **FastAPI + Pydantic v2** | High-throughput asynchronous ASGI web server, automatic OpenAPI 3.1 & ReDoc generation, fast validation via `pydantic-core`. |
| **Database** | **PostgreSQL 16 + SQLAlchemy 2.0 (Async)** | ACID compliance for relational data (Repositories, Analyses, Files, Symbols, Issues) and JSONB indexing for metadata. |
| **Task Queue** | **Celery + Redis 7** | Non-blocking execution of heavy repository analysis workloads with worker concurrency controls and task state management. |
| **Static Analyzers**| **Tree-sitter & Python AST** | Concrete multilingual syntax trees and Python semantic inspection without executing repository code. |
| **Proxy / Gateway** | **Nginx Alpine** | Hardened ingress proxy with gzip compression, security headers, unbuffered SSE streaming, and non-root execution. |
| **Containerization**| **Docker & Docker Compose** | Reproducible multi-stage production container builds with unprivileged system users (`appuser`). |

---

## 5. Analysis Pipeline

Each repository analysis executes through an isolated 9-stage deterministic pipeline:

```
  ┌───────────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
  │ 1. Validate & Clone   │ ──> │ 2. Discover & Classify│ ──> │ 3. AST Symbol Extract │
  └───────────────────────┘     └───────────────────────┘     └───────────────────────┘
              │                                                           │
              ▼                                                           ▼
  ┌───────────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
  │ 6. Karp-Rabin Clones  │ <── │ 5. Dependency Graph   │ <── │ 4. Complexity Metrics │
  └───────────────────────┘     └───────────────────────┘     └───────────────────────┘
              │
              ▼
  ┌───────────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
  │ 7. Churn & Hotspots   │ ──> │ 8. Health & Rules     │ ──> │ 9. Clean & Persist    │
  └───────────────────────┘     └───────────────────────┘     └───────────────────────┘
```

1. **Validation & Sandbox Clone**: URL SSRF verification followed by shallow git clone (`--depth 100`) into an isolated temporary workspace directory.
2. **File Discovery & Classification**: Scans files while respecting `.gitignore`, binary exclusions, and size thresholds; classifies programming languages.
3. **AST Symbol Extraction**: Parses concrete syntax trees to extract functions, classes, methods, signatures, docstrings, and line bounds.
4. **Complexity Analysis**: Computes cyclomatic complexity, SLOC, Halstead volume, and Maintainability Index ($MI$) per file.
5. **Dependency Graph Synthesis**: Maps module import statements into directed graph edges, calculating efferent/afferent coupling and running Tarjan's algorithm for circular cycles.
6. **Karp-Rabin Clone Detection**: Tokenizes statements into 64-bit polynomial rolling hashes to detect duplicate code fragments ($\ge 5$ lines).
7. **Git Churn Extraction & Hotspot Fusion**: Analyzes git log statistics to calculate commit volatility, lines changed, and author count, fusing churn with complexity ($H_{\text{defect}}$).
8. **Health Scoring & Rule Evaluation**: Calculates the 5-pillar health score ($S_{\text{overall}}$) and evaluates deterministic diagnostic rules with canonical fingerprints.
9. **Persistence & Sandbox Cleanup**: Persists analysis metrics, issues, and metadata to PostgreSQL, broadcasts completion via SSE, and removes temporary clones.

---

## 6. Security Model

* **Zero-Execution Sandbox**: Repository source code is treated strictly as inert text data. Analyzed files are never loaded into Python's interpreter runtime, compiled, or executed.
* **SSRF Prevention**: Strict validation via `is_ip_literal_or_private()` blocks loopback interfaces (`127.0.0.1`), AWS instance metadata (`169.254.169.254`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and IPv6 addresses (`::1`, `[::1]`).
* **Path Traversal Defense**: All file paths are strictly resolved relative to the sandbox root; traversal attacks (`../`) are rejected immediately.
* **Non-Root Execution**: Backend and worker containers run under an unprivileged `appuser` (UID 1001), preventing host privilege escalation.
* **Credential Sanitization**: The logging system filters and redacts URI passwords, tokens, and authorization headers across all logs.
* **Resource Governance**:
  * Repository size cap: `MAX_REPO_SIZE_MB = 500`
  * Clone timeout: `CLONE_TIMEOUT_SECONDS = 60`
  * Candidate bucket size cap: `MAX_CANDIDATE_BUCKET_SIZE = 100` (prevents polynomial comparison explosion)
  * Retained clone pairs cap: `MAX_CLONE_PAIRS_CAP = 10000`

---

## 7. Zero-Execution Invariant

A foundational design principle of the engine is the **Zero-Execution Invariant**:

> **Invariant**: Under no circumstances does the engine execute, import, evaluate, or invoke scripts, modules, or build configurations from the analyzed repository.

### Verification Mechanism
* **Lexical & AST Isolation**: Analysis is driven entirely by static tokenization (Tree-sitter concrete syntax trees and Python's `ast.parse`).
* **Module Namespace Guard**: Unit tests verify that after analyzing repositories (including live packages like `bottle` and `expressjs/morgan`), zero analyzed modules exist within `sys.modules`.
* **No Interpreter Invocation**: The engine never executes `python setup.py`, `npm install`, `pip install`, `make`, or arbitrary package manager hooks.

---

## 8. Explainable Software Health Scoring

Unlike black-box quality metrics, the engine uses an auditable, deterministic formulation:

$$S_{\text{overall}} = 0.25 S_{\text{maint}} + 0.20 S_{\text{dup}} + 0.20 S_{\text{arch}} + 0.20 S_{\text{vol}} + 0.15 S_{\text{qual}}$$

### Pillar Formulations

1. **Maintainability Score ($S_{\text{maint}}$)**:
   $$S_{\text{maint}} = \text{clamp}\left(\frac{\sum MI \times \text{SLOC}}{\sum \text{SLOC}}, 0, 100\right)$$
   Weighted average of Coleman-Welker Maintainability Index across all source files.

2. **Duplication Health Score ($S_{\text{dup}}$)**:
   $$S_{\text{dup}} = \text{clamp}\left(100 - (\text{duplication\_ratio} \times 1.5) - \min(10, \text{duplication\_blocks} \times 0.5), 0, 100\right)$$
   Penalizes both overall duplicated line volume and fragmented clone instances.

3. **Architecture Score ($S_{\text{arch}}$)**:
   $$S_{\text{arch}} = \text{clamp}\left(100 - (\text{circular\_cycles} \times 15) - (\text{high\_coupling\_files} \times 5), 0, 100\right)$$
   Penalizes circular dependency cycles and files with extreme efferent coupling ($C_e > 10$).

4. **Volatility Score ($S_{\text{vol}}$)**:
   $$S_{\text{vol}} = \text{clamp}\left(100 - (\text{avg\_churn} \times 0.5) - (\text{hotspot\_count} \times 5), 0, 100\right)$$
   Reflects churn stability and the density of defect hotspot files.

5. **Quality Score ($S_{\text{qual}}$)**:
   $$S_{\text{qual}} = \text{clamp}\left(100 - (\text{issues}_{\text{high}} \times 10) - (\text{issues}_{\text{medium}} \times 3) - (\text{issues}_{\text{low}} \times 1), 0, 100\right)$$
   Deducts weighted points based on static diagnostic issue severity.

---

## 9. Dependency Analysis & Circular Cycle Detection

The engine constructs a directed graph $G = (V, E)$ where vertices $V$ represent source files and directed edges $E = (u, v)$ represent import statements from $u$ to $v$.

* **Afferent Coupling ($C_a$)**: Number of external files depending on this file (incoming dependencies).
* **Efferent Coupling ($C_e$)**: Number of external files this file depends upon (outgoing dependencies).
* **Instability ($I$)**:
  $$I = \frac{C_e}{C_a + C_e}$$
  Measures the file's resilience to change ($0 \le I \le 1$). An instability of $1.0$ indicates maximal fragility.
* **Tarjan's Strongly Connected Components (SCC)**: Traverses the directed graph in linear time $O(V + E)$ to find strongly connected subgraphs with $|V| > 1$, isolating circular dependency loops.

---

## 10. Code Duplication Detection (Karp-Rabin)

The engine detects Type-1 (exact) and Type-2 (renamed/parameterized) code clones:

* **Tokenization & Normalization**: Strips comments, whitespace, and formatting; normalizes statement tokens.
* **64-bit Polynomial Rolling Hash**: Computes rolling hash values across sliding token windows ($\ge 5$ lines):
  $$H(s) = \sum_{i=0}^{k-1} c_i \cdot b^{k-1-i} \pmod{2^{64}}$$
* **Bucket Indexing with Protection Guard**: Hashes are indexed in collision buckets. To guarantee linear complexity $O(N)$ and prevent polynomial explosion $O(N^2)$ on massive repetitive files, candidate buckets are capped at `MAX_CANDIDATE_BUCKET_SIZE = 100`.
* **DUP-001 Diagnostics**: Emits actionable duplication issues with start/end line coordinates, clone companion paths, and remediation effort estimates.

---

## 11. Git Churn & Defect Hotspot Fusion

The engine queries git commit history (`git log -z --numstat --no-merges --depth 100`) to quantify change velocity:

### Exact Git Churn Formula ($C_{\text{churn}}$)
$$C_{\text{churn}} = \text{clamp}\left(\frac{\text{commits}}{20} \times 50.0 + \frac{\text{insertions} + \text{deletions}}{1000} \times 30.0 + \frac{\text{authors}}{5} \times 20.0, 0.0, 100.0\right)$$

### Defect Hotspot Fusion Formula ($H_{\text{defect}}$)
Files undergoing rapid modification while maintaining high complexity represent elevated bug risk. The engine calculates:
$$H_{\text{defect}} = 0.6 H_{\text{static}} + 0.4 C_{\text{churn}}$$
where $H_{\text{static}}$ is normalized cyclomatic complexity. Files are sorted by $H_{\text{defect}}$ to guide refactoring and code review attention.

---

## 12. Compare Engine & Longitudinal Timeline

### Comparative Diff Engine
Engineers can compare any two analyses of the same repository (`base_id` vs. `head_id`):
* **Delta Metrics**: Changes in SLOC, overall health ($\Delta S_{\text{overall}}$), maintainability, and circular cycle counts.
* **Issue Lifecycle Tracking**: Issues are fingerprinted using a canonical SHA-256 hash:
  $$\text{Fingerprint} = \text{SHA256}(\text{rule\_id} + \text{file\_path} + \text{symbol\_scope})$$
  This isolates line movements from genuine code changes, categorizing issues into `new`, `fixed`, and `persistent`.
* **Automated PR Quality Gates**: Evaluates conditions to produce an unambiguous verdict:
  * `PASSED`: No critical issues, health delta $\ge 0$.
  * `WARNING`: Minor health regression or low-severity issues introduced.
  * `FAILED`: Critical issues introduced or health score dropped beyond threshold.

### Longitudinal Timeline
The timeline API endpoint (`GET /api/v1/repositories/{id}/timeline`) aggregates health trajectory points across consecutive commits, tracking technical debt trends over time.

---

## 13. Export Formats

| Format | Endpoint | Intended Audience / Use Case |
| :--- | :--- | :--- |
| **OASIS SARIF v2.1.0** | `GET /api/v1/analyses/{id}/export/sarif` | Standardized format for CI/CD ingestion, GitHub Code Scanning, and SonarQube. |
| **Executive Markdown** | `GET /api/v1/analyses/{id}/export/markdown` | Human-readable audit report including score breakdown, top hotspots, and remediation plans. |
| **Consolidated JSON** | `GET /api/v1/analyses/{id}/export/json` | Full machine-readable data snapshot for custom data pipelines and archiving. |

---

## 14. API Overview

### Health & System Probes
* `GET /live`: Lightweight Kubernetes liveness probe (HTTP 200).
* `GET /ready`: Readiness probe verifying PostgreSQL and Redis connection health (HTTP 200 or 503).
* `GET /health` or `GET /api/v1/health`: Detailed component health diagnostic information.

### Analysis & Ingestion
* `POST /api/v1/repositories/analyze`: Enqueues repository analysis (`HTTP 202 Accepted`).
* `GET /api/v1/analyses/{id}`: Retrieves analysis status, progress, and completed metrics.
* `GET /api/v1/analyses/{id}/events`: Server-Sent Events (SSE) stream for live progress tracking.
* `POST /api/v1/analyses/{id}/cancel`: Gracefully cancels an in-progress or queued analysis.
* `POST /api/v1/analyses/recover-stale`: Identifies and recovers stalled background jobs.

### Detailed Analysis Queries
* `GET /api/v1/analyses/{id}/files`: File catalog with language tags, lines of code, and comment density.
* `GET /api/v1/analyses/{id}/symbols`: Extracted function, class, and method symbols with line boundaries.
* `GET /api/v1/analyses/{id}/dependencies`: Directed dependency nodes, edges, coupling, and circular loops.
* `GET /api/v1/analyses/{id}/hotspots`: Defect hotspot rankings ($H_{\text{defect}}$).
* `GET /api/v1/analyses/{id}/duplication`: Karp-Rabin code clones and DUP-001 diagnostics.
* `GET /api/v1/analyses/{id}/churn`: Git churn metrics and file volatility.
* `GET /api/v1/analyses/{id}/health`: 5-pillar health score radar breakdown.
* `GET /api/v1/analyses/{id}/issues`: Filterable static diagnostic issues with remediation plans.

### Longitudinal & Diffing
* `GET /api/v1/analyses/compare?base_id={uuid}&head_id={uuid}`: Comparative diff and PR Quality Gate.
* `GET /api/v1/repositories/{id}/timeline`: Historical health trajectory data points.

### Exports
* `GET /api/v1/analyses/{id}/export/sarif`: OASIS SARIF v2.1.0 report.
* `GET /api/v1/analyses/{id}/export/markdown`: Executive Markdown report.
* `GET /api/v1/analyses/{id}/export/json`: Consolidated JSON snapshot.

---

## 15. Local Development Setup

### Prerequisites
* Python 3.11+
* Node.js 20+ & npm
* PostgreSQL 16 & Redis 7 (local or containerized)

### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start Celery worker in a separate terminal
celery -A app.workers.celery_app.celery_app worker --loglevel=info -Q ingestion

# Launch development ASGI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend dashboard will be available at [http://localhost:5173](http://localhost:5173).

---

## 16. Production Docker Deployment

Deploy the multi-stage, non-root production stack using Docker Compose:

```bash
# 1. Prepare production environment file
cp .env.example .env.prod
# Update POSTGRES_PASSWORD, SECRET_KEY, and REDIS_PASSWORD in .env.prod

# 2. Build and launch all services in detached mode
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 3. Verify deployment health probes
curl -f http://localhost/live
curl -f http://localhost/ready
```

### Production Stack Configuration
* **Nginx Reverse Proxy**: Port 80, security headers (HSTS, CSP, X-Frame-Options DENY), unbuffered SSE support (`proxy_buffering off`).
* **Frontend**: Static production assets served via unprivileged Nginx.
* **FastAPI Backend**: Uvicorn multi-worker ASGI engine running under unprivileged user `appuser`.
* **Celery Worker**: Asynchronous queue processor running under unprivileged user `appuser`.
* **PostgreSQL 16**: Persistent database volume (`prod_postgres_data`) with health checks.
* **Redis 7**: Persistent cache & broker volume (`prod_redis_data`) with authentication.

---

## 17. Testing & Verification

The platform is backed by a comprehensive automated test suite covering security boundaries, static parsing, algorithmic correctness, and API contracts:

### Run Backend Test Suite
```bash
cd backend
pytest -v
```
**Results**: **229 tests passed (100% pass rate)**.

### Run Frontend Typecheck & Production Build
```bash
cd frontend
npm run build
```
**Results**: **0 TypeScript compilation errors, 0 build warnings**.

---

## 18. Known Limitations & Operational Boundaries

To ensure engineering transparency, the platform's operational boundaries are explicitly defined:

1. **Static Analysis Boundary**: Concrete AST parsing examines source code structure and statically declared imports. The engine does **not** execute repository code and cannot observe dynamic runtime behavior (such as dynamic dispatch, runtime reflection, or environment-driven dependency injection).
2. **Git History Depth**: Repository clones use shallow depth (`--depth 100`) to bound disk usage and provide fast ingestion times. Churn analytics reflect activity within this commit window.
3. **Correlation vs. Causality**: Git churn ($C_{\text{churn}}$) and defect hotspot fusion ($H_{\text{defect}}$) quantify file change velocity and complexity to highlight refactoring targets. High churn indicates change pressure, not necessarily defect presence.
4. **Diagnostic Scope**: Built-in heuristic rules detect architectural smells, maintainability anti-patterns, cyclomatic complexity anomalies, and credential leaks. They complement, but do not replace, dedicated dynamic application security testing (DAST) or CVE database scanners.
5. **Bounded Clone Detection**: Code duplication detection uses a 64-bit Karp-Rabin polynomial rolling hash. To prevent $O(N^2)$ memory and compute explosion on massive repositories, candidate comparison buckets are capped at `MAX_CANDIDATE_BUCKET_SIZE = 100` and retained clone pairs are capped at `MAX_CLONE_PAIRS_CAP = 10000`.
6. **Readiness Probe Coupling**: The readiness probe (`GET /ready`) verifies active connectivity to both PostgreSQL and Redis. If either dependency is degraded, `/ready` returns HTTP 503 to divert traffic, while the liveness probe (`GET /live`) remains independent (HTTP 200) to prevent container restart loops.
7. **Rate Limiter Degradation Behavior**: When Redis is unavailable and `RATE_LIMIT_ALLOW_MEMORY_FALLBACK = True`, rate limiting operates in degraded, per-process in-memory mode, logging prominent warnings and attaching `X-RateLimit-Degraded: true` response headers. When set to `False`, requests fail closed with HTTP 503.

---

## 19. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
