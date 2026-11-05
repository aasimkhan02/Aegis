"""Audit original must_include against retrieval_context and KB."""

import json
from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent.parent
data_path = backend_root / "data" / "bharathome_golden_dataset.json"

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data["test_cases"]
print(f"Auditing {len(test_cases)} original cases against retrieval_context...\n")

missing_total = 0
for idx, tc in enumerate(test_cases, 1):
    name = tc["name"]
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    must = exp.get("must_include", [])
    ret = tc.get("retrieval_context", [])

    ctx_text = ""
    for doc in ret:
        ctx_text += " " + doc.get("text", "") + " " + doc.get("content", "") + " " + doc.get("title", "") + " " + doc.get("section", "")
    ctx_lower = ctx_text.lower()

    unmatched = [kw for kw in must if kw.lower() not in ctx_lower]
    if unmatched:
        print(f"#{idx:02d} [{tc.get('metadata', {}).get('category')}] {name}")
        print(f"    Missing in ret_context: {unmatched}")
        missing_total += 1

print("\n" + "=" * 70)
print(f"Cases with keywords missing from retrieval_context: {missing_total} / {len(test_cases)}")

