#!/usr/bin/env python3
"""Verify the curated release without launching scientific calculations."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label}: {actual} != {expected} within {tolerance}")


def verify_hashes() -> int:
    checksum_file = ROOT / "metadata" / "SHA256SUMS.txt"
    checked = 0
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch: {relative}")
        checked += 1
    return checked


def main() -> None:
    strict = rows("data/cohorts/Strict_model_validation_cohort_64.csv")
    pool = rows("data/cohorts/DFT_screening_source_pool_64.csv")
    scheduled = rows("data/cohorts/DFT_scheduled_candidate_mapping_32.csv")
    historical = rows("data/screening/tables/historical_dft.csv")
    protocols = rows("data/common_family/processed/supplementary_input_protocols.csv")
    unified = rows("data/common_family/processed/main-queue-analysis-20260909/unified_results.csv")
    formation = rows("data/common_family/processed/convergence-analysis-20260909/formation_convergence.csv")
    gaps = rows("data/common_family/processed/supplement-final-audit-20260909/pair_gaps.csv")
    forces = rows("data/common_family/processed/final-force-audit-20260910/comparison.csv")

    assert len(strict) == 64
    assert len(pool) == 64
    assert len(scheduled) == 32
    assert len(historical) == 32
    assert sum(r["qe_job_done"].lower() == "true" for r in historical) == 31
    assert len(protocols) == 55
    assert len(unified) == 7
    assert len(forces) == 4
    assert len(list((ROOT / "data/model_validation/structures").glob("*.cif"))) == 64
    assert len(list((ROOT / "data/screening/structures").glob("*.cif"))) == 32

    c110 = next(r for r in formation if r["group"] == "c110")
    close(float(c110["formation_meV_atom"]), -17.4021917177, 1e-8, "c110 formation")
    ptpd = next(r for r in gaps if r["lower_candidate"].startswith("Pt-Pd-01"))
    close(float(ptpd["new_gap_meV_atom"]), 51.1537666201, 1e-8, "Pt-Pd dense gap")
    warning = next(r for r in forces if r["job"].startswith("Pt-Pd-01"))
    assert warning["force_warning"].lower() == "true"

    audit = json.loads((ROOT / "data/cohorts/cohort_mapping_audit.json").read_text(encoding="utf-8"))
    if not isinstance(audit, dict):
        raise AssertionError("cohort audit is not a JSON object")

    checked = verify_hashes()
    print("Release verification passed")
    print(f"Strict cohort: {len(strict)}")
    print(f"Screening pool/scheduled/completed: {len(pool)}/{len(scheduled)}/31")
    print(f"Common-family validation cases: {len(protocols)}")
    print(f"Files verified by SHA-256: {checked}")


if __name__ == "__main__":
    main()
