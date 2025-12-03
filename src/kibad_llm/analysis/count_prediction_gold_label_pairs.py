from collections import Counter
import json
from pathlib import Path
import sys


def load_json_or_ndjson(p: Path):
    text = p.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        objs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            objs.append(json.loads(line))
        return objs


def leaf_paths(obj, prefix=""):
    paths = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            newp = f"{prefix}.{k}" if prefix else k
            paths |= leaf_paths(v, newp)
    elif isinstance(obj, list):
        for el in obj:
            paths |= leaf_paths(el, prefix)
        if not obj:
            paths.add(prefix)
    else:
        if prefix:
            paths.add(prefix)
    return paths


def extract_values(obj, path):
    parts = path.split(".")
    results = []

    def rec(o, idx):
        if idx >= len(parts):
            if isinstance(o, list):
                for e in o:
                    rec(e, idx)
            elif isinstance(o, dict):
                results.append(json.dumps(o, sort_keys=True))
            else:
                results.append(None if o is None else str(o))
            return

        key = parts[idx]
        if isinstance(o, dict):
            if key in o:
                rec(o[key], idx + 1)
            else:
                return
        elif isinstance(o, list):
            for e in o:
                rec(e, idx)
        else:
            return

    rec(obj, 0)
    cleaned = []
    for v in results:
        if v is None:
            cleaned.append("")
        else:
            cleaned.append(v)
    return sorted(set(cleaned))


def clean_pred_dicts(pred_dict):
    if type(pred_dict.get("structured")) is dict:
        new_pred_dict = pred_dict["structured"]
    else:
        new_pred_dict = {}
    new_pred_dict["file_name"] = pred_dict["file_name"]
    return new_pred_dict


def main(pred_path, gold_path):
    """
    Quick and dirty script to compare predictions and gold labels and create a table
    Table shows the confusion matrix as list with count of how manz pairs of (pred, gold) values occured for each field
    Matches input and output by file_name and zotitem_ptr_id, s.t. only gold labels with predictions are considered
    """

    # this only works for output predictions that have the "structured" schema
    pred = [clean_pred_dicts(pred_dict) for pred_dict in load_json_or_ndjson(Path(pred_path))]
    gold = load_json_or_ndjson(Path(gold_path))

    pred_map = {p.get("file_name"): p for p in pred}
    gold_map = {g.get("zotitem_ptr_id"): g for g in gold}

    keys = set()
    for obj in pred:
        keys |= leaf_paths(obj)

    keys = sorted(k for k in keys if k)
    counters_by_key = {k: Counter() for k in keys}

    for fid, p_obj in pred_map.items():
        g_obj = gold_map.get(fid[:-4])
        if not g_obj:
            continue
        for k in keys:
            p_vals = extract_values(p_obj, k)
            g_vals = extract_values(g_obj, k)
            p_repr = ", ".join(p_vals)
            g_repr = ", ".join(g_vals)
            counters_by_key[k][(p_repr, g_repr)] += 1

    for k in keys:
        ctr = counters_by_key[k]
        if not ctr:
            continue
        print(f"\n=== Key: {k} ===")
        print(f"{'prediction':60} | {'gold':60} | count")
        print("-" * 140)
        for (p_val, g_val), count in ctr.most_common():
            print(f"{p_val[:60]:60} | {g_val[:60]:60} | {count}")


if __name__ == "__main__":
    # execute from kibad-llm root directory
    main(sys.argv[1], "data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl")
