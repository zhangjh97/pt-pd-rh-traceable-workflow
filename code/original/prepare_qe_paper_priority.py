from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PAPER_SELECTION = {
    "Pt-Pd": {1, 8, 9, 11, 13, 15},
    "Pt-Rh": {1, 2, 4, 8, 13, 16},
    "Pd-Rh": {1, 5, 6, 8, 10, 14, 15, 16},
    "Pt-Pd-Rh": {1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 16},
}

LEGACY_SERIES = {
    "Pd-Rh-01_Pd4Rh": "dft-static-v3-worker-02",
    "Pd-Rh-05_Pd6Rh6": "dft-static-v3-worker-06",
    "Pd-Rh-06_PdRh3": "dft-static-v3-worker-07",
    "Pd-Rh-10_Pd6Rh3": "dft-static-v3-worker-10",
    "Pd-Rh-16_Pd5Rh7": "dft-static-v3-worker-04",
    "Pt-Pd-08_Pd5Pt15": "dft-static-v3-worker-11",
}


def candidate_number(candidate_id: str, system: str) -> int:
    suffix = candidate_id.removeprefix(f"{system}-").split("_", 1)[0]
    return int(suffix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the focused Pt-Pd-Rh paper DFT queue")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    screening = json.loads(args.screening.read_text(encoding="utf-8"))
    model_data = {}
    for group in screening["results"]:
        system = str(group["system"])
        for index, item in enumerate(group["candidates"], start=1):
            model_data[(system, index)] = item

    selected = []
    for item in manifest:
        system = str(item["candidate_id"]).split("-", 3)
        system = "Pt-Pd-Rh" if str(item["candidate_id"]).startswith("Pt-Pd-Rh-") else "-".join(system[:2])
        if system not in PAPER_SELECTION:
            continue
        number = candidate_number(str(item["candidate_id"]), system)
        if number not in PAPER_SELECTION[system]:
            continue
        model = model_data[(system, number)]
        selected.append({
            **item,
            "paper_system": system,
            "paper_candidate_number": number,
            "model_energy_ev_per_atom": model.get("model_energy_eV_per_atom"),
            "model_max_force_ev_a": model.get("max_force_eV_A"),
            "composition_x_a": model.get("x_a"),
            "composition_x_b": model.get("x_b"),
            "composition_x_c": model.get("x_c"),
        })

    selected.sort(key=lambda row: (
        0 if row["paper_system"] == "Pt-Pd-Rh" else 1,
        int(row["num_atoms"]),
        float(row["estimated_cost"]),
    ))
    loads = [0 for _ in range(args.workers)]
    worker_rows = [[] for _ in range(args.workers)]
    for row in sorted(selected, key=lambda item: float(item["estimated_cost"]), reverse=True):
        worker = min(range(args.workers), key=loads.__getitem__)
        loads[worker] += int(row["estimated_cost"])
        worker_rows[worker].append(row)

    args.output_root.mkdir(parents=True, exist_ok=True)
    paper_manifest = []
    for index, rows in enumerate(worker_rows, start=1):
        series = f"dft-paper-worker-{index:02d}"
        worker_dir = args.output_root / series
        worker_dir.mkdir(parents=True, exist_ok=True)
        for row in sorted(rows, key=lambda item: (int(item["num_atoms"]), item["candidate_id"])):
            source = Path(row["input_file"])
            target = worker_dir / source.name
            job = source.stem
            content = source.read_text(encoding="utf-8")
            outdir = f"./scratch/{series}/{job}"
            content = re.sub(r"(?m)^\s*outdir\s*=\s*['\"][^'\"]+['\"]", f"  outdir = '{outdir}'", content)
            target.write_text(content, encoding="utf-8", newline="\n")
            candidate_id = str(row["candidate_id"])
            paper_manifest.append({
                **row,
                "series": LEGACY_SERIES.get(candidate_id, series),
                "execution_series": series,
                "input_file": str(target),
            })

    (args.output_root / "paper-manifest.json").write_text(
        json.dumps(paper_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {
        "objective": "Pt-Pd-Rh ternary paper with three binary-edge baselines",
        "selected": len(paper_manifest),
        "systems": {
            system: sum(row["paper_system"] == system for row in paper_manifest)
            for system in PAPER_SELECTION
        },
        "worker_loads": loads,
    }
    (args.output_root / "paper-selection-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
