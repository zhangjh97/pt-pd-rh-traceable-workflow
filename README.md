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

It does **not** contain ongoing or future Pt-W, zirconia-dispersion, Pt-Pd-Rh-Ru, catalytic-reaction, mechanical-property, or high-temperature studies. It also excludes server credentials, network information, large restart wavefunctions, charge-density scratch data, and unrelated project files.

## Directory map

- `data/cohorts/`: machine-readable cohort definitions corresponding to Supplementary Tables S12-S15.
- `data/model_validation/`: strict-validation summary tables and the 64 associated CIF structures.
- `data/screening/`: screening DFT tables, 32 input structures and inputs, and compact job records.
- `data/common_family/processed/`: audited tables for relaxations, convergence, ranking, force, and stress analyses.
- `data/common_family/raw_archives/`: seven compact calculation archives referenced in Supplementary Table S1. Large QE scratch directories are absent.
- `workflow/queue_definitions/`: queue scripts and original calculation inputs for the common-family validation runs.
- `code/`: selection, audit, verification, and figure-source scripts.
- `docs/`: data dictionary, publication instructions, and manuscript availability text.
- `metadata/`: file manifest and SHA-256 checksums.

## Quick verification

From the repository root, run:

```bash
python code/verify_release.py
```

The script checks cohort sizes, DFT completion counts, common-family case counts, selected numerical values reported in the manuscript, and file hashes where available. It performs no new DFT calculation.

## Software

The numerical DFT records were produced with Quantum ESPRESSO 7.5. The analysis scripts use Python 3 and, for plotting, NumPy and Matplotlib. See `requirements.txt` and the manuscript Methods for the complete scientific protocol.

## Third-party resources

MatterGen, MatterSim, Quantum ESPRESSO, pseudopotentials, and other third-party software retain their original licenses and citations. Model weights are not redistributed here. Pseudopotential filenames, sources, revisions, and SHA-256 values are recorded so that the exact resources can be obtained from their official distributions.

## Known limits

The archived model snapshot identifier is recorded, but the exact early MatterGen source-code commit and stochastic generation seeds were not preserved. The manuscript reports this limitation. The screening and common-family DFT protocols use different pseudopotential families and must not be pooled as one energy scale.

## Citation and permanent archive

Before public release, add the accepted manuscript citation and a permanent repository DOI. The recommended workflow is to create a GitHub release and archive that release with Zenodo. Do not invent a DOI before Zenodo issues one.

## Licensing

See `LICENSE_SELECTION_REQUIRED.md`. No license is granted until the authors or rights holder approve and add the final license files.
