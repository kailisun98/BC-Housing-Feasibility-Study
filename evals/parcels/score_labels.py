"""Score the shape classifier against a person's labels.

    python evals/parcels/score_labels.py            # labels.json beside uncertain.json

Each labelled parcel's ring is classified again with the current `ffm.parcel_shapes` thresholds (so a threshold change
is scored at once) and compared with the label; `other: ...` and unlabelled parcels are listed but not scored.
Prints one line per parcel and the totals; `--json` prints the rows as JSON instead.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from ffm import parcel_shapes as ps  # noqa: E402


def score(labels: dict, uncertain: dict) -> dict:
    by_id = {p["site_id"]: p for p in uncertain["parcels"]}
    rows = []
    for L in labels["labels"]:
        p = by_id[L["site_id"]]
        res = ps.classify({"type": "Polygon", "coordinates": p["ring_lonlat"]})
        label = L.get("label")
        kind = "unlabelled" if not label else ("other" if label.startswith("other") else label)
        rows.append({"address": L["address"], "site_id": L["site_id"], "label": kind, "note": L.get("note"),
                     "asked": L["best_guess"], "asked_runner_up": L["runner_up"], "now": res["class"], "now_alternative": res["alternative"],
                     "rectangularity": res["rectangularity"], "convexity": res["convexity"], "vertices": res["vertices"], "reflex": res["reflex_corners"],
                     "narrowest_m": res["narrowest_cross_section_m"], "area_m2": res["area_m2"]})
    scored = [r for r in rows if r["label"] not in ("other", "unlabelled")]
    totals = {"labelled_with_a_class": len(scored), "other_or_unlabelled": len(rows) - len(scored),
              "asked_right": sum(r["label"] == r["asked"] for r in scored), "asked_runner_up_right": sum(r["label"] == r["asked_runner_up"] for r in scored),
              "now_right": sum(r["label"] == r["now"] for r in scored), "now_alternative_right": sum(r["label"] == r["now_alternative"] for r in scored),
              "now_wrong": Counter(f'{r["now"]} -> {r["label"]}' for r in scored if r["now"] != r["label"]),
              "labels": Counter(r["label"] for r in scored)}
    return {"rows": rows, "totals": totals}


def main() -> None:
    labels = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
    uncertain = json.loads((HERE / "uncertain.json").read_text(encoding="utf-8"))
    out = score(labels, uncertain)
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    print(f"{'address':26} {'asked':15} {'now':15} {'label':15} rect  conv  v r")
    for r in out["rows"]:
        mark = "=" if r["label"] == r["now"] else (" " if r["label"] in ("other", "unlabelled") else "X")
        print(f'{r["address"]:26} {r["asked"]:15} {r["now"]:15} {r["label"]:15} {r["rectangularity"]:.3f} {r["convexity"]:.3f} {r["vertices"]} {r["reflex"]} {mark}')
    t = out["totals"]
    print()
    print(f'{t["labelled_with_a_class"]} labelled with a class, {t["other_or_unlabelled"]} other or unlabelled.')
    print(f'As asked (the thresholds of 11 Nov 2026): {t["asked_right"]} right, runner-up right {t["asked_runner_up_right"]}.')
    print(f'Now: {t["now_right"]} right, alternative right {t["now_alternative_right"]}; wrong: {dict(t["now_wrong"])}')


if __name__ == "__main__":
    main()
