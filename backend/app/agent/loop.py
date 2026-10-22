"""Agent loop: native tool calling with a step cap and a duplicate-call guard, then the verdict phase.

Yields event dicts matching the SSE contract in app/services/scan_service.py.
"""

import json
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.agent.precheck import precheck
from app.agent.prompts import TOOL_SYSTEM, wrap_message
from app.agent.tools import Toolbox
from app.agent.verdict import apply_evidence_floor, produce_verdict
from app.api.schemas import Citation, RiskLevel


async def run_agent(
    client: AsyncOpenAI,
    toolbox: Toolbox,
    message: str,
    *,
    model: str,
    max_steps: int,
    max_repairs: int,
    use_tools: bool = True,
) -> AsyncIterator[dict]:
    """use_tools=False is the zero-shot baseline: same verdict prompt, no evidence gathering."""
    trail: list[str] = []
    if use_tools and toolbox.brands:  # code-level link/brand check; the zero-shot baseline gets none
        trail += [f"precheck: {line}" for line in precheck(message, toolbox.brands).evidence]
    strong: list[str] = []  # evidence that forces a high-risk verdict (see apply_evidence_floor)
    citations: list[dict] = []
    advisories: list[str] = []

    if use_tools:
        messages: list[dict] = [
            {"role": "system", "content": TOOL_SYSTEM},
            {"role": "user", "content": wrap_message(message)},
        ]
        seen: set[str] = set()
        n_calls = 0
        for _ in range(max_steps):
            r = await client.chat.completions.create(
                model=model, temperature=0, messages=messages, tools=toolbox.specs
            )
            msg = r.choices[0].message
            if not msg.tool_calls:
                break
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                n_calls += 1
                call_id = tc.id or f"call_{n_calls}"
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if not isinstance(args, dict):
                        raise TypeError
                except (ValueError, TypeError):
                    args = {}
                key = f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"
                if key in seen:
                    content = json.dumps({"error": "duplicate call — you already have this result"})
                else:
                    seen.add(key)
                    yield {"type": "step", "id": call_id, "tool": name,
                           "args": {k: str(v) for k, v in args.items()}}
                    result = await toolbox.run(name, args)
                    content = result.content
                    strong.extend(result.strong)
                    for c in result.citations:
                        if c["url"] not in {x["url"] for x in citations}:
                            citations.append(c)
                    # Advisories go in their own block: they inform advice and citations, not the decision.
                    (advisories if name == "search_advisories" else trail).append(
                        f"{name}({json.dumps(args, ensure_ascii=False)}) -> {content}")
                    if name == "search_advisories":
                        content = result.summary  # the tool phase only needs to know it ran; saves tokens
                        # (the class proxy caps tokens per window — full excerpts go to the verdict only)
                    yield {"type": "observation", "id": call_id, "tool": name,
                           "summary": result.summary, "tone": result.tone}
                messages.append({"role": "tool", "tool_call_id": call_id, "content": content})

    yield {"type": "summarizing"}
    evidence = "\n".join(trail) if trail else "(no tool evidence)"
    if strong:
        evidence += "\nSTRONG EVIDENCE OF A SCAM:\n" + "\n".join(f"- {s}" for s in strong)
    verdict, repairs = await produce_verdict(client, model, message, evidence, max_repairs, "\n".join(advisories))
    verdict = apply_evidence_floor(verdict, strong)
    # Citations come from the retrieval trail, never the model — and only back a warning: scam advisories
    # retrieved for a genuine message are topic matches, not support for "this is fine".
    if verdict.risk_level in (RiskLevel.medium, RiskLevel.high):
        verdict.citations = [Citation(**c) for c in citations[:3]]
    yield {"type": "verdict", "verdict": verdict.model_dump(mode="json"), "repairs": repairs}
