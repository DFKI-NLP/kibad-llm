"""Calculate manuscript extraction time per document using only the standard library.

Run from the repository root with `python scripts/manuscript_inference_costs.py`.
The experiment READMEs select the model-specific multiruns; Hydra overrides verify
model/seed identities. Prediction records supply document counts, cross-checked
against console logs. Outputs include run-level provenance, summary CSV and a
Markdown table. GPT-5 is deliberately excluded, with monetary-cost placeholders.
"""

import argparse
import csv
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = {
    "CoreSchema": "525_faktencheck_core_bestconfig_testset",
    "OrganismTrends": "549_organism_trends_bestconfig_testset",
}
MODELS = {
    "gpt_oss_20b": "GPT OSS 20B",
    "gemma3_27b": "Gemma 3 27B",
    "qwen3_30b": "Qwen 3 30B",
    "mistral_small_3_24b": "Mistral Small 3 24B",
}
SEEDS = {42, 1337, 7331}


def readme_multiruns(results_root, experiment):
    """Read the four active open-weight model locations from a prediction README."""
    readme = (results_root / "logs" / experiment / "README.md").read_text(encoding="utf-8")
    prediction = readme.split("## Prediction\n", 1)[1].split("## Evaluation\n", 1)[0]
    sections = re.split(r"^### (.+)\n", prediction, flags=re.MULTILINE)
    locations = {}
    for model, section in zip(sections[1::2], sections[2::2]):
        if model not in MODELS:
            continue
        paths = re.findall(r"Saved to `(logs/[^`]+/predict/multiruns/[^`]+)`", section)
        if len(paths) != 1 or not paths[0].startswith(f"logs/{experiment}/"):
            raise ValueError(f"Ambiguous/missing README location for {experiment}/{model}")
        locations[model] = results_root / paths[0]
    if set(locations) != set(MODELS):
        raise ValueError(f"Missing model sections in {experiment}/README.md")
    return locations


def collect_runs(results_root):
    """Validate and normalize all three seeds per model and test set."""
    rows = []
    for task, experiment in EXPERIMENTS.items():
        reference_documents = None
        for model, folder in readme_multiruns(results_root, experiment).items():
            seeds = []
            # Only seed subdirectories: the multirun root repeats the same timings.
            for job_file in sorted(folder.glob("[0-9]*/job_return_value.json")):
                run = job_file.parent
                overrides = (run / ".hydra/overrides.yaml").read_text(encoding="utf-8")
                if f"- extractor/llm={model}_in_process" not in overrides.splitlines():
                    raise ValueError(f"README/model mismatch: {run}")
                seed = int(re.search(r"^- seed=(\d+)$", overrides, re.MULTILINE)[1])
                seeds.append(seed)
                job = json.loads(job_file.read_text(encoding="utf-8"))
                prediction_file = results_root / job["output_file"]
                documents = set()
                with prediction_file.open(encoding="utf-8") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        name = json.loads(line)["file_name"]
                        if name in documents:
                            raise ValueError(f"Duplicate document {name}: {prediction_file}")
                        documents.add(name)
                console = (run / "console.log").read_text(encoding="utf-8")
                logged_counts = set(re.findall(r"Processing (\d+) PDF files", console))
                if not documents or logged_counts != {str(len(documents))}:
                    raise ValueError(f"Prediction/console document-count mismatch: {run}")
                if reference_documents is None:
                    reference_documents = documents
                elif documents != reference_documents:
                    raise ValueError(f"Different document sets in {experiment}: {run}")
                seconds = float(job["time_extraction"])
                if not math.isfinite(seconds) or seconds <= 0:
                    raise ValueError(f"Invalid extraction time: {job_file}")
                rows.append(
                    {
                        "task": task,
                        "model": MODELS[model],
                        "seed": seed,
                        "documents": len(documents),
                        "time_extraction_s": seconds,
                        "seconds_per_document": seconds / len(documents),
                        "job_return_value": str(job_file.relative_to(results_root)),
                        "predictions": str(prediction_file.relative_to(results_root)),
                    }
                )
            if len(seeds) != 3 or set(seeds) != SEEDS:
                raise ValueError(f"Expected exactly seeds {sorted(SEEDS)}: {folder}, got {seeds}")
    return rows


def summarize(rows):
    """Compute the mean and sample SD of the three normalized run times."""
    summary = []
    for task in EXPERIMENTS:
        for model in MODELS.values():
            group = [row for row in rows if row["task"] == task and row["model"] == model]
            values = [row["seconds_per_document"] for row in group]
            summary.append(
                {
                    "task": task,
                    "model": model,
                    "documents": group[0]["documents"],
                    "runs": len(values),
                    "mean_s_per_document": statistics.mean(values),
                    "sample_sd_s_per_document": statistics.stdev(values),
                }
            )
    return summary


def write_csv(path, rows):
    """Write unrounded values and provenance for independent inspection."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def table_markdown(summary):
    """Format the manuscript table and explain the timing denominator."""
    lines = [
        "# Inference costs per document",
        "",
        "Reproduce with `python scripts/manuscript_inference_costs.py` (no extra dependencies).",
        "",
        "| Model | Measure | CoreSchema | OrganismTrends |",
        "| --- | --- | ---: | ---: |",
    ]
    for model in MODELS.values():
        cells = []
        for task in EXPERIMENTS:
            row = next(row for row in summary if row["task"] == task and row["model"] == model)
            cells.append(
                f"{row['mean_s_per_document']:.2f} ± {row['sample_sd_s_per_document']:.2f}"
            )
        lines.append(f"| {model} | s/document | {' | '.join(cells)} |")
    lines += [
        "| GPT-5 | €/document | TBD | TBD |",
        "",
        "Values are mean ± sample standard deviation (ddof=1) across seeds 42, 1337 and 7331.",
        "Each run's `time_extraction` is divided by the number of distinct `file_name` values",
        "in its predictions JSONL, including documents with extraction errors or empty outputs.",
        "Counts agree with all console logs: 500 for CoreSchema and 419 for OrganismTrends.",
        "The 430 OrganismTrends documents stated elsewhere in the manuscript differ from",
        "the 419 actually processed in these runs; the timing denominator is therefore 419.",
        "This is extraction-stage wall-clock time, including chunk processing and aggregation,",
        "excluding PDF conversion, extractor/model initialization and final file writing.",
        "These are timings under the recorded execution conditions, not a controlled hardware benchmark.",
        "",
        "Run locations are read from the prediction sections of the experiment READMEs:",
        "",
        *[f"- `{experiment}` ({task})" for task, experiment in EXPERIMENTS.items()],
        "",
        "`runs.csv` preserves source paths, document counts and raw/normalized timings for all 24 runs.",
        "`summary.csv` preserves unrounded means and sample standard deviations.",
        "",
        "GPT-5 monetary costs remain TBD; no GPT-5 inference timings are included.",
        "For the later cost analysis, the core README is `574_gpt5_faktencheck_core_testset`,",
        "and the trends README is `574_gpt5_organism_trends_testset`; each specifies one seed.",
        "The supplied experiment list repeats the trends experiment for GPT-5 core.",
    ]
    return "\n".join(lines) + "\n"


def main():
    """Generate the manuscript timing table and its supporting CSV files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=ROOT / "data/kibad-llm-results")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/manuscript-inference-costs"
    )
    args = parser.parse_args()
    rows = collect_runs(args.results_root)
    summary = summarize(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "runs.csv", rows)
    write_csv(args.output_dir / "summary.csv", summary)
    table = table_markdown(summary)
    (args.output_dir / "table.md").write_text(table, encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
