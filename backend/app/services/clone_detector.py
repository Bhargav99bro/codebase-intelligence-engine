import hashlib
import io
import keyword
import logging
import re
import tokenize
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# Keywords to strictly preserve across languages
COMMON_KEYWORDS = set(keyword.kwlist) | {
    "async", "await", "match", "case",
    # JavaScript & TypeScript keywords
    "abstract", "any", "as", "boolean", "break", "case", "catch", "class", "const",
    "constructor", "continue", "debugger", "declare", "default", "delete", "do",
    "else", "enum", "export", "extends", "false", "finally", "for", "from", "function",
    "get", "if", "implements", "import", "in", "instanceof", "interface", "let",
    "module", "namespace", "never", "new", "null", "number", "of", "package", "private",
    "protected", "public", "readonly", "require", "return", "set", "static", "string",
    "super", "switch", "symbol", "this", "throw", "true", "try", "type", "typeof",
    "undefined", "unknown", "var", "void", "while", "with", "yield",
}

# Regex for generic/JS/TS tokenization
JS_TOKEN_REGEX = re.compile(
    r"""
    (?P<COMMENT_LINE>//[^\n]*)
  | (?P<COMMENT_BLOCK>/\*[\s\S]*?\*/)
  | (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)
  | (?P<NUMBER>\b0x[0-9a-fA-F]+\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)
  | (?P<IDENT>[a-zA-Z_$][a-zA-Z0-9_$]*)
  | (?P<OP>===|!==|==|!=|<=|>=|=>|\+\+|--|\+=|-=|\*=|/=|&&|\|\||<<|>>|\*\*|[+\-*/%<>&|^!=~?:;,{}()\[\].])
  | (?P<WS>\s+)
""",
    re.VERBOSE,
)


@dataclass(slots=True)
class TokenInfo:
    text: str
    norm_text: str
    line: int
    col: int


@dataclass
class DuplicateMatch:
    clone_type: int
    source_file_path: str
    source_start_line: int
    source_end_line: int
    target_file_path: str
    target_start_line: int
    target_end_line: int
    line_count: int
    token_count: int
    checksum: str
    source_snippet: Optional[str] = None
    target_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clone_type": self.clone_type,
            "source_file_path": self.source_file_path,
            "source_start_line": self.source_start_line,
            "source_end_line": self.source_end_line,
            "target_file_path": self.target_file_path,
            "target_start_line": self.target_start_line,
            "target_end_line": self.target_end_line,
            "line_count": self.line_count,
            "token_count": self.token_count,
            "checksum": self.checksum,
            "source_snippet": self.source_snippet,
            "target_snippet": self.target_snippet,
        }


@dataclass
class DuplicationResult:
    duplicates: List[DuplicateMatch]
    duplicate_blocks_count: int
    duplicate_lines_count: int
    duplication_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duplicates": [d.to_dict() for d in self.duplicates],
            "duplicate_blocks_count": self.duplicate_blocks_count,
            "duplicate_lines_count": self.duplicate_lines_count,
            "duplication_ratio": self.duplication_ratio,
        }


class CloneDetector:
    """Type-1 and Type-2 static code clone detection engine using Karp-Rabin 64-bit rolling hash."""

    MIN_LINES = 10
    MIN_TOKENS = 40
    WINDOW_SIZE = 40
    MAX_PERSISTED_PAIRS = 10000

    # Karp-Rabin constants
    PRIME_BASE = 313
    PRIME_MOD = (1 << 64) - 59  # 64-bit prime

    def __init__(self, min_lines: int = 10, min_tokens: int = 40) -> None:
        self.min_lines = min_lines
        self.min_tokens = min_tokens
        self.window_size = min_tokens
        self._vocab: Dict[str, int] = {}
        self._vocab_counter = 1

    def _get_token_id(self, token_str: str) -> int:
        tid = self._vocab.get(token_str)
        if tid is None:
            tid = self._vocab_counter
            self._vocab[token_str] = tid
            self._vocab_counter += 1
        return tid

    def tokenize_python(self, content: str, file_path: str) -> List[TokenInfo]:
        tokens: List[TokenInfo] = []
        try:
            reader = io.StringIO(content).readline
            in_import = False
            for tok in tokenize.generate_tokens(reader):
                ttype = tok.type
                tstring = tok.string
                sline, scol = tok.start

                if ttype in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                    if ttype in (tokenize.NEWLINE, tokenize.NL):
                        in_import = False
                    continue

                if ttype == tokenize.NAME:
                    if tstring in ("import", "from"):
                        in_import = True
                        norm = tstring
                    elif in_import:
                        norm = tstring  # Preserve imported module and symbol names
                    elif tstring in COMMON_KEYWORDS:
                        norm = tstring
                    else:
                        norm = "_ID_"
                elif ttype == tokenize.NUMBER:
                    norm = "_LIT_"
                elif ttype == tokenize.STRING:
                    norm = "_LIT_"
                elif ttype == tokenize.OP:
                    norm = tstring
                    if tstring in (";",):
                        in_import = False
                else:
                    norm = tstring

                tokens.append(TokenInfo(text=tstring, norm_text=norm, line=sline, col=scol))
        except Exception as exc:
            logger.debug("Python tokenize failed on %s: %s", file_path, exc)
            return self.tokenize_generic(content, file_path)

        return tokens

    def tokenize_generic(self, content: str, file_path: str) -> List[TokenInfo]:
        tokens: List[TokenInfo] = []
        in_import = False
        current_line = 1

        for match in JS_TOKEN_REGEX.finditer(content):
            group = match.lastgroup
            val = match.group()

            # Track newlines accurately
            newlines = val.count("\n")

            if group in ("COMMENT_LINE", "COMMENT_BLOCK", "WS"):
                current_line += newlines
                if "\n" in val:
                    in_import = False
                continue

            start_col = match.start()
            line = current_line
            current_line += newlines

            if group == "IDENT":
                if val in ("import", "from", "require"):
                    in_import = True
                    norm = val
                elif in_import:
                    norm = val
                elif val in COMMON_KEYWORDS:
                    norm = val
                else:
                    norm = "_ID_"
            elif group in ("NUMBER", "STRING"):
                norm = "_LIT_"
            elif group == "OP":
                norm = val
                if val == ";":
                    in_import = False
            else:
                norm = val

            tokens.append(TokenInfo(text=val, norm_text=norm, line=line, col=start_col))

        return tokens

    def tokenize_file(self, content: str, file_path: str) -> List[TokenInfo]:
        if file_path.endswith((".py", ".pyi")):
            return self.tokenize_python(content, file_path)
        return self.tokenize_generic(content, file_path)

    def detect_clones(
        self,
        files_content: Dict[str, str],
        total_sloc: int = 0,
    ) -> DuplicationResult:
        """Runs Type-1 and Type-2 clone detection across provided repository files."""
        # 1. Tokenize all files
        file_tokens: Dict[str, List[TokenInfo]] = {}
        for fpath, content in sorted(files_content.items()):
            toks = self.tokenize_file(content, fpath)
            if len(toks) >= self.min_tokens:
                file_tokens[fpath] = toks

        # 2. Build Karp-Rabin rolling hash index over sliding windows of size W
        W = self.window_size
        B = self.PRIME_BASE
        M = self.PRIME_MOD
        B_W1 = pow(B, W - 1, M)

        hash_index: Dict[int, List[Tuple[str, int]]] = {}

        for fpath, toks in file_tokens.items():
            n = len(toks)
            if n < W:
                continue

            # Compute initial rolling hash for window [0..W-1]
            curr_hash = 0
            for i in range(W):
                tid = self._get_token_id(toks[i].norm_text)
                curr_hash = (curr_hash * B + tid) % M

            hash_index.setdefault(curr_hash, []).append((fpath, 0))

            # Roll hash forward
            for i in range(1, n - W + 1):
                old_tid = self._get_token_id(toks[i - 1].norm_text)
                new_tid = self._get_token_id(toks[i + W - 1].norm_text)
                curr_hash = ((curr_hash - old_tid * B_W1) * B + new_tid) % M
                hash_index.setdefault(curr_hash, []).append((fpath, i))

        # 3. Seed match evaluation with exact token collision defense and greedy expansion
        raw_matches: List[DuplicateMatch] = []
        seen_pairs: Set[Tuple[str, int, str, int]] = set()

        max_bucket_size = getattr(settings, "MAX_CANDIDATE_BUCKET_SIZE", 100)
        max_pairs_cap = getattr(settings, "MAX_CLONE_PAIRS_CAP", self.MAX_PERSISTED_PAIRS)

        for hval, occurrences in hash_index.items():
            if len(occurrences) < 2:
                continue

            if len(occurrences) > max_bucket_size:
                occurrences = occurrences[:max_bucket_size]

            if len(raw_matches) >= max_pairs_cap:
                logger.warning("Reached maximum clone pairs cap (%d); halting candidate evaluation.", max_pairs_cap)
                break

            # Check pairs
            for idx_a in range(len(occurrences)):
                fpath_a, pos_a = occurrences[idx_a]
                toks_a = file_tokens[fpath_a]

                for idx_b in range(idx_a + 1, len(occurrences)):
                    fpath_b, pos_b = occurrences[idx_b]
                    toks_b = file_tokens[fpath_b]

                    # Collision defense: exact token-by-token comparison
                    match_exact = True
                    for k in range(W):
                        if toks_a[pos_a + k].norm_text != toks_b[pos_b + k].norm_text:
                            match_exact = False
                            break

                    if not match_exact:
                        continue

                    # Greedy expansion to the left
                    left_ext = 0
                    while (
                        pos_a - left_ext > 0
                        and pos_b - left_ext > 0
                        and toks_a[pos_a - left_ext - 1].norm_text == toks_b[pos_b - left_ext - 1].norm_text
                    ):
                        left_ext += 1

                    # Greedy expansion to the right
                    right_ext = 0
                    while (
                        pos_a + W + right_ext < len(toks_a)
                        and pos_b + W + right_ext < len(toks_b)
                        and toks_a[pos_a + W + right_ext].norm_text == toks_b[pos_b + W + right_ext].norm_text
                    ):
                        right_ext += 1

                    start_a = pos_a - left_ext
                    end_a = pos_a + W + right_ext
                    start_b = pos_b - left_ext
                    end_b = pos_b + W + right_ext

                    matched_tokens = end_a - start_a
                    if matched_tokens < self.min_tokens:
                        continue

                    src_f, src_s_tok, src_e_tok = fpath_a, start_a, end_a
                    tgt_f, tgt_s_tok, tgt_e_tok = fpath_b, start_b, end_b

                    # Canonical order: (src_file, src_tok) <= (tgt_file, tgt_tok)
                    if (src_f > tgt_f) or (src_f == tgt_f and src_s_tok > tgt_s_tok):
                        src_f, tgt_f = tgt_f, src_f
                        src_s_tok, tgt_s_tok = tgt_s_tok, src_s_tok
                        src_e_tok, tgt_e_tok = tgt_e_tok, src_e_tok

                    src_toks = file_tokens[src_f]
                    tgt_toks = file_tokens[tgt_f]

                    src_start_line = src_toks[src_s_tok].line
                    src_end_line = src_toks[src_e_tok - 1].line
                    tgt_start_line = tgt_toks[tgt_s_tok].line
                    tgt_end_line = tgt_toks[tgt_e_tok - 1].line

                    src_line_cnt = src_end_line - src_start_line + 1
                    tgt_line_cnt = tgt_end_line - tgt_start_line + 1
                    line_count = max(src_line_cnt, tgt_line_cnt)

                    if line_count < self.min_lines:
                        continue

                    # Same-file non-overlapping condition
                    if src_f == tgt_f:
                        if tgt_start_line <= src_end_line:
                            continue

                    pair_key = (src_f, src_start_line, tgt_f, tgt_start_line)
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    # Determine clone type: Type-1 (identical raw text) vs Type-2
                    is_type1 = all(
                        src_toks[src_s_tok + k].text == tgt_toks[tgt_s_tok + k].text
                        for k in range(matched_tokens)
                    )
                    clone_type = 1 if is_type1 else 2

                    # Checksum of normalized tokens
                    norm_slice_str = "".join(t.norm_text for t in src_toks[src_s_tok:src_e_tok])
                    csum = hashlib.sha256(norm_slice_str.encode("utf-8")).hexdigest()

                    # Extract snippets
                    src_snip = self._extract_snippet(files_content.get(src_f, ""), src_start_line, src_end_line)
                    tgt_snip = self._extract_snippet(files_content.get(tgt_f, ""), tgt_start_line, tgt_end_line)

                    raw_matches.append(
                        DuplicateMatch(
                            clone_type=clone_type,
                            source_file_path=src_f,
                            source_start_line=src_start_line,
                            source_end_line=src_end_line,
                            target_file_path=tgt_f,
                            target_start_line=tgt_start_line,
                            target_end_line=tgt_end_line,
                            line_count=line_count,
                            token_count=matched_tokens,
                            checksum=csum,
                            source_snippet=src_snip,
                            target_snippet=tgt_snip,
                        )
                    )

        # 4. Greedy merge overlapping/adjacent matches
        merged_matches = self._merge_matches(raw_matches)

        # 5. Deterministic sorting and retention cap
        # Sort by: -line_count, source_file_path, source_start_line, target_file_path, target_start_line
        merged_matches.sort(
            key=lambda m: (
                -m.line_count,
                m.source_file_path,
                m.source_start_line,
                m.target_file_path,
                m.target_start_line,
            )
        )
        retained = merged_matches[: max_pairs_cap]

        # 6. Calculate union of duplicated lines per file to prevent over-counting
        file_intervals: Dict[str, List[Tuple[int, int]]] = {}
        for m in retained:
            file_intervals.setdefault(m.source_file_path, []).append((m.source_start_line, m.source_end_line))
            file_intervals.setdefault(m.target_file_path, []).append((m.target_start_line, m.target_end_line))

        duplicate_lines_count = 0
        for fpath, intervals in file_intervals.items():
            intervals.sort(key=lambda x: (x[0], x[1]))
            merged_intervals: List[Tuple[int, int]] = []
            for s, e in intervals:
                if not merged_intervals:
                    merged_intervals.append((s, e))
                else:
                    last_s, last_e = merged_intervals[-1]
                    if s <= last_e + 1:
                        merged_intervals[-1] = (last_s, max(last_e, e))
                    else:
                        merged_intervals.append((s, e))

            duplicate_lines_count += sum(e - s + 1 for s, e in merged_intervals)

        # Duplication ratio
        if total_sloc > 0:
            dup_ratio = round(min(100.0, (duplicate_lines_count / total_sloc) * 100.0), 2)
        else:
            dup_ratio = 0.0

        # Clean up internal token caches to free memory immediately
        file_tokens.clear()
        hash_index.clear()
        seen_pairs.clear()
        raw_matches.clear()
        merged_matches.clear()
        self._vocab.clear()
        self._vocab_counter = 1

        return DuplicationResult(
            duplicates=retained,
            duplicate_blocks_count=len(retained),
            duplicate_lines_count=duplicate_lines_count,
            duplication_ratio=dup_ratio,
        )

    def _extract_snippet(self, content: str, start_line: int, end_line: int, max_lines: int = 50) -> str:
        lines = content.splitlines()
        s = max(0, start_line - 1)
        e = min(len(lines), end_line)
        slice_lines = lines[s:e]
        if len(slice_lines) > max_lines:
            slice_lines = slice_lines[:max_lines] + ["... [truncated]"]
        return "\n".join(slice_lines)

    def _merge_matches(self, matches: List[DuplicateMatch]) -> List[DuplicateMatch]:
        """Merges duplicate matches that heavily overlap or are subsumed."""
        if not matches:
            return []

        # Sort by (src_f, tgt_f, src_start_line, tgt_start_line, -line_count)
        matches.sort(
            key=lambda m: (
                m.source_file_path,
                m.target_file_path,
                m.source_start_line,
                m.target_start_line,
                -m.line_count,
            )
        )

        merged: List[DuplicateMatch] = []
        for m in matches:
            subsumed = False
            for existing in merged:
                if (
                    existing.source_file_path == m.source_file_path
                    and existing.target_file_path == m.target_file_path
                ):
                    # Check if m is contained within existing
                    if (
                        existing.source_start_line <= m.source_start_line
                        and existing.source_end_line >= m.source_end_line
                        and existing.target_start_line <= m.target_start_line
                        and existing.target_end_line >= m.target_end_line
                    ):
                        subsumed = True
                        break
            if not subsumed:
                merged.append(m)

        return merged
