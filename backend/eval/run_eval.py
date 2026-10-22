"""Run the agent (or the zero-shot baseline) over a labelled split and print the metrics.

    uv run python -m eval.run_eval --split test --mode baseline     # zero-shot gemma, no tools (named baseline)
    uv run python -m eval.run_eval --split test --mode agent_norag  # agent with URL + indicator tools
    uv run python -m eval.run_eval --split test --mode agent        # + search_advisories (RAG)

"Flagged" = risk_level medium/high; that is what the user sees as a warning.
Per-item results are written to eval/results/<split>-<mode>.jsonl.
"""

import argparse
import asyncio
import json
from pathlib import Path

from app.agent.loop import run_agent
from app.agent.tools import Toolbox
from app.agent.verdict import VerdictError
from app.config import get_settings
from app.llm.client import get_llm_client
from app.services.scan_service import build_toolbox
from eval.metrics import binary, macro_f1

RESULTS_DIR = Path(__file__).parent / "results"
# baseline: zero-shot, no tools · agent_norag: URL/indicator tools only · agent: + search_advisories (RAG)
MODES = ["baseline", "agent_norag", "agent"]


async def run_one(item: dict, toolbox: Toolbox, use_tools: bool) -> dict:
    s = get_settings()
    out = {"id": item["id"], "tools": [], "error": None, "repairs": 0}
    try:
        async for ev in run_agent(
            get_llm_client(), toolbox, item["message"], model=s.chat_model,
            max_steps=s.agent_max_steps, max_repairs=s.verdict_max_repairs, use_tools=use_tools,
        ):
            if ev["type"] == "step":
                out["tools"].append(f"{ev['tool']}({', '.join(ev['args'].values())})")
            elif ev["type"] == "verdict":
                out["scam_type"] = ev["verdict"]["scam_type"]
                out["risk_level"] = ev["verdict"]["risk_level"]
                out["summary"] = ev["verdict"]["summary"]
                out["citations"] = [c["url"] for c in ev["verdict"]["citations"]]
                out["repairs"] = ev["repairs"]
    except VerdictError as e:
        out["error"] = str(e)
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--mode", choices=MODES, default="agent")
    ap.add_argument("--include-review", action="store_true")
    a = ap.parse_args()

    path = get_settings().data_dir / "messages" / f"{a.split}.jsonl"
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    skipped = [it["id"] for it in items if it.get("needs_review") and not a.include_review]
    items = [it for it in items if it["id"] not in skipped]  # unconfirmed labels are not scored
    if skipped:
        print(f"skipping {len(skipped)} needs_review items (use --include-review): {', '.join(skipped)}")
    toolbox = build_toolbox(use_rag=a.mode == "agent")
    # sequential: the proxy is shared by the whole class
    results = [await run_one(it, toolbox, use_tools=a.mode != "baseline") for it in items]

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{a.split}-{a.mode}.jsonl"
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")

    print(f"{'id':8} {'gold':22} {'pred':22} ok  tools")
    for it, r in zip(items, results):
        gold = f"{it['scam_type']}/{it['risk_level']}"
        pred = "PARSE FAIL" if r["error"] else f"{r['scam_type']}/{r['risk_level']}"
        ok = "✓" if not r["error"] and r["scam_type"] == it["scam_type"] else "✗"
        print(f"{it['id']:8} {gold:22} {pred:22} {ok}   {'; '.join(r['tools'])}")

    gold_t = [it["scam_type"] for it in items]
    pred_t = [r.get("scam_type", "PARSE_FAIL") for r in results]
    bin_ = binary([it["is_scam"] for it in items],
                  [r.get("risk_level") in ("medium", "high") for r in results])
    n = len(items)
    print(f"\n[{a.split} / {a.mode}] n={n}")
    print(f"scam_type accuracy  {sum(g == p for g, p in zip(gold_t, pred_t)) / n:.3f}")
    print(f"scam_type macro-F1  {macro_f1(gold_t, pred_t):.3f}")
    print(f"flagged: precision {bin_['precision']:.3f}  recall {bin_['recall']:.3f}  f1 {bin_['f1']:.3f}"
          f"  (tp={bin_['tp']} fp={bin_['fp']} fn={bin_['fn']} tn={bin_['tn']})")
    print(f"parse failures      {sum(r['error'] is not None for r in results)}   "
          f"repairs used {sum(r['repairs'] for r in results)}")
    print(f"-> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
