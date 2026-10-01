# Data dictionary and manuscript mapping

## Cohorts

| File | Unit | Manuscript role |
|---|---:|---|
| `Strict_model_validation_cohort_64.csv` | one retained structure per row | Supplementary Table S12; strict model-validation cohort |
| `DFT_screening_source_pool_64.csv` | one candidate per row | earlier source pool used for screening DFT selection |
| `DFT_scheduled_candidate_mapping_32.csv` | one scheduled candidate per row | Supplementary Tables S13 and S15; includes one incomplete job |
| `cohort_mapping_audit.json` | one audit record | verifies the distinction and internal correspondence of the two cohorts |

Model energies are model outputs, not DFT formation energies. Missing or incomplete calculations are not zero-energy observations.

## Strict model validation

`model_structure_details.csv` contains formula, atom count, convergence flag, residual force, minimum distance, local volume curvature, reduced formula, assigned space group, composition, and the archived source identifier for each of the 64 retained structures. The CIF files in `structures/` are named by Supplementary Table S12 row number.

These data support the composition, structural-group, residual-force, distance, and local-curvature results in Figure 3 and Supplementary Table S12.

## Screening DFT

`historical_dft.csv` contains the 32 scheduled candidates and 31 completed fixed-geometry screening results. `qe_input_parameters.csv` records the numerical protocol and pseudopotential filenames. The figure-source tables contain the finite candidate-set hull and same-stoichiometry comparisons used in Figures 3 and 4.

The finite-set hull values are limited to the evaluated candidate set. They do not establish equilibrium phase stability.

## Common-family DFT validation

| Directory or file | Supports |
|---|---|
| `main-queue-analysis-20260909/unified_results.csv` | seven candidate relaxations; Figure 5; Supplementary Table S3 |
| `convergence-analysis-20260909/formation_convergence.csv` | cutoff and mesh sensitivity; Figure 6; Supplementary Table S4 |
| `supplement-final-audit-20260909/kmesh_comparison.csv` | dense-mesh comparison; Figure 6; Supplementary Table S5 |
| `supplement-final-audit-20260909/pair_gaps.csv` | same-composition ranking; Figure 7a; Supplementary Table S6 |
| `final-force-audit-20260910/comparison.csv` | tight-SCF force/stress checks; Figure 7b; Supplementary Tables S7-S9 |
| `supplementary_input_protocols.csv` | all 55 validation protocols; Supplementary Tables S10-S11 |

Formation quantities use compatible elemental references within each protocol. Screening DFT and common-family DFT absolute energies must not be mixed.

## Raw archives

The seven `tar.gz` files reproduce the compact archive coverage listed in Supplementary Table S1. They contain inputs, outputs, metadata, and pseudopotential records. Large restart scratch data were intentionally excluded from the original exports.

## Excluded records

The release excludes ongoing Pt-W, Pt-ZrO2, Pt-Pd-Rh-Ru, ammonia-oxidation, long-duration degradation, mechanical-property, and high-temperature calculations because they do not support the submitted manuscript. It also excludes credentials, private network information, unrelated materials data, and large temporary QE files.
