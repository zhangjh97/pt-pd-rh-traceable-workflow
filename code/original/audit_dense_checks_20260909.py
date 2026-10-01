"""Audit supplementary SCFs, including force warnings and full stress tensors."""
import csv
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from ase.io import read

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data/dft_runs'
OUT = DATA / 'supplement-final-audit-20260909'
RY_EV = 13.605693122994
NUM = r'[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(pattern, text):
    return float(re.findall(pattern, text, re.M)[-1].replace('D', 'E').replace('d', 'e'))


def normalized(text):
    return re.sub(r"restart_mode\s*=\s*'restart'", "restart_mode = 'from_scratch'", text).strip()


def audit(run, package):
    names = json.loads((run / 'jobs.json').read_text())
    assert names == json.loads((package / 'jobs.json').read_text())
    meta = json.loads((run / 'pseudopotential_metadata.json').read_text())
    assert meta == json.loads((package / 'pseudopotential_metadata.json').read_text())
    assert (run / 'STATUS').read_text().strip() == 'DONE'
    rows = []
    hashes = []
    for name in names:
        job = run / name
        inp = (job / 'input.in').read_text()
        assert normalized(inp) == normalized((package / 'inputs' / (name + '.in')).read_text()), name
        log_path = sorted(job.glob('output.part*.log'))[-1]
        log = log_path.read_text(errors='replace')
        assert (job / ('returncode.' + log_path.stem.split('.')[-1])).read_text().strip() == '0'
        assert (job / 'STATUS').read_text().strip() == 'DONE'
        assert (job / 'output.log').read_text(errors='replace').rstrip().endswith(log.rstrip())
        match = list(re.finditer(r'^!\s+total energy\s*=\s*(' + NUM + r')\s+Ry', log, re.M))[-1]
        tail = log[match.end():]
        assert 'convergence has been achieved' in tail and 'JOB DONE.' in tail and 'Error in routine' not in log
        if '_ref_' in name:
            assert 'bfgs converged' in log and 'End of BFGS Geometry Optimization' in log
        accuracy = number(r'estimated scf accuracy\s*<\s*(' + NUM + ')', tail)
        assert accuracy < number(r'conv_thr\s*=\s*(' + NUM + ')', inp)
        atoms = read(log_path, format='espresso-out', index=-1)
        forces = np.array(re.findall(r'atom\s+\d+\s+type\s+\d+\s+force\s*=\s*(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + ')', tail), dtype=float)
        assert len(forces) == len(atoms)
        stress_text = re.search(r'P=\s*' + NUM + r'\s*\n((?:[^\n]+\n){3})', tail).group(1)
        stress = np.array([[float(x) for x in line.split()[3:6]] for line in stress_text.splitlines()])
        for f in meta['files']:
            assert sha(job / 'pseudo' / f['filename']) == f['sha256']
        meshes = re.search(r'K_POINTS\s+automatic\s*\n([^\n]+)', inp).group(1).split()
        rows.append(dict(job=name, nat=len(atoms), final_log=log_path.name, energy_Ry=float(match.group(1)),
                         accuracy_Ry=accuracy, kmesh='x'.join(meshes[:3]), shift=' '.join(meshes[3:]),
                         pressure_kbar=number(r'\bP=\s*(' + NUM + ')', tail),
                         max_abs_stress_kbar=float(np.abs(stress).max()),
                         max_force_component_Ry_bohr=float(np.abs(forces).max()),
                         max_atom_force_Ry_bohr=float(np.linalg.norm(forces, axis=1).max()),
                         total_force_Ry_bohr=number(r'Total force\s*=\s*(' + NUM + ')', tail),
                         total_SCF_correction_Ry_bohr=number(r'Total SCF correction\s*=\s*(' + NUM + ')', tail),
                         force_accuracy_warning='SCF correction compared to forces is large' in tail))
        for f in job.iterdir():
            if f.is_file():
                hashes.append(sha(f) + '  ' + str(f.relative_to(DATA)))
    return rows, hashes


def main():
    OUT.mkdir(exist_ok=True)
    runs = list(DATA.rglob('kdense3_check_20260909/jobs.json'))
    assert len(runs) == 1, runs
    dense, hashes = audit(runs[0].parent, BASE / 'deployment/qe-kdense3-check-20260909')
    energies = {r['job']: r['energy_Ry'] for r in dense}
    ef = (energies['k_dense3_alloy'] - sum(n * energies['k_dense3_ref_' + e] for e, n in [('Pt', 11), ('Pd', 7), ('Rh', 2)])) * RY_EV / 20 * 1000
    prior = list(csv.DictReader((DATA / 'convergence-analysis-20260909/formation_convergence.csv').open(encoding='utf-8-sig')))
    comparison = [dict(group=r['group'], alloy_mesh=r['alloy_kmesh'], ref_mesh=r['ref_kmesh'], formation_meV_atom=float(r['formation_meV_atom'])) for r in prior if r['group'] in ('c110', 'k_coarse', 'k_dense1', 'k_dense2')]
    comparison.append(dict(group='k_dense3', alloy_mesh='8x7x7', ref_mesh='18x18x18', formation_meV_atom=ef))
    for row in comparison:
        row['delta_to_dense3_meV_atom'] = row['formation_meV_atom'] - ef
    pairs, gaps = [], []
    pair_paths = list(DATA.rglob('pair_ranking_check_20260909/jobs.json'))
    if pair_paths:
        assert len(pair_paths) == 1
        pairs, extra = audit(pair_paths[0].parent, BASE / 'deployment/qe-pair-ranking-check-20260909')
        hashes.extend(extra)
        old = {r['job']: r for r in csv.DictReader((DATA / 'main-queue-analysis-20260909/unified_results.csv').open(encoding='utf-8-sig'))}
        new = {r['job']: r for r in pairs}
        for lo, hi in [('Pt-Pd-01_Pd4Pt4', 'Pt-Pd-15_Pd4Pt4'), ('Pd-Rh-14_Pd2Rh6', 'Pd-Rh-06_PdRh3')]:
            gap = (new[hi]['energy_Ry']/new[hi]['nat'] - new[lo]['energy_Ry']/new[lo]['nat']) * RY_EV * 1000
            previous = float(old[hi]['formation_meV_atom']) - float(old[lo]['formation_meV_atom'])
            gaps.append(dict(lower_candidate=lo, higher_candidate=hi, old_gap_meV_atom=previous, new_gap_meV_atom=gap, change_meV_atom=gap-previous, ranking_preserved=gap>0))
    result = dict(dense_jobs=dense, dense_comparison=comparison, pair_results_present=bool(pair_paths), pair_jobs=pairs, pair_gaps=gaps)
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2))
    for name, rows in [('dense_job_audit.csv', dense), ('kmesh_comparison.csv', comparison), ('pair_job_audit.csv', pairs), ('pair_gaps.csv', gaps)]:
        if rows:
            with (OUT / name).open('w', newline='', encoding='utf-8-sig') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    (OUT / 'source_SHA256SUMS.txt').write_text('\n'.join(hashes) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
