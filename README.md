# Pt-Pd-Rh workflow: minimal reproducibility package

This repository contains the data and code that support the manuscript
"A traceable computational workflow for generative screening and DFT validation of platinum palladium rhodium alloys".

## Scope

The release is deliberately limited to the Pt-Pd-Rh study reported in the manuscript. It contains:

- the 64-structure strict model-validation cohort;
- the earlier 64-candidate screening pool and its 32 scheduled DFT candidates;
- the 31 completed mixed-family screening DFT records;
- the 55-case common-family DFT validation dataset;
- processed source tables used for the reported numerical results;
- Quantum ESPRESSO inputs, compact outputs, queue definitions, checksums, and analysis scripts.

The scope is the present manuscript. Large restart wavefunctions, charge-density scratch data and unrelated project files are excluded.

## Directory map

- `data/cohorts/`: machine-readable cohort definitions corresponding to Supplementary Tables S12-S15.
- `data/model_validation/`: strict-validation summary tables and the 64 associated CIF structures.
- `data/screening/`: screening DFT tables, 32 input structures and inputs, and compact job records.
- `data/common_family/processed/`: audited tables for relaxations, convergence, ranking, force, and stress analyses.
- `data/common_family/raw_archives/`: seven compact calculation archives referenced in Supplementary Table S1. Large QE scratch directories are absent.
- `workflow/queue_definitions/`: queue scripts and original calculation inputs for the common-family validation runs.
- `code/`: selection, audit, verification, and figure-source scripts.
- `docs/`: data dictionary, release instructions, and manuscript availability text.
- `metadata/`: file manifest and SHA-256 checksums.

## Quick verification

From the repository root, run:

```bash
python code/verify_release.py
```

The script checks cohort sizes, DFT completion counts, common-family case counts, selected numerical values reported in the manuscript, and file hashes where available. It performs no new DFT calculation.

## Software

The numerical DFT records were produced with Quantum ESPRESSO 7.5. The verification command above uses only the Python 3 standard library (Python 3.10 or later). Plotting scripts use NumPy and Matplotlib; install them with `python -m pip install -r requirements.txt`. See the manuscript Methods and archived inputs for the scientific protocol. Historical scripts in `code/original/` preserve the original project paths and may require path adaptation; this is an evidence archive, not a one-command recreation of the full generation and DFT campaign. Verification does not start DFT jobs or require a GPU.

## Third-party resources

MatterGen, MatterSim, Quantum ESPRESSO and other external software retain their original licenses and citations. Their source packages, executables and model weights are not redistributed here. The three bundled PseudoDojo pseudopotentials retain PseudoDojo's CC BY 4.0 license, including copies inside calculation archives. Sources, revision, hashes, attribution and changes are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Known limits

The archived model snapshot identifier is recorded, but the exact early MatterGen source-code commit and stochastic generation seeds were not preserved. The manuscript reports this limitation. The screening and common-family DFT protocols use different pseudopotential families and must not be pooled as one energy scale.

## Citation and permanent archive

Repository: https://github.com/zhangjh97/pt-pd-rh-traceable-workflow

Cite the manuscript title above, this repository and the exact Git commit used. A manuscript DOI and an archival repository DOI have not been assigned in this release. They can be added when available; no acceptance or publication is implied.

## Licensing

Author-written software is licensed under the [MIT License](LICENSE). Author-generated data are licensed under [CC BY 4.0](LICENSE-DATA.md). See [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the per-material scope and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party attribution. These rules cover files stored inside the calculation archives as well as loose files.
