from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math


@dataclass
class TreemapNode:
    name: str
    path: str
    type: str  # "directory" | "file"
    sloc: int = 0
    total_lines: int = 0
    file_count: int = 0
    language: Optional[str] = None
    maintainability_score: Optional[float] = None
    max_cyclomatic_complexity: Optional[int] = None
    total_cyclomatic_complexity: Optional[int] = None
    issue_count: int = 0
    dominant_severity: Optional[str] = None
    children: List["TreemapNode"] = field(default_factory=list)
    # Squarified layout coordinates in [0, 1000] viewport
    layout_rect: Optional[Dict[str, float]] = None

    @property
    def node_type(self) -> str:
        return self.type

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "node_type": self.type,
            "sloc": self.sloc,
            "total_lines": self.total_lines,
            "file_count": self.file_count,
            "language": self.language,
            "maintainability_score": self.maintainability_score,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "total_cyclomatic_complexity": self.total_cyclomatic_complexity,
            "issue_count": self.issue_count,
            "dominant_severity": self.dominant_severity,
        }
        if self.layout_rect is not None:
            result["layout_rect"] = self.layout_rect
            result["x"] = self.layout_rect["x"]
            result["y"] = self.layout_rect["y"]
            result["width"] = self.layout_rect["width"]
            result["height"] = self.layout_rect["height"]
            result["w"] = self.layout_rect["width"]
            result["h"] = self.layout_rect["height"]
        if self.type == "directory":
            result["children"] = [c.to_dict() for c in self.children]
        return result


class TreemapBuilder:
    """Constructs deterministic squarified treemap hierarchies for codebase visual exploration."""

    SEVERITY_RANKS = {
        "blocker": 5,
        "critical": 4,
        "major": 3,
        "minor": 2,
        "info": 1,
    }

    @classmethod
    def build_hierarchy(
        cls,
        files_data: List[Dict[str, Any]],
        compute_layout: bool = True,
        viewport_width: float = 1000.0,
        viewport_height: float = 1000.0,
    ) -> TreemapNode:
        """Builds a deterministic directory/file tree from file records.

        Each item in `files_data` must have:
        - `path`: str
        - `sloc`: int
        - `total_lines`: int
        - `language`: Optional[str]
        - `maintainability_score`: Optional[float]
        - `max_cyclomatic_complexity`: Optional[int]
        - `total_cyclomatic_complexity`: Optional[int]
        - `issues`: Optional[List[Dict[str, Any]]] or issue counts
        """
        root = TreemapNode(name="root", path="", type="directory")
        dir_map: Dict[str, TreemapNode] = {"": root}

        for item in files_data:
            raw_path = item["path"].replace("\\", "/").strip("/")
            parts = raw_path.split("/")

            # Ensure parent directory nodes exist
            curr_path = ""
            parent_node = root
            for part in parts[:-1]:
                curr_path = f"{curr_path}/{part}" if curr_path else part
                if curr_path not in dir_map:
                    new_dir = TreemapNode(name=part, path=curr_path, type="directory")
                    dir_map[curr_path] = new_dir
                    parent_node.children.append(new_dir)
                parent_node = dir_map[curr_path]

            # File leaf node
            file_name = parts[-1]
            issues = item.get("issues", [])
            dominant_sev = None
            if issues:
                sorted_issues = sorted(
                    issues,
                    key=lambda i: cls.SEVERITY_RANKS.get((i.get("severity") or "").lower(), 0),
                    reverse=True,
                )
                if sorted_issues:
                    dominant_sev = (sorted_issues[0].get("severity") or "").lower()

            leaf = TreemapNode(
                name=file_name,
                path=raw_path,
                type="file",
                sloc=max(0, item.get("sloc", 0)),
                total_lines=max(0, item.get("total_lines", 0)),
                file_count=1,
                language=item.get("language"),
                maintainability_score=item.get("maintainability_score"),
                max_cyclomatic_complexity=item.get("max_cyclomatic_complexity", 0),
                total_cyclomatic_complexity=item.get("total_cyclomatic_complexity", 0),
                issue_count=len(issues) if isinstance(issues, list) else item.get("issue_count", 0),
                dominant_severity=dominant_sev or item.get("dominant_severity"),
            )
            parent_node.children.append(leaf)

        # Roll up metrics and enforce deterministic child sorting at each directory level
        cls._rollup_and_sort(root)

        # Compute squarified coordinates
        if compute_layout and root.sloc > 0:
            root.layout_rect = {"x": 0.0, "y": 0.0, "width": viewport_width, "height": viewport_height}
            cls._squarify_node(root, 0.0, 0.0, viewport_width, viewport_height)

        return root

    @classmethod
    def _rollup_and_sort(cls, node: TreemapNode) -> None:
        """Post-order traversal to sum SLOC and sort children deterministically."""
        if node.type == "file":
            return

        total_sloc = 0
        total_lines = 0
        file_count = 0
        issue_count = 0
        max_cc = 0
        total_cc = 0
        mi_sum = 0.0
        mi_count = 0
        top_sev_rank = 0
        top_sev_name = None

        for child in node.children:
            cls._rollup_and_sort(child)
            total_sloc += child.sloc
            total_lines += child.total_lines
            file_count += child.file_count
            issue_count += child.issue_count
            if child.max_cyclomatic_complexity:
                max_cc = max(max_cc, child.max_cyclomatic_complexity)
            if child.total_cyclomatic_complexity:
                total_cc += child.total_cyclomatic_complexity
            if child.maintainability_score is not None:
                mi_sum += child.maintainability_score * max(1, child.file_count)
                mi_count += max(1, child.file_count)
            if child.dominant_severity:
                rank = cls.SEVERITY_RANKS.get(child.dominant_severity, 0)
                if rank > top_sev_rank:
                    top_sev_rank = rank
                    top_sev_name = child.dominant_severity

        node.sloc = total_sloc
        node.total_lines = total_lines
        node.file_count = file_count
        node.issue_count = issue_count
        node.max_cyclomatic_complexity = max_cc if file_count > 0 else None
        node.total_cyclomatic_complexity = total_cc if file_count > 0 else None
        node.maintainability_score = round(mi_sum / mi_count, 1) if mi_count > 0 else None
        node.dominant_severity = top_sev_name

        # NON-NEGOTIABLE DETERMINISTIC CHILD ORDERING:
        # 1. descending SLOC
        # 2. path ascending on ties
        node.children.sort(key=lambda c: (-c.sloc, c.path))

    @classmethod
    def _squarify_node(cls, node: TreemapNode, x: float, y: float, w: float, h: float) -> None:
        """Recursively partitions (x, y, w, h) among children using the squarified layout."""
        if not node.children or w <= 0 or h <= 0 or node.sloc <= 0:
            return

        total_weight = float(node.sloc)
        cls._squarify_children(node.children, x, y, w, h, total_weight)

        # Recursively squarify sub-directories
        for child in node.children:
            if child.type == "directory" and child.layout_rect:
                cls._squarify_node(
                    child,
                    child.layout_rect["x"],
                    child.layout_rect["y"],
                    child.layout_rect["width"],
                    child.layout_rect["height"],
                )

    @classmethod
    def _squarify_children(
        cls,
        children: List[TreemapNode],
        x: float,
        y: float,
        w: float,
        h: float,
        total_weight: float,
    ) -> None:
        """Squarified treemap implementation based on Bruls, Huizing, and van Wijk."""
        if not children or total_weight <= 0:
            return

        # Prepare normalized weights where total area = w * h
        total_area = w * h
        items = []
        for c in children:
            area = (float(c.sloc) / total_weight) * total_area
            items.append((c, max(1e-6, area)))

        curr_x, curr_y = x, y
        curr_w, curr_h = w, h
        remaining = items[:]

        while remaining:
            row = [remaining.pop(0)]
            side = min(curr_w, curr_h)

            while remaining:
                next_item = remaining[0]
                if cls._worst_aspect_ratio(row + [next_item], side) <= cls._worst_aspect_ratio(row, side):
                    row.append(remaining.pop(0))
                else:
                    break

            # Layout current row
            row_area = sum(item[1] for item in row)
            if curr_w >= curr_h:
                # Vertical strip across height
                row_width = row_area / curr_h if curr_h > 0 else 0
                sub_y = curr_y
                for child_node, area in row:
                    sub_h = area / row_width if row_width > 0 else 0
                    child_node.layout_rect = {
                        "x": round(curr_x, 4),
                        "y": round(sub_y, 4),
                        "width": round(row_width, 4),
                        "height": round(sub_h, 4),
                    }
                    sub_y += sub_h
                curr_x += row_width
                curr_w = max(0.0, curr_w - row_width)
            else:
                # Horizontal strip across width
                row_height = row_area / curr_w if curr_w > 0 else 0
                sub_x = curr_x
                for child_node, area in row:
                    sub_w = area / row_height if row_height > 0 else 0
                    child_node.layout_rect = {
                        "x": round(sub_x, 4),
                        "y": round(curr_y, 4),
                        "width": round(sub_w, 4),
                        "height": round(row_height, 4),
                    }
                    sub_x += sub_w
                curr_y += row_height
                curr_h = max(0.0, curr_h - row_height)

    @staticmethod
    def _worst_aspect_ratio(row: List[Any], side: float) -> float:
        """Returns the maximum aspect ratio of rectangles in row with length `side`."""
        if not row or side <= 0:
            return float("inf")
        row_sum = sum(item[1] for item in row)
        if row_sum <= 0:
            return float("inf")
        side_sq = side * side
        row_sum_sq = row_sum * row_sum
        worst = 0.0
        for _, area in row:
            if area <= 0:
                continue
            r1 = (side_sq * area) / row_sum_sq
            r2 = row_sum_sq / (side_sq * area)
            worst = max(worst, max(r1, r2))
        return worst
