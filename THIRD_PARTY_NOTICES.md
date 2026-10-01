# Third-party resources and attribution

Reviewed: 2026-10-01. The repository's author licenses do not replace third-party
licenses. This notice applies to loose files and to copies inside the seven
calculation archives in data/common_family/raw_archives/.

## Bundled PseudoDojo pseudopotentials

Credit: the PseudoDojo project and the original pseudopotential authors.
These data were generated using ONCVPSP by D. R. Hamann. PseudoDojo explicitly
licenses its pseudopotential files and associated input files under CC BY 4.0.
Its software has a separate license; the generator is not redistributed here.

- Official license statement: https://github.com/PseudoDojo/pseudodojo#license
- Historical project statement: https://github.com/abinit/pseudo_dojo/blob/master/README.md
- Data library: https://github.com/PseudoDojo/ONCVPSP-PBE-SR
- Recorded source revision: 823b18f7701b6303e0e69114eaa645173f706600
- Recorded library: NC SR (ONCVPSP v0.4.1), PBE, scalar relativistic, standard table.
- License: https://creativecommons.org/licenses/by/4.0/legalcode.en
- Website: https://www.pseudo-dojo.org/

| Local filename | Element | SHA-256 |
| --- | --- | --- |
| Pt_std.upf | Pt | d720e74ecee92d6f9d701eb0505324bef77d0b67d115f32eadb9a0639162ce46 |
| Pd_std.upf | Pd | 3b2cac5272fcab98ade99eff6cc6153e4c450ca1632ac96202a7e182bf592d67 |
| Rh_std.upf | Rh | 2c5ac1aeca2d407236885fd9a777221beeb1869cc30b1efb327105cb6b640696 |

The release contains 59 copies of each identity across loose files and archives.
The local names standardize the filenames used by the calculations. No changes
to the pseudopotential bytes were made when preparing this licensed release;
original header and generator notices are retained. The per-queue
pseudopotential_metadata.json files supply provenance. Credit PseudoDojo when
reusing or redistributing these files and retain this notice with extracted copies.

Scientific references:

- D. R. Hamann, Optimized norm-conserving Vanderbilt pseudopotentials,
  Physical Review B 88, 085117 (2013), https://doi.org/10.1103/PhysRevB.88.085117.
- M. J. van Setten et al., The PseudoDojo: Training and grading a 85 element
  optimized norm-conserving pseudopotential table, Computer Physics Communications
  226, 39-54 (2018), https://doi.org/10.1016/j.cpc.2018.01.012.

## Screening pseudopotentials

The historical mixed-family screening used the SSSP 1.3.0 PBE Precision
distribution. Its files are identified in the manuscript and archived inputs;
the SSSP UPF binaries are not included in this release. Obtain those resources
and their family-specific license notices from the official SSSP distribution:
https://www.materialscloud.org/discover/sssp/table/precision

SSSP collection licensing must not be assumed to replace the license of every
individual potential. Do not substitute the bundled PseudoDojo potentials when
reproducing historical screening energies.

## External software and models (not bundled)

- MatterGen: https://github.com/microsoft/mattergen
- MatterSim: https://github.com/microsoft/mattersim
- Quantum ESPRESSO: https://www.quantum-espresso.org/ and https://gitlab.com/QEF/q-e
- pymatgen: https://github.com/materialsproject/pymatgen
- NumPy: https://numpy.org/
- Matplotlib: https://matplotlib.org/

Obtain source code, executables and model checkpoints from these original
distributors and follow the license applicable to the version or checkpoint
used. Cite the software and methods as described in the manuscript. Printed
third-party attribution in calculation outputs is retained. Presence of an
output record does not imply redistribution of the corresponding executable.
