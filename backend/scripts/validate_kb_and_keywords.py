"""Validate keywords match against retrieval contexts and KB articles."""

import json
from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.demo.knowledge_base import BHARATHOME_KNOWLEDGE_BASE, search_knowledge_base

data_path = backend_root / "data" / "bharathome_golden_dataset.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data["test_cases"]

print(f"Auditing {len(test_cases)} test cases against retrieval contexts and KB...\n")

missing_in_context = []

for idx, tc in enumerate(test_cases, 1):
    name = tc["name"]
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    keywords = exp.get("must_include", [])
    ret_context = tc.get("retrieval_context", [])

    # Concatenate all text in retrieval_context
    ctx_text = ""
    for doc in ret_context:
        ctx_text += " " + doc.get("text", "") + " " + doc.get("content", "") + " " + doc.get("title", "") + " " + doc.get("section", "")
    ctx_lower = ctx_text.lower()

    # Also search KB
    kb_res = search_knowledge_base(q, top_k=2)
    kb_text = ""
    for k in kb_res:
        kb_text += " " + k.get("title", "") + " " + k.get("content", "")
    kb_lower = kb_text.lower()

    combined = (ctx_lower + " " + kb_lower).strip()

    unmatched_ctx = [kw for kw in keywords if kw.lower() not in ctx_lower]
    unmatched_combined = [kw for kw in keywords if kw.lower() not in combined]

    print(f"[{idx:02d}] {name}")
    print(f"     Keywords: {keywords}")
    if unmatched_combined:
        print(f"     MISSING in combined (ctx + KB): {unmatched_combined}")
        missing_in_context.append((idx, name, unmatched_combined))
    elif unmatched_ctx:
        print(f"     Found in KB but missing in ret_context: {unmatched_ctx}")
    else:
        print(f"     ALL {len(keywords)} keywords present in ret_context!")

print("\n" + "=" * 80)
print(f"Summary: {len(missing_in_context)} test cases have keywords missing from combined text.")
for item in missing_in_context:
    print(f"Case {item[0]}: {item[1]} -> Missing: {item[2]}")

