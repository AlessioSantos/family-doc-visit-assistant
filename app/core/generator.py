import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple
import streamlit as st

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from .json_utils import extract_json_object


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _render_template(tpl: str, **kwargs) -> str:
    out = tpl
    for k, v in kwargs.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _call_stub(prompt: str) -> str:
    return json.dumps(
        {
            "summary": "Stub summary. Set MODEL_PROVIDER=transformers to run real model.",
            "draft_note": "Stub draft note. Facts only. Clinician review required.\n\nPLAN (do uzupełnienia przez lekarza):\n- [ ]",
            "missing_info": ["MODEL_PROVIDER=stub — connect MedGemma to generate real output."],
            "followup_questions": [],
            "risk_level": "LOW",
            "risk_flags": [],
            "safety": {"no_diagnosis_or_treatment": True, "notes": ["Human-in-the-loop."]},
            "provenance": {
                "model_family": "stub",
                "model_variant": None,
                "prompt_version": "step5",
                "generated_at": _utc_now_iso(),
            },
        },
        ensure_ascii=False,
    )


# --- caching for Streamlit reruns ---
try:
    import streamlit as st
    _cache_resource = st.cache_resource
except Exception:
    _cache_resource = None

def _load_model_tok(model_id: str):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_TOKEN")

    tok = AutoTokenizer.from_pretrained(model_id, use_fast=True, token=token)
    mdl = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype="auto",
        token=token,
    )
    mdl.eval()
    return tok, mdl

if _cache_resource:
    @_cache_resource(show_spinner=False)
    def _get_model_and_tokenizer(model_id: str):
        return _load_model_tok(model_id)
else:
    @lru_cache(maxsize=1)
    def _get_model_and_tokenizer(model_id: str):
        return _load_model_tok(model_id)

def _call_transformers(system_prompt: str, user_prompt: str, max_new_tokens: int) -> str:
    import torch

    model_id = os.getenv("MODEL_ID", "").strip()
    if not model_id:
        raise RuntimeError("MODEL_PROVIDER=transformers requires MODEL_ID in .env")

    token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_TOKEN")

    tokenizer, model = _get_model_and_tokenizer(model_id)

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]

    # IMPORTANT: chat template for Gemma/MedGemma
    if getattr(tokenizer, "chat_template", None):
        prompt_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt_text = system_prompt.strip() + "\n\n" + user_prompt.strip()

    inputs = tokenizer(prompt_text, return_tensors="pt", add_special_tokens=True)

    # Move tensors to model device
    try:
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
    except Exception:
        pass

    input_len = inputs["input_ids"].shape[1]

    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            top_p=1.0,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            max_time=60,
        )

    # Decode ONLY generated tokens (not the prompt)
    gen_tokens = out[0][input_len:]
    text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
    return text.strip()


_TREATMENT_RE = re.compile(
    r"\b("
    r"zalec\w*|zaleceni\w*|leczen\w*|lecz\w*|terapi\w*|"
    r"dawk\w*|podaw\w*|przyjm\w*|antybiotyk\w*|"
    r"ibuprofen\w*|paracetamol\w*|syrop\w*|"
    r"włącz\w*|odstaw\w*|zastosow\w*|"
    r"treatment|dose|dosing|recommend\w*|prescrib\w*"
    r")\b",
    re.IGNORECASE,
)


def _strip_treatment_sentences(text: str) -> str:
    if not text:
        return text
    # Split into sentences; keep those without treatment-like language
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [s for s in parts if s and not _TREATMENT_RE.search(s)]
    return " ".join(kept).strip()


def _ensure_plan_placeholder(note: str) -> str:
    if not note:
        note = ""
    if "PLAN" in note.upper():
        return note.strip()
    suffix = "\n\nPLAN (do uzupełnienia przez lekarza):\n- [ ]"
    return (note.strip() + suffix).strip()


def generate_output(
    intake: Dict[str, Any],
    output_schema: Dict[str, Any],
    risk_level: str,
    risk_flags: list,
    prompts_dir: str = "prompts",
) -> Tuple[Dict[str, Any], str]:
    """
    Returns (output_json, raw_model_text)
    Enforces JSON-only output and schema validation with retries.
    """
    provider = os.getenv("MODEL_PROVIDER", "stub").strip().lower()
    retries = int(os.getenv("RETRIES", "2"))
    max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "800"))

    system_path = os.path.join(prompts_dir, "system.md")
    user_path = os.path.join(prompts_dir, "user_template.md")
    system_prompt = _load_text(system_path)
    user_tpl = _load_text(user_path)

    user_prompt = _render_template(
        user_tpl,
        RISK_LEVEL=risk_level,
        RISK_FLAGS=json.dumps(risk_flags, ensure_ascii=False),
        INTAKE_JSON=json.dumps(intake, ensure_ascii=False),
    )

    last_text = ""
    last_err = ""

    for _attempt in range(retries + 1):
        # Generate
        if provider == "stub":
            full_prompt = system_prompt.strip() + "\n\n" + user_prompt.strip()
            last_text = _call_stub(full_prompt)
        elif provider == "transformers":
            last_text = _call_transformers(system_prompt, user_prompt, max_new_tokens=max_new_tokens)
        else:
            raise RuntimeError(f"Unknown MODEL_PROVIDER: {provider}")

        # Extract JSON
        obj = extract_json_object(last_text)
        if obj is None:
            last_err = "No valid JSON object found."
        else:
            # Force risk + safety fields (model must not override)
            obj["risk_level"] = risk_level
            obj["risk_flags"] = risk_flags
            obj.setdefault("safety", {})
            obj["safety"]["no_diagnosis_or_treatment"] = True
            obj.setdefault("provenance", {})
            obj["provenance"].setdefault("model_family", provider)
            obj["provenance"].setdefault("prompt_version", "step5")
            obj["provenance"]["generated_at"] = _utc_now_iso()

            # Variant A: keep draft_note factual; remove treatment-like sentences; add empty PLAN
            original_note = obj.get("draft_note", "")
            cleaned_note = _strip_treatment_sentences(original_note)
            cleaned_note = _ensure_plan_placeholder(cleaned_note)
            obj["draft_note"] = cleaned_note

            # Optional: also keep summary factual (no treatment-like sentences)
            obj["summary"] = _strip_treatment_sentences(obj.get("summary", ""))

            obj["safety"].setdefault("notes", [])
            obj["safety"]["notes"].append("Plan section is a placeholder; clinician must fill in. Treatment-like language removed from AI draft.")

            try:
                validate(instance=obj, schema=output_schema)
                return obj, last_text
            except ValidationError as e:
                last_err = f"Schema validation error: {e.message}"

        # Retry: tighten instructions by appending to USER prompt
        user_prompt = user_prompt + "\n\nIMPORTANT: Return ONLY one valid JSON object. First char '{' last char '}'. " + last_err

    # Save RAW for debugging
    Path("last_model_raw.txt").write_text(last_text or "", encoding="utf-8", errors="ignore")
    raise RuntimeError(
        f"Failed to produce valid Output JSON. Last error: {last_err}. Saved RAW to last_model_raw.txt"
    )