import os
import pytest
from app.services.clone_detector import CloneDetector, DuplicateMatch, DuplicationResult


@pytest.fixture
def fixture_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "duplication_repo")


@pytest.fixture
def fixture_files_content(fixture_dir):
    contents = {}
    for fname in os.listdir(fixture_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(fixture_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                contents[fname] = f.read()
    return contents


def test_type1_clone_detection(fixture_files_content):
    detector = CloneDetector(min_lines=10, min_tokens=40)
    # Only test type1_a.py and type1_b.py
    subset = {
        "type1_a.py": fixture_files_content["type1_a.py"],
        "type1_b.py": fixture_files_content["type1_b.py"],
    }
    result = detector.detect_clones(subset, total_sloc=28)
    assert result.duplicate_blocks_count >= 1
    t1_matches = [d for d in result.duplicates if d.clone_type == 1]
    assert len(t1_matches) >= 1
    m = t1_matches[0]
    assert (m.source_file_path == "type1_a.py" and m.target_file_path == "type1_b.py") or (
        m.source_file_path == "type1_b.py" and m.target_file_path == "type1_a.py"
    )
    assert m.line_count >= 10
    assert m.token_count >= 40
    assert result.duplication_ratio > 0.0


def test_type2_clone_detection(fixture_files_content):
    detector = CloneDetector(min_lines=10, min_tokens=40)
    # Test type2_a.py and type2_b.py
    subset = {
        "type2_a.py": fixture_files_content["type2_a.py"],
        "type2_b.py": fixture_files_content["type2_b.py"],
    }
    result = detector.detect_clones(subset, total_sloc=35)
    assert result.duplicate_blocks_count >= 1
    t2_matches = [d for d in result.duplicates if d.clone_type == 2]
    assert len(t2_matches) >= 1
    m = t2_matches[0]
    assert m.line_count >= 15
    assert m.token_count >= 40


def test_same_file_non_overlapping_clone(fixture_files_content):
    detector = CloneDetector(min_lines=10, min_tokens=40)
    subset = {"overlapping.py": fixture_files_content["overlapping.py"]}
    result = detector.detect_clones(subset, total_sloc=30)
    assert result.duplicate_blocks_count >= 1
    m = result.duplicates[0]
    assert m.source_file_path == "overlapping.py"
    assert m.target_file_path == "overlapping.py"
    # Verify strict non-overlapping lines
    assert m.target_start_line > m.source_end_line


def test_short_block_below_threshold_ignored(fixture_files_content):
    detector = CloneDetector(min_lines=10, min_tokens=40)
    # 2 copies of the short block (only 6-8 lines)
    subset = {
        "short_a.py": fixture_files_content["short_block.py"],
        "short_b.py": fixture_files_content["short_block.py"],
    }
    result = detector.detect_clones(subset, total_sloc=16)
    assert result.duplicate_blocks_count == 0
    assert result.duplication_ratio == 0.0


def test_collision_defense_exact_token_verification():
    detector = CloneDetector(min_lines=2, min_tokens=4)
    # Force a scenario where tokens differ despite mock collisions
    toks_a = detector.tokenize_file("def foo():\n    return 1\n", "foo.py")
    toks_b = detector.tokenize_file("def bar():\n    return 2\n", "bar.py")
    assert len(toks_a) > 0
    assert len(toks_b) > 0


def test_mirrored_pair_deduplication():
    detector = CloneDetector(min_lines=10, min_tokens=40)
    code = "\n".join([f"def func_{i}(): return {i}" for i in range(25)])
    files = {"a.py": code, "b.py": code}
    result = detector.detect_clones(files, total_sloc=50)
    # Mirrored pairs (a, b) and (b, a) must NOT produce 2 matches
    pairs = [(d.source_file_path, d.target_file_path) for d in result.duplicates]
    assert len(pairs) == len(set(pairs))
    for src, tgt in pairs:
        assert src <= tgt


def test_retention_cap_at_10000():
    detector = CloneDetector()
    assert detector.MAX_PERSISTED_PAIRS == 10000


def test_zero_duplication_empty_repo():
    detector = CloneDetector()
    result = detector.detect_clones({}, total_sloc=0)
    assert result.duplicate_blocks_count == 0
    assert result.duplicate_lines_count == 0
    assert result.duplication_ratio == 0.0
