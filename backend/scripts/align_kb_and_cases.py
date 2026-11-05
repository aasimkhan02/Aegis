"""Align KB articles with each test case."""

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
print(f"Total Test Cases: {len(test_cases)}")
print(f"Total KB Articles: {len(BHARATHOME_KNOWLEDGE_BASE)}\n")

for idx, tc in enumerate(test_cases, 1):
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    must = exp.get("must_include", [])
    matches = search_knowledge_base(q, top_k=2)

    top_art = matches[0] if matches else None
    top_title = top_art["title"] if top_art else "NO MATCH"
    top_content = top_art["content"].lower() if top_art else ""

    missing_in_art = [kw for kw in must if kw.lower() not in top_content] if top_art else must
    print(f"#{idx:02d} [{tc.get('metadata', {}).get('category')}] {tc['name']}")
    print(f"    Top Match: {top_title}")
    if missing_in_art:
        print(f"    Missing keywords in top article: {missing_in_art}")
    else:
        print("    --> 100% of expected keywords found in top article!")

