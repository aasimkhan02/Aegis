"""Inspect the true 40 test cases from bharathome_golden_dataset.json."""

import json
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
data_path = backend_root / "data" / "bharathome_golden_dataset.json"

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for idx, tc in enumerate(data["test_cases"][16:25], 17):
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    must = exp.get("must_include", [])
    cat = tc.get("metadata", {}).get("category", "")
    print(f"#{idx:02d} [{cat}] {tc['name']}")
    print(f"    Q: {q}")
    print(f"    Must: {must}")
    print("-" * 75)
