#!/usr/bin/env python3
# scripts/run_demo.py
from __future__ import annotations
import os
import sys
import json
import inspect
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple, Callable

# Make repo root importable so `import app...` works when running `python scripts/run_demo.py`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))



# Optional .env support (doesn't fail if not installed)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

try:
    import jsonschema
    from jsonschema import ValidationError
except Exception as e:
    print("ERROR: jsonschema is required. Install: pip install jsonschema", file=sys.stderr)
    raise


@dataclass
class CaseResult:
    case_file: str
    ok: bool
    output_file: Optional[str] = None
    raw_file: Optional[str] = None
    prompt_file: Optional[str] = None
    error: Optional[str] = None
    trace: Optional[str] = None
    validated: bool = False


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return _read_json(schema_path)


def _get_validator(schema: Dict[str, Any]) -> jsonschema.Validator:
    ValidatorCls = jsonschema.validators.validator_for(schema)
    ValidatorCls.check_schema(schema)
    return ValidatorCls(schema)


def _try_import_generator() -> Callable[[Dict[str, Any]], Any]:
    """
    Tries to import your project's generator.
    Expected locations (in order):
      - app.core.generator: generate_output(intake) -> dict
      - app/core/generator.py: generate_output_json(intake) -> dict
    """
    import importlib

    candidates: list[Tuple[str, str]] = [
        ("app.core.generator", "generate_output"),
        ("app.core.generator", "generate_output_json"),
        ("app.core.generator", "generate_output_from_intake"),
    ]

    last_err: Optional[Exception] = None
    for mod_name, fn_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn  # type: ignore[return-value]
        except Exception as e:
            last_err = e

    msg = (
        "Cannot import generator function.\n"
        "Expected: app/core/generator.py with one of functions: "
        "generate_output, generate_output_json, generate_output_from_intake.\n"
    )
    if last_err:
        msg += f"Last import error: {last_err}"
    raise RuntimeError(msg)

def _capture_raw_artifact(raw_dir: Path, case_stem: str) -> Optional[str]:
    """
    If your generator writes last_model_raw.txt (per earlier troubleshooting),
    we copy it into raw_dir with a per-case name.
    """
    src = Path("last_model_raw.txt")
    if not src.exists():
        return None
    raw_dir.mkdir(parents=True, exist_ok=True)
    dst = raw_dir / f"raw_{case_stem}.txt"
    try:
        dst.write_text(src.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        return str(dst.as_posix())
    except Exception:
        return None

def _capture_prompt_artifact(raw_dir: Path, case_stem: str) -> Optional[str]:
    """
    Copies last_model_prompt.txt (written by generator.py when SAVE_LAST_PROMPT=1)
    into raw_dir with a per-case name.
    """
    src = Path("last_model_prompt.txt")
    if not src.exists():
        return None
    raw_dir.mkdir(parents=True, exist_ok=True)
    dst = raw_dir / f"prompt_{case_stem}.txt"
    try:
        dst.write_text(src.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        return str(dst.as_posix())
    except Exception:
        return None

def _call_generator(generate_fn, intake: Dict[str, Any], output_schema: Dict[str, Any]) -> Any:
    """
    Calls generator with a compatible signature.

    Priority:
      1) (intake, output_schema, risk_level, risk_flags)
      2) (intake, output_schema, risk_level=..., risk_flags=...)
      3) shorter fallbacks (if project changes later)
    """
    risk = intake.get("risk_flags_rule_based") or {}
    risk_level = risk.get("risk_level") or "LOW"
    risk_flags = risk.get("flags") or []

    attempts = [
        # Most likely for your project:
        lambda: generate_fn(intake, output_schema, risk_level, risk_flags),
        lambda: generate_fn(intake, output_schema, risk_level=risk_level, risk_flags=risk_flags),

        # Fallbacks (just in case signature differs in some branches):
        lambda: generate_fn(intake, output_schema),
        lambda: generate_fn(intake, risk_level, risk_flags),
        lambda: generate_fn(intake, risk_level=risk_level, risk_flags=risk_flags),
        lambda: generate_fn(intake),
    ]

    last_err: Exception | None = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as e:
            last_err = e

    # If we got here, none of the signatures matched
    raise last_err if last_err else RuntimeError("Generator call failed for unknown reasons.")

def run_one_case(
    case_path: Path,
    out_dir: Path,
    raw_dir: Path,
    validator: jsonschema.Validator,
    generate_fn: Callable[[Dict[str, Any]], Any],
    output_schema: Dict[str, Any],
) -> CaseResult:
    case_stem = case_path.stem
    result = CaseResult(case_file=str(case_path.as_posix()), ok=False)

    try:
        intake = _read_json(case_path)

        # If missing attachments cause trouble in your pipeline, uncomment this:
        # intake["attachments"] = []

        output = _call_generator(generate_fn, intake, output_schema)

        # Some implementations may return (output, raw_text) or {"output":..., "raw":...}
        raw_text: Optional[str] = None
        if isinstance(output, tuple) and len(output) == 2:
            output, raw_text = output  # type: ignore[misc]
        elif isinstance(output, dict) and "output" in output and "raw" in output:
            raw_text = output.get("raw")  # type: ignore[assignment]
            output = output.get("output")  # type: ignore[assignment]

        if not isinstance(output, dict):
            raise TypeError(f"Generator returned non-dict output: {type(output)}")

        # Validate against schema
        validator.validate(output)
        result.validated = True

        # Save output_*.json
        out_path = out_dir / f"output_{case_stem}.json"
        _write_json(out_path, output)
        result.output_file = str(out_path.as_posix())

        # Save/copy RAW if we have it
        if raw_text:
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"raw_{case_stem}.txt"
            raw_path.write_text(raw_text, encoding="utf-8", errors="ignore")
            result.raw_file = str(raw_path.as_posix())
        else:
            # fallback: copy last_model_raw.txt if exists
            result.raw_file = _capture_raw_artifact(raw_dir, case_stem)            
        
        result.ok = True
        result.prompt_file = _capture_prompt_artifact(raw_dir, case_stem)
        return result

    except ValidationError as e:
        result.error = f"Schema validation failed: {e.message}"
        result.trace = traceback.format_exc(limit=3)
        result.raw_file = _capture_raw_artifact(raw_dir, case_stem)
        result.prompt_file = _capture_prompt_artifact(raw_dir, case_stem)
        return result

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.trace = traceback.format_exc(limit=5)
        result.raw_file = _capture_raw_artifact(raw_dir, case_stem)
        result.prompt_file = _capture_prompt_artifact(raw_dir, case_stem)
        return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Run demo cases end-to-end and validate outputs.")
    parser.add_argument("--cases_dir", default="data_demo/cases", help="Directory with intake cases (*.json)")
    parser.add_argument("--out_dir", default="data_demo/outputs", help="Where to write output_*.json")
    parser.add_argument("--raw_dir", default="data_demo/raw", help="Where to write/copy RAW model outputs")
    parser.add_argument("--schema", default="schemas/output.schema.json", help="Output JSON schema path")
    parser.add_argument("--report", default="data_demo/demo_report.json", help="Machine-readable report path")
    parser.add_argument("--report_md", default="data_demo/demo_report.md", help="Human-readable report path")
    args = parser.parse_args()
    # --- fail-fast: basic env sanity (no tokens) ---
    provider = (os.getenv("MODEL_PROVIDER") or "").strip()
    model_id = (os.getenv("MODEL_ID") or "").strip()

    if not provider:
        print("ERROR: MODEL_PROVIDER is empty. Set it in .env (e.g. MODEL_PROVIDER=transformers).", file=sys.stderr)
        return 2

    if provider == "transformers" and not model_id:
        print("ERROR: MODEL_ID is empty for MODEL_PROVIDER=transformers. Set MODEL_ID in .env.", file=sys.stderr)
        return 2

    # for demo runs: ensure prompt capture is on unless explicitly disabled
    os.environ.setdefault("SAVE_LAST_PROMPT", "1")
    # ----------------------------------------------
    cases_dir = Path(args.cases_dir)
    out_dir = Path(args.out_dir)
    raw_dir = Path(args.raw_dir)
    schema_path = Path(args.schema)

    if not cases_dir.exists():
        print(f"ERROR: cases_dir not found: {cases_dir}", file=sys.stderr)
        return 2

    schema = _load_schema(schema_path)
    validator = _get_validator(schema)
    generate_fn = _try_import_generator()

    case_files = sorted(cases_dir.glob("*.json"))
    if not case_files:
        print(f"ERROR: no cases found in {cases_dir}", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    results: list[CaseResult] = []
    ok_count = 0

    print(f"Running {len(case_files)} demo case(s)...")
    for p in case_files:
        r = run_one_case(p, out_dir, raw_dir, validator, generate_fn, schema)
        results.append(r)
        status = "OK" if r.ok else "FAILED"
        print(f"- {status}: {p.name}")
        if not r.ok:
            print(f"  reason: {r.error}")
            if r.raw_file:
                print(f"  raw:    {r.raw_file}")

        ok_count += 1 if r.ok else 0

    finished = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    run_config = {
        "MODEL_PROVIDER": (os.getenv("MODEL_PROVIDER") or "").strip(),
        "MODEL_ID": (os.getenv("MODEL_ID") or "").strip(),
        "MAX_NEW_TOKENS": (os.getenv("MAX_NEW_TOKENS") or "").strip(),
        "RETRIES": (os.getenv("RETRIES") or "").strip(),
        "SAVE_LAST_PROMPT": (os.getenv("SAVE_LAST_PROMPT") or "").strip(),
        "schema_path": str(schema_path.as_posix()),
}
    report_obj = {
        "started_at": started,
        "finished_at": finished,
        "run_config": run_config,
        "cases_total": len(case_files),
        "cases_ok": ok_count,
        "cases_failed": len(case_files) - ok_count,
        "results": [asdict(r) for r in results],
    }

    report_path = Path(args.report)
    _write_json(report_path, report_obj)

    # Markdown report (nice for README / CI logs)
    md_lines = [
        "# Demo run report",
        "",
        f"- started_at: `{started}`",
        f"- finished_at: `{finished}`",
        f"- total: **{len(case_files)}** | ok: **{ok_count}** | failed: **{len(case_files) - ok_count}**",
        "",
        "## Results",
        "",
        "| case | status | output | raw | error |",
        "|---|---:|---|---|---|",
    ]
    for r in results:
        status = "OK" if r.ok else "FAILED"
        md_lines.append(
            f"| `{Path(r.case_file).name}` | **{status}** | "
            f"{('`'+r.output_file+'`') if r.output_file else ''} | "
            f"{('`'+r.raw_file+'`') if r.raw_file else ''} | "
            f"{(r.error or '').replace('|','&#124;')} |"
        )

    report_md_path = Path(args.report_md)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("")
    print(f"Report: {report_path.as_posix()}")
    print(f"Report (md): {report_md_path.as_posix()}")
    print(f"Outputs: {out_dir.as_posix()}")
    print(f"RAW: {raw_dir.as_posix()}")

    return 0 if ok_count == len(case_files) else 1

if __name__ == "__main__":
    raise SystemExit(main())