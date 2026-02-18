import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

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
    return json.dumps({
        "summary": "Stub summary. Set MODEL_PROVIDER=transformers to run real model.",
        "draft_note": "Stub draft note. Facts only. Clinician review required.",
        "missing_info": ["MODEL_PROVIDER=stub — connect MedGemma to generate real output."],
        "followup_questions": [],
        "risk_level": "LOW",
        "risk_flags": [],
        "safety": {"no_diagnosis_or_treatment": True, "notes": ["Human-in-the-loop."]},
        "provenance": {"model_family": "stub", "model_variant": None, "prompt_version": "step5", "generated_at": _utc_now_iso()}
    }, ensure_ascii=False)


def _call_transformers(prompt: str, max_new_tokens: int) -> str:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    model_id = os.getenv("MODEL_ID", "").strip()
    if not model_id:
        raise RuntimeError("MODEL_PROVIDER=transformers requires MODEL_ID in .env")

    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype="auto")
    model.eval()

    inputs = tokenizer(prompt, return_tensors="pt")
    if hasattr(model, "device"):
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            top_p=1.0
        )

    gen_tokens = out[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
    return text.strip()


def generate_output(
    intake: Dict[str, Any],
    output_schema: Dict[str, Any],
    risk_level: str,
    risk_flags: list,
    prompts_dir: str = "prompts"
) -> Tuple[Dict[str, Any], str]:
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
        INTAKE_JSON=json.dumps(intake, ensure_ascii=False)
    )

    prompt = system_prompt.strip() + "\n\n" + user_prompt.strip()

    last_text = ""
    last_err = ""

    for _ in range(retries + 1):
        if provider == "stub":
            last_text = _call_stub(prompt)
        elif provider == "transformers":
            last_text = _call_transformers(prompt, max_new_tokens=max_new_tokens)
        else:
            raise RuntimeError(f"Unknown MODEL_PROVIDER: {provider}")

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
            obj["provenance"].setdefault("generated_at", _utc_now_iso())

            try:
                validate(instance=obj, schema=output_schema)
                return obj, last_text
            except ValidationError as e:
                last_err = f"Schema validation error: {e.message}"

        prompt = prompt + "\n\nReturn ONLY valid JSON that matches the schema. " + last_err

    raise RuntimeError(f"Failed to produce valid Output JSON. Last error: {last_err}")
