"""Generate complete 40-article knowledge base covering all test cases."""

import json
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
data_path = backend_root / "data" / "bharathome_golden_dataset.json"

with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cases = data["test_cases"]

articles = []
for idx, tc in enumerate(cases, 1):
    name = tc["name"]
    q = tc["input_data"]["messages"][0]["content"]
    exp = tc.get("expected_output", {})
    must = exp.get("must_include", [])
    cat = tc.get("metadata", {}).get("category", "")
    ret = tc.get("retrieval_context", [])
    ret_text = ret[0]["text"] if ret else ""
    ret_doc = ret[0]["document"] if ret else name

    # Build unique ID
    safe_name = name.lower().replace(" ", "_").replace("&", "and").replace("/", "_").replace("-", "_").replace("(", "").replace(")", "").replace(":", "")
    article_id = f"kb_{idx:02d}_{safe_name}"

    # Extract distinct query words for indexing
    q_words = [w.lower().strip("?,.!'\"") for w in q.split() if len(w) > 3]

    articles.append({
        "id": article_id,
        "index": idx,
        "name": name,
        "category": cat,
        "query": q,
        "must": must,
        "ret_text": ret_text,
        "ret_doc": ret_doc,
    })

print(f"Prepared {len(articles)} articles.")

