"""Inspect all 40 cases and verify data structure."""

import json
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
data_path = backend_root / "data" / "bharathome_golden_dataset.json"

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cases = data["test_cases"]
print(f"Total test cases: {len(cases)}")

categories = {}
for idx, tc in enumerate(cases, 1):
    cat = tc.get("metadata", {}).get("category", "Uncategorized")
    categories.setdefault(cat, []).append((idx, tc))

for cat, items in categories.items():
    print(f"\n=== Category: {cat} ({len(items)} cases) ===")
    for idx, tc in items:
        name = tc["name"]
        q = tc["input_data"]["messages"][0]["content"]
        must = tc.get("expected_output", {}).get("must_include", [])
        print(f"  [{idx:02d}] {name}")
        print(f"       Q: {q[:80]}...")
        print(f"       Must: {must}")

