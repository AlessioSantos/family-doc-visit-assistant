import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple


EXPECTED_KEYS = {
    "summary",
    "draft_note",
    "missing_info",
    "followup_questions",
    "safety",
    "provenance",
    "risk_level",
    "risk_flags",
}


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    # remove ```json / ``` fences, keep inner content
    text = re.sub(r"```(?:json|JSON)?", "", text)
    text = text.replace("```", "")
    return text.strip()


def _scan_top_level_json_object_spans(text: str) -> List[Tuple[int, int]]:
    """
    Returns spans (start, end_exclusive) for every top-level {...} JSON-like object.
    Uses brace balancing with string/escape awareness.
    """
    spans: List[Tuple[int, int]] = []
    depth = 0
    start = None

    in_str = False
    esc = False

    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        # not in string
        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append((start, i + 1))
                    start = None

    return spans


def _parse_candidate(candidate: str) -> Optional[Dict[str, Any]]:
    """
    Try parse candidate as JSON dict; fallback to ast.literal_eval for dict-like outputs.
    Returns dict or None.
    """
    candidate = candidate.strip()
    if not candidate.startswith("{") or not candidate.endswith("}"):
        return None

    # 1) strict JSON
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        pass

    # 2) python dict-like (single quotes, True/False/None)
    try:
        obj = ast.literal_eval(candidate)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        return None


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the *best* JSON object from model output.
    - Strips code fences
    - Finds ALL top-level {...} objects
    - Prefers the LAST object that matches expected output keys
      (important when prompt contains an earlier JSON skeleton)
    """
    if not text:
        return None

    text = _strip_code_fences(text)

    spans = _scan_top_level_json_object_spans(text)
    if not spans:
        return None

    parsed: List[Dict[str, Any]] = []
    for s, e in spans:
        cand = text[s:e]
        obj = _parse_candidate(cand)
        if isinstance(obj, dict):
            parsed.append(obj)

    if not parsed:
        return None

    # Prefer the last object that looks like Output JSON
    for obj in reversed(parsed):
        keys = set(obj.keys())
        # must have core keys; allow some missing but prefer more matches
        core = {"summary", "draft_note", "missing_info", "followup_questions", "safety", "provenance"}
        if core.issubset(keys):
            return obj

    # Otherwise: pick the object with the most expected keys
    best = max(parsed, key=lambda o: len(set(o.keys()) & EXPECTED_KEYS))
    return best