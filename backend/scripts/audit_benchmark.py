"""Audit all 40 test cases and their retrieval contexts against the knowledge base."""

from pathlib import Path
import json
import sys

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.demo.knowledge_base import BHARATHOME_KNOWLEDGE_BASE, search_knowledge_base


def audit_test_cases() -> None:
    fixture_path = backend_root / "data" / "bharathome_golden_dataset.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data["test_cases"]
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Total Existing KB Articles: {len(BHARATHOME_KNOWLEDGE_BASE)}\n")

    for i, tc in enumerate(test_cases, 1):
        name = tc["name"]
        cat = tc.get("metadata", {}).get("category", "Uncategorized")
        user_msg = tc["input_data"]["messages"][0]["content"]
        exp_out = tc.get("expected_output", {})
        must_include = exp_out.get("must_include", []) if isinstance(exp_out, dict) else []
        ret_context = tc.get("retrieval_context", [])

        # Check KB search match
        kb_matches = search_knowledge_base(user_msg, top_k=2)
        top_kb_title = kb_matches[0]["title"] if kb_matches else "NO_MATCH"

        print(f"[{i:02d}] Category: {cat}")
        print(f"     Name: {name}")
        print(f"     User Query: {user_msg[:90]}...")
        print(f"     Must Include: {must_include}")
        print(f"     Has Retrieval Context: {len(ret_context)} doc(s)")
        print(f"     Top KB Match: {top_kb_title}")
        print("-" * 80)


if __name__ == "__main__":
    audit_test_cases()

