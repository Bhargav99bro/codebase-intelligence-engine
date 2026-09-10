from collections import deque
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

from app.dependencies.graph import DirectedDependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class ImpactedFileItem:
    file_id: uuid.UUID
    file_path: str
    depth: int
    is_direct: bool
    relationship_path: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": str(self.file_id),
            "file_path": self.file_path,
            "depth": self.depth,
            "is_direct": self.is_direct,
            "relationship_path": self.relationship_path,
        }


@dataclass
class ImpactAnalysisResult:
    target_file_id: uuid.UUID
    target_file_path: str
    direction: str  # "dependents" or "dependencies"
    max_depth: int
    affected_files_count: int
    direct_count: int
    transitive_count: int
    items: List[ImpactedFileItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_file_id": str(self.target_file_id),
            "target_file_path": self.target_file_path,
            "direction": self.direction,
            "max_depth": self.max_depth,
            "affected_files_count": self.affected_files_count,
            "direct_count": self.direct_count,
            "transitive_count": self.transitive_count,
            "items": [item.to_dict() for item in self.items],
        }


class ImpactAnalyzer:
    """Calculates direct and transitive change impact blast-radius using bounded BFS."""

    def __init__(self, graph: DirectedDependencyGraph) -> None:
        self.graph = graph

    def analyze(
        self,
        target_file_id: uuid.UUID,
        direction: str = "dependents",
        max_depth: int = 5,
    ) -> Optional[ImpactAnalysisResult]:
        """
        Traverses dependencies using BFS.
        direction='dependents': traverses reverse edges (who breaks if target changes?)
        direction='dependencies': traverses outgoing edges (what does target need?)
        """
        if target_file_id not in self.graph.nodes:
            return None

        # Clamp max_depth between 1 and 10
        bounded_depth = max(1, min(max_depth, 10))
        target_node = self.graph.nodes[target_file_id]

        # Choose adjacency direction
        # If 'dependents', we traverse reverse_adjacency (incoming edges)
        # If 'dependencies', we traverse adjacency (outgoing edges)
        adj = self.graph.reverse_adjacency if direction == "dependents" else self.graph.adjacency

        visited: Set[uuid.UUID] = {target_file_id}
        # Queue item: (current_file_id, depth, path_of_file_paths)
        queue = deque([(target_file_id, 0, [target_node.file_path])])

        impacted_items: List[ImpactedFileItem] = []
        direct_count = 0
        transitive_count = 0

        while queue:
            curr_id, curr_depth, curr_path = queue.popleft()

            if curr_depth >= bounded_depth:
                continue

            neighbors = sorted(
                adj.get(curr_id, set()),
                key=lambda fid: self.graph.nodes[fid].file_path if fid in self.graph.nodes else "",
            )

            for neighbor_id in neighbors:
                if neighbor_id not in visited and neighbor_id in self.graph.nodes:
                    visited.add(neighbor_id)
                    neighbor_node = self.graph.nodes[neighbor_id]
                    next_depth = curr_depth + 1
                    next_path = curr_path + [neighbor_node.file_path]
                    is_direct = (next_depth == 1)

                    if is_direct:
                        direct_count += 1
                    else:
                        transitive_count += 1

                    item = ImpactedFileItem(
                        file_id=neighbor_id,
                        file_path=neighbor_node.file_path,
                        depth=next_depth,
                        is_direct=is_direct,
                        relationship_path=next_path,
                    )
                    impacted_items.append(item)
                    queue.append((neighbor_id, next_depth, next_path))

        # Sort items by depth ascending, then file_path
        impacted_items.sort(key=lambda it: (it.depth, it.file_path))

        return ImpactAnalysisResult(
            target_file_id=target_file_id,
            target_file_path=target_node.file_path,
            direction=direction,
            max_depth=bounded_depth,
            affected_files_count=len(impacted_items),
            direct_count=direct_count,
            transitive_count=transitive_count,
            items=impacted_items,
        )
