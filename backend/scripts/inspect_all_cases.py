"""List all 40 test cases, their category, question, and expected output."""

import json
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
data_path = backend_root / "data" / "bharathome_golden_dataset.json"

with open(data_path, "r", encoding="utf-8") as f:
    d = json.load(f)

for i, tc in enumerate(d["test_cases"], 1):
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    must = exp.get("must_include", []) if isinstance(exp, dict) else []
    cat = tc.get("metadata", {}).get("category", "")
    print(f"{i:02d}. [{cat}] {tc['name']}")
    print(f"    Q: {q}")
    print(f"    Must: {must}")

