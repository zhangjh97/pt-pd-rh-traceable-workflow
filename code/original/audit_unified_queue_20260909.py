"""Verify completed relaxations and export final geometries with provenance."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import read, write

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / 'data/dft_runs/unified_validation_20260908_133506'
PACKAGE = BASE / 'deployment/qe-unified-long-queue-20260908'
OUT = BASE / 'data/dft_runs/main-queue-analysis-20260909'
RY_EV = 13.605693122994
BOHR_ANG = 0.529177210903
NUM = r'[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def final_number(pattern, text):
    return float(re.findall(pattern, text, re.M)[-1].replace('d', 'e').replace('D', 'E'))


def norm(text):
    return re.sub(r"restart_mode\s*=\s*'restart'", "restart_mode = 'from_scratch'", text).strip()


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'structures').mkdir(exist_ok=True)
    refs = {r['job'].rsplit('_', 1)[-1]: float(r['final_energy_Ry']) for r in csv.DictReader((BASE / 'data/dft_runs/convergence-analysis-20260909/job_audit.csv').open(encoding='utf-8-sig')) if r['job'].startswith('c110_ref_')}
    metadata = json.loads((RUN / 'pseudopotential_metadata.json').read_text())
    rows, manifests = [], []
    for name in (RUN / 'JOB_ORDER.txt').read_text().split():
        job = RUN / name
        inp = (job / 'input.in').read_text()
        assert norm(inp) == norm((PACKAGE / 'inputs' / (name + '.in')).read_text()), name
        assert (job / 'STATUS').read_text().strip() == 'DONE', name
        part = sorted(job.glob('output.part*.log'))[-1]
        rc = job / ('returncode.' + part.stem.split('.')[-1])
        assert rc.read_text().strip() == '0', name
        log = part.read_text(errors='replace')
        combined = (job / 'output.log').read_text(errors='replace')
        assert combined.rstrip().endswith(log.rstrip()), name
        assert 'bfgs converged' in log and 'End of BFGS Geometry Optimization' in log and 'Error in routine' not in log, name
        match = list(re.finditer(r'^!\s+total energy\s*=\s*(' + NUM + r')\s+Ry', log, re.M))[-1]
        tail = log[match.end():]
        assert 'convergence has been achieved' in tail and 'JOB DONE.' in tail, name
        accuracy = final_number(r'estimated scf accuracy\s*<\s*(' + NUM + ')', tail)
        assert accuracy < 1e-8, name
        coords = re.findall(r'Begin final coordinates[\s\S]*?End final coordinates', log)[-1]
        assert coords.strip() == (job / 'final_coordinates.txt').read_text().strip(), name
        nat = int(final_number(r'\bnat\s*=\s*(\d+)', inp))
        cell_lines = re.search(r'CELL_PARAMETERS\s*\(angstrom\)\s*\n((?:[^\n]+\n){3})', coords).group(1)
        cell = np.array([[float(v) for v in line.split()] for line in cell_lines.splitlines()])
        positions = re.search(r'ATOMIC_POSITIONS\s*\(crystal\)\s*\n((?:[^\n]+\n){' + str(nat) + '})', coords).group(1).splitlines()
        species = [p.split()[0] for p in positions]
        frac = [[float(v) for v in p.split()[1:4]] for p in positions]
        atoms = Atoms(species, cell=cell, scaled_positions=frac, pbc=True)
        independently_read = read(part, format='espresso-out', index=-1)
        assert Counter(independently_read.get_chemical_symbols()) == Counter(species), name
        assert np.allclose(independently_read.cell, cell, atol=2e-5, rtol=0), name
        delta = independently_read.get_scaled_positions() - atoms.get_scaled_positions()
        assert np.max(np.abs(delta - np.rint(delta))) < 2e-5, name
        initial = read(job / 'input.in', format='espresso-in')
        assert Counter(initial.get_chemical_symbols()) == Counter(species), name
        counts = Counter(species)
        for f in metadata['files']:
            assert sha(job / 'pseudo' / f['filename']) == f['sha256'], name
        forces = np.array(re.findall(r'atom\s+\d+\s+type\s+\d+\s+force\s*=\s*(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + ')', tail), dtype=float)
        assert len(forces) == nat, name
        pressure = final_number(r'\bP=\s*(' + NUM + ')', tail)
        stress_lines = re.search(r'P=\s*' + NUM + r'\s*\n((?:[^\n]+\n){3})', tail).group(1)
        stress = np.array([[float(x) for x in l.split()[3:6]] for l in stress_lines.splitlines()])
        max_comp = float(np.abs(forces).max())
        force_thr = final_number(r'forc_conv_thr\s*=\s*(' + NUM + ')', inp)
        pressure_thr = final_number(r'press_conv_thr\s*=\s*(' + NUM + ')', inp)
        ef = (float(match.group(1)) - sum(counts[e] * refs[e] for e in counts)) * RY_EV / nat
        kmesh = re.search(r'K_POINTS\s+automatic\s*\n([^\n]+)', inp).group(1).split()
        row = dict(job=name, nat=nat, Pt=counts['Pt'], Pd=counts['Pd'], Rh=counts['Rh'],
                   source_final_log=part.name, final_energy_Ry=float(match.group(1)), formation_eV_atom=ef,
                   formation_meV_atom=ef*1000, accuracy_Ry=accuracy, max_force_component_Ry_bohr=max_comp,
                   max_atom_force_eV_A=float(np.linalg.norm(forces, axis=1).max()*RY_EV/BOHR_ANG),
                   pressure_kbar=pressure, max_abs_stress_component_kbar=float(np.abs(stress).max()),
                   final_force_components_pass=max_comp <= force_thr, final_pressure_pass=abs(pressure) <= pressure_thr,
                   volume_A3=atoms.get_volume(), kmesh='x'.join(kmesh[:3]), kshift=' '.join(kmesh[3:]),
                   min_distance_A=float(np.min(atoms.get_all_distances(mic=True) + np.eye(nat)*1e6)))
        rows.append(row)
        write(OUT / 'structures' / (name + '.cif'), atoms)
        (OUT / 'structures' / (name + '_final_coordinates.txt')).write_text(coords + '\n')
        for file in job.iterdir():
            if file.is_file():
                manifests.append(sha(file) + '  ' + name + '/' + file.name)
    with (OUT / 'unified_results.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / 'audit.json').write_text(json.dumps(dict(reference_group='c110 final SCF, 12x12x12 shifted fcc', references_Ry_atom=refs, jobs=rows), indent=2))
    (OUT / 'source_SHA256SUMS.txt').write_text('\n'.join(manifests) + '\n')
    make_plot(rows)
    print(json.dumps(rows, indent=2))


def make_plot(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(8.8, 4.8), layout='constrained')
    energies = [r['formation_meV_atom'] for r in rows]
    bars = ax.barh([r['job'] for r in rows], energies, color=['#007F79' if v < 0 else '#B44E35' for v in energies], height=0.6)
    ax.bar_label(bars, fmt='%.2f', padding=4, fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0, color='#555555', lw=0.8)
    ax.set_xlim(-40, 125)
    ax.set_xlabel('Formation energy relative to fcc elements (meV/atom)')
    ax.set_title('Unified DFT validation: seven relaxed candidates', loc='left', fontsize=12)
    ax.spines[['top', 'right']].set_visible(False)
    fig.savefig(OUT / 'formation_energies.png', dpi=300)
    fig.savefig(OUT / 'formation_energies.pdf')
    plt.close(fig)


if __name__ == '__main__':
    main()
