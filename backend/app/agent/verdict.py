"""Verdict phase: prompt for JSON -> parse -> Pydantic validate -> repair (capped).

The proxy ignores `response_format`, so the JSON contract is enforced here, not by the API.
"""

import json
import re

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agent.prompts import REPAIR, VERDICT_SYSTEM, wrap_message
from app.api.schemas import RiskLevel, ScamType, Verdict


class VerdictError(RuntimeError):
    pass


def extract_json(text: str) -> dict:
    """Pull the first {...} object out of a reply that may carry fences or prose around it."""
    text = re.sub(r"```(?:json)?", "", text or "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    obj = json.loads(text[start : end + 1])
    if not isinstance(obj, dict):
        raise TypeError("top-level JSON is not an object")
    return obj


def ground_quotes(verdict: Verdict, message: str) -> Verdict:
    """Drop quotes that are not verbatim in the message — the UI highlights them, so they must exist."""
    for flag in verdict.red_flags:
        if flag.quote is not None and (not flag.quote.strip() or flag.quote not in message):
            flag.quote = None
    return verdict


def apply_evidence_floor(verdict: Verdict, strong: list[str]) -> Verdict:
    """Deterministic guardrail: hard tool evidence (lookalike domain, mixed-script host, reported
    indicator) means high risk, whatever the model wrote. The model still writes the explanation."""
    if not strong:
        return verdict
    data = verdict.model_dump()
    data["risk_level"] = RiskLevel.high
    if verdict.scam_type is ScamType.legit:
        data["scam_type"] = ScamType.phishing_link
    have = {f.text for f in verdict.red_flags}
    data["red_flags"] = [*data["red_flags"], *({"text": s, "quote": None} for s in strong if s not in have)]
    return Verdict.model_validate(data)


async def produce_verdict(
    client: AsyncOpenAI, model: str, message: str, evidence: str, max_repairs: int, advisories: str = ""
) -> tuple[Verdict, int]:
    """Returns the validated verdict and how many repair rounds it took."""
    messages = [
        {"role": "system", "content": VERDICT_SYSTEM},
        {"role": "user", "content": f"{wrap_message(message)}\n\n<evidence>\n{evidence}\n</evidence>"
                                    f"\n\n<advisories>\n{advisories or '(none)'}\n</advisories>"},
    ]
    last_error = ""
    for attempt in range(max_repairs + 1):
        r = await client.chat.completions.create(model=model, temperature=0, messages=messages)
        raw = r.choices[0].message.content or ""
        try:
            verdict = Verdict.model_validate(extract_json(raw))
            verdict.citations = []  # citations are attached by code from retrieval, never by the model
            return ground_quotes(verdict, message), attempt
        except (ValueError, TypeError, ValidationError) as e:  # JSONDecodeError is a ValueError
            last_error = str(e)[:600]
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": REPAIR.format(error=last_error)},
            ]
    raise VerdictError(f"model did not return a valid verdict after {max_repairs} repairs: {last_error}")
