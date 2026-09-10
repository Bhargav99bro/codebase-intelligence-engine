import random
import pytest
from app.services.treemap_builder import TreemapBuilder, TreemapNode


def test_treemap_hierarchy_construction():
    files = [
        {"path": "backend/app/main.py", "sloc": 1200, "maintainability_score": 65.0, "max_cyclomatic_complexity": 18, "issues": [{"severity": "major"}]},
        {"path": "backend/app/models/user.py", "sloc": 300, "maintainability_score": 85.0, "max_cyclomatic_complexity": 4, "issues": []},
        {"path": "backend/app/models/order.py", "sloc": 500, "maintainability_score": 75.0, "max_cyclomatic_complexity": 8, "issues": [{"severity": "minor"}]},
        {"path": "frontend/src/index.tsx", "sloc": 400, "maintainability_score": 80.0, "max_cyclomatic_complexity": 6, "issues": []},
    ]

    root = TreemapBuilder.build_hierarchy(files, compute_layout=True)
    assert root.name == "root"
    assert root.node_type == "directory"
    # Total SLOC rollup
    assert root.sloc == 1200 + 300 + 500 + 400
    assert root.file_count == 4

    # Top level directories: backend and frontend
    child_names = [c.name for c in root.children]
    # 'backend' (2000 sloc) must be ordered before 'frontend' (400 sloc)
    assert child_names == ["backend", "frontend"]


def test_treemap_deterministic_child_ordering():
    # Test that equal SLOC children are ordered alphabetically by path
    files = [
        {"path": "src/z_service.py", "sloc": 500},
        {"path": "src/a_service.py", "sloc": 500},
        {"path": "src/m_service.py", "sloc": 500},
        {"path": "src/heavy.py", "sloc": 1000},
    ]

    root = TreemapBuilder.build_hierarchy(files, compute_layout=False)
    src_dir = root.children[0]
    assert src_dir.name == "src"

    ordered_paths = [c.path for c in src_dir.children]
    # heavy.py (1000 sloc) first, then alphabetical among 500 sloc: a, m, z
    assert ordered_paths == [
        "src/heavy.py",
        "src/a_service.py",
        "src/m_service.py",
        "src/z_service.py",
    ]


def test_treemap_layout_repeatability_on_shuffled_inputs():
    files = [
        {"path": f"module_{i}/file_{j}.py", "sloc": (i * 10 + j) * 50, "maintainability_score": 70.0}
        for i in range(1, 6)
        for j in range(1, 4)
    ]

    base_root = TreemapBuilder.build_hierarchy(files, compute_layout=True)
    base_dict = base_root.to_dict()

    for seed in (10, 42, 100, 555, 999):
        shuffled = list(files)
        random.seed(seed)
        random.shuffle(shuffled)
        shuffled_root = TreemapBuilder.build_hierarchy(shuffled, compute_layout=True)
        shuffled_dict = shuffled_root.to_dict()

        # Layout rectangle coordinates and structure must match bit-for-bit
        def assert_nodes_equal(n1, n2):
            assert n1["name"] == n2["name"]
            assert n1["path"] == n2["path"]
            assert n1["sloc"] == n2["sloc"]
            assert n1.get("x") == n2.get("x")
            assert n1.get("y") == n2.get("y")
            assert n1.get("width") == n2.get("width")
            assert n1.get("height") == n2.get("height")
            c1 = n1.get("children", [])
            c2 = n2.get("children", [])
            assert len(c1) == len(c2)
            for child1, child2 in zip(c1, c2):
                assert_nodes_equal(child1, child2)

        assert_nodes_equal(base_dict, shuffled_dict)


def test_treemap_single_file_and_empty():
    # Empty files list
    empty_root = TreemapBuilder.build_hierarchy([])
    assert empty_root.sloc == 0
    assert len(empty_root.children) == 0

    # Single file
    single = [{"path": "solo.py", "sloc": 120}]
    single_root = TreemapBuilder.build_hierarchy(single, compute_layout=True)
    assert single_root.sloc == 120
    assert len(single_root.children) == 1
    assert single_root.children[0].name == "solo.py"
    assert single_root.children[0].node_type == "file"
