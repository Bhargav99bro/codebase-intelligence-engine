from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.dependencies.base import ResolvedDependency

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    file_id: uuid.UUID
    file_path: str
    language: Optional[str] = None
    fan_in: int = 0
    fan_out: int = 0
    internal_dependencies_count: int = 0
    external_dependencies_count: int = 0
    unresolved_dependencies_count: int = 0
    instability: float = 0.0
    in_cycle: bool = False
    cycle_count: int = 0


@dataclass
class GraphEdge:
    id: uuid.UUID
    source_file_id: uuid.UUID
    source_file_path: str
    target_file_id: uuid.UUID
    target_file_path: str
    target_module: str
    dependency_type: str
    imported_symbols: List[str]
    line_number: int


@dataclass
class DetectedCycle:
    cycle_id: int
    length: int
    file_ids: List[uuid.UUID]
    file_paths: List[str]
    edges: List[Dict[str, Any]]


class DirectedDependencyGraph:
    """Directed dependency graph representing internal repository file dependencies."""

    def __init__(self) -> None:
        self.nodes: Dict[uuid.UUID, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        self.reverse_adjacency: Dict[uuid.UUID, Set[uuid.UUID]] = {}

        # Repository-wide edge counters
        self.total_dependencies: int = 0
        self.internal_edges_count: int = 0
        self.external_edges_count: int = 0
        self.unresolved_edges_count: int = 0

        # Cycle results
        self.cycles: List[DetectedCycle] = []
        self.cycle_cap_reached: bool = False

    def add_file_node(
        self,
        file_id: uuid.UUID,
        file_path: str,
        language: Optional[str] = None,
    ) -> None:
        if file_id not in self.nodes:
            self.nodes[file_id] = GraphNode(
                file_id=file_id,
                file_path=file_path,
                language=language,
            )
            self.adjacency[file_id] = set()
            self.reverse_adjacency[file_id] = set()

    def process_resolved_dependency(self, dep: ResolvedDependency) -> None:
        self.total_dependencies += 1

        if not dep.source_file_id or dep.source_file_id not in self.nodes:
            return

        source_node = self.nodes[dep.source_file_id]

        if dep.resolution_status == "internal" and dep.target_file_id:
            # Internal edge
            self.internal_edges_count += 1
            source_node.internal_dependencies_count += 1

            if dep.target_file_id in self.nodes:
                target_node = self.nodes[dep.target_file_id]
                self.adjacency[dep.source_file_id].add(dep.target_file_id)
                self.reverse_adjacency[dep.target_file_id].add(dep.source_file_id)

                self.edges.append(
                    GraphEdge(
                        id=uuid.uuid4(),
                        source_file_id=dep.source_file_id,
                        source_file_path=dep.source_file_path,
                        target_file_id=dep.target_file_id,
                        target_file_path=target_node.file_path,
                        target_module=dep.target_module,
                        dependency_type=dep.dependency_type,
                        imported_symbols=dep.imported_symbols,
                        line_number=dep.line_number,
                    )
                )

        elif dep.resolution_status == "external":
            self.external_edges_count += 1
            source_node.external_dependencies_count += 1

        else:  # unresolved
            self.unresolved_edges_count += 1
            source_node.unresolved_dependencies_count += 1

    def compute_metrics(self) -> None:
        """Calculates fan-in, fan-out, and instability I = fan_out / (fan_in + fan_out)."""
        for fid, node in self.nodes.items():
            node.fan_out = len(self.adjacency.get(fid, set()))
            node.fan_in = len(self.reverse_adjacency.get(fid, set()))

            total_degree = node.fan_in + node.fan_out
            if total_degree == 0:
                node.instability = 0.0
            else:
                node.instability = round(float(node.fan_out) / float(total_degree), 4)

    def detect_cycles(self, max_cycles: int = 100) -> List[DetectedCycle]:
        """
        Discovers circular dependencies using Tarjan's Strongly Connected Components
        with canonical rotation deduplication and a hard safety limit.
        """
        sccs = self._tarjan_scc()
        detected: List[DetectedCycle] = []
        seen_canonical_cycles: Set[Tuple[uuid.UUID, ...]] = set()

        for scc in sccs:
            if len(detected) >= max_cycles:
                self.cycle_cap_reached = True
                break

            # Case A: Self-loop (single node importing itself)
            if len(scc) == 1:
                u = next(iter(scc))
                if u in self.adjacency.get(u, set()):
                    cycle_tuple = (u,)
                    if cycle_tuple not in seen_canonical_cycles:
                        seen_canonical_cycles.add(cycle_tuple)
                        node_u = self.nodes[u]
                        node_u.in_cycle = True
                        node_u.cycle_count += 1
                        detected.append(
                            DetectedCycle(
                                cycle_id=len(detected) + 1,
                                length=1,
                                file_ids=[u, u],
                                file_paths=[node_u.file_path, node_u.file_path],
                                edges=[
                                    {
                                        "source": node_u.file_path,
                                        "target": node_u.file_path,
                                    }
                                ],
                            )
                        )
                continue

            # Case B: Multi-node SCC (contains one or more cycles)
            # Run elementary cycle discovery within the SCC subgraph
            scc_set = set(scc)
            for start_node in scc:
                if len(detected) >= max_cycles:
                    self.cycle_cap_reached = True
                    break

                self._find_cycles_dfs(
                    start_node=start_node,
                    curr_node=start_node,
                    scc_set=scc_set,
                    path=[start_node],
                    visited_in_path={start_node},
                    detected=detected,
                    seen=seen_canonical_cycles,
                    max_cycles=max_cycles,
                )

        # Mark cycle participation on graph nodes
        for c in detected:
            for fid in set(c.file_ids):
                if fid in self.nodes:
                    self.nodes[fid].in_cycle = True
                    self.nodes[fid].cycle_count += 1

        self.cycles = detected
        return detected

    def _find_cycles_dfs(
        self,
        start_node: uuid.UUID,
        curr_node: uuid.UUID,
        scc_set: Set[uuid.UUID],
        path: List[uuid.UUID],
        visited_in_path: Set[uuid.UUID],
        detected: List[DetectedCycle],
        seen: Set[Tuple[uuid.UUID, ...]],
        max_cycles: int,
    ) -> None:
        if len(detected) >= max_cycles:
            self.cycle_cap_reached = True
            return

        for neighbor in sorted(self.adjacency.get(curr_node, set()), key=lambda n: self.nodes[n].file_path):
            if neighbor not in scc_set:
                continue

            if neighbor == start_node and len(path) >= 2:
                # Cycle closed: path forms a cycle back to start_node
                canonical = self._canonicalize_cycle(path)
                if canonical not in seen:
                    seen.add(canonical)
                    full_cycle_nodes = list(canonical) + [canonical[0]]
                    paths = [self.nodes[fid].file_path for fid in full_cycle_nodes]

                    edges_in_cycle = []
                    for i in range(len(full_cycle_nodes) - 1):
                        edges_in_cycle.append(
                            {
                                "source": self.nodes[full_cycle_nodes[i]].file_path,
                                "target": self.nodes[full_cycle_nodes[i + 1]].file_path,
                            }
                        )

                    detected.append(
                        DetectedCycle(
                            cycle_id=len(detected) + 1,
                            length=len(canonical),
                            file_ids=full_cycle_nodes,
                            file_paths=paths,
                            edges=edges_in_cycle,
                        )
                    )
                    if len(detected) >= max_cycles:
                        self.cycle_cap_reached = True
                        return

            elif neighbor not in visited_in_path and len(path) < 15:  # Bound depth
                # To prevent rotated permutations during search, we only consider neighbors
                # with file_path >= start_node's file_path
                if self.nodes[neighbor].file_path >= self.nodes[start_node].file_path:
                    visited_in_path.add(neighbor)
                    path.append(neighbor)
                    self._find_cycles_dfs(
                        start_node=start_node,
                        curr_node=neighbor,
                        scc_set=scc_set,
                        path=path,
                        visited_in_path=visited_in_path,
                        detected=detected,
                        seen=seen,
                        max_cycles=max_cycles,
                    )
                    path.pop()
                    visited_in_path.remove(neighbor)

    def _canonicalize_cycle(self, cycle: List[uuid.UUID]) -> Tuple[uuid.UUID, ...]:
        """
        Rotates a cycle list so the element with the lexicographically smallest
        file_path is at index 0. This guarantees each cycle is unique regardless of rotation.
        """
        if not cycle:
            return ()
        min_idx = 0
        min_path = self.nodes[cycle[0]].file_path
        for i, fid in enumerate(cycle):
            p = self.nodes[fid].file_path
            if p < min_path:
                min_path = p
                min_idx = i
        rotated = cycle[min_idx:] + cycle[:min_idx]
        return tuple(rotated)

    def _tarjan_scc(self) -> List[List[uuid.UUID]]:
        """Tarjan's algorithm for finding Strongly Connected Components in O(V + E)."""
        index = 0
        indices: Dict[uuid.UUID, int] = {}
        lowlinks: Dict[uuid.UUID, int] = {}
        on_stack: Set[uuid.UUID] = set()
        stack: List[uuid.UUID] = []
        sccs: List[List[uuid.UUID]] = []

        def strongconnect(v: uuid.UUID) -> None:
            nonlocal index
            indices[v] = index
            lowlinks[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in self.adjacency.get(v, set()):
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for node_id in self.nodes:
            if node_id not in indices:
                strongconnect(node_id)

        return sccs

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Produces repository-level dependency summary metrics and architecture indicators."""
        nodes_list = list(self.nodes.values())
        total_files = len(nodes_list)

        fan_ins = [n.fan_in for n in nodes_list]
        fan_outs = [n.fan_out for n in nodes_list]
        instabilities = [n.instability for n in nodes_list if (n.fan_in + n.fan_out) > 0]

        avg_fan_in = round(sum(fan_ins) / total_files, 2) if total_files else 0.0
        avg_fan_out = round(sum(fan_outs) / total_files, 2) if total_files else 0.0
        max_fan_in = max(fan_ins) if fan_ins else 0
        max_fan_out = max(fan_outs) if fan_outs else 0
        avg_instability = round(sum(instabilities) / len(instabilities), 2) if instabilities else 0.0

        # Isolated modules: internal fan_in == 0, internal fan_out == 0, internal_dep_count == 0
        isolated_nodes = [
            {"file_id": str(n.file_id), "file_path": n.file_path}
            for n in nodes_list
            if n.fan_in == 0 and n.fan_out == 0 and n.internal_dependencies_count == 0
        ]

        # Top Fan-in (most depended-on / core foundation)
        top_fan_in = sorted(nodes_list, key=lambda n: n.fan_in, reverse=True)[:10]
        top_fan_in_data = [
            {
                "file_id": str(n.file_id),
                "file_path": n.file_path,
                "fan_in": n.fan_in,
                "fan_out": n.fan_out,
                "instability": n.instability,
            }
            for n in top_fan_in
            if n.fan_in > 0
        ]

        # Top Fan-out (highest coupling / orchestrators)
        top_fan_out = sorted(nodes_list, key=lambda n: n.fan_out, reverse=True)[:10]
        top_fan_out_data = [
            {
                "file_id": str(n.file_id),
                "file_path": n.file_path,
                "fan_in": n.fan_in,
                "fan_out": n.fan_out,
                "instability": n.instability,
            }
            for n in top_fan_out
            if n.fan_out > 0
        ]

        # Architectural indicators
        core_foundation = [n.file_path for n in nodes_list if n.fan_in >= 3 and n.instability <= 0.3]
        high_coupling = [n.file_path for n in nodes_list if n.fan_out >= 5 or (n.fan_in >= 3 and n.fan_out >= 3)]
        cyclic_modules = sorted(list({n.file_path for n in nodes_list if n.in_cycle}))

        return {
            "total_dependencies": self.total_dependencies,
            "internal_dependencies": self.internal_edges_count,
            "external_dependencies": self.external_edges_count,
            "unresolved_dependencies": self.unresolved_edges_count,
            "analyzed_files": total_files,
            "isolated_files_count": len(isolated_nodes),
            "average_fan_in": avg_fan_in,
            "average_fan_out": avg_fan_out,
            "max_fan_in": max_fan_in,
            "max_fan_out": max_fan_out,
            "average_instability": avg_instability,
            "circular_dependency_count": len(self.cycles),
            "cycle_cap_reached": self.cycle_cap_reached,
            "top_fan_in": top_fan_in_data,
            "top_fan_out": top_fan_out_data,
            "cycles_summary": [
                {
                    "cycle_id": c.cycle_id,
                    "length": c.length,
                    "files": c.file_paths,
                }
                for c in self.cycles[:20]
            ],
            "architecture_hotspots": {
                "core_foundation": core_foundation[:15],
                "high_coupling": high_coupling[:15],
                "cyclic_modules": cyclic_modules[:20],
                "isolated_modules": [n["file_path"] for n in isolated_nodes[:15]],
            },
        }
