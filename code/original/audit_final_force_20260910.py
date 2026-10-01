"""Audit returned tight-SCF results without altering source calculations."""
import csv
import json
from pathlib import Path
import re
import numpy as np
from ase.io import read
from audit_dense_checks_20260909 import NUM, RY_EV, number, sha

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data/dft_runs'
RUN = DATA / 'final_force_check_20260909'
OUT = DATA / 'final-force-audit-20260910'
FORCE_FACTOR = RY_EV / 0.529177210903


def canonical(text):
    text = re.sub(r"restart_mode\s*=\s*'[^']+'", "restart_mode='from_scratch'", text)
    text = re.sub(r'max_seconds\s*=\s*' + NUM, 'max_seconds=0', text)
    text = re.sub(r'conv_thr\s*=\s*' + NUM, 'conv_thr=0', text)
    text = re.sub(r"starting(?:pot|wfc)\s*=\s*'file'", '', text)
    return re.sub(r'\s+', '', text)


def parse(log):
    matches = list(re.finditer(r'^!\s+total energy\s*=\s*(' + NUM + r')\s+Ry', log, re.M))
    assert matches, 'Missing final energy'
    tail = log[matches[-1].end():]
    assert 'convergence has been achieved' in tail and 'JOB DONE.' in tail
    assert 'Error in routine' not in log
    forces = np.array(re.findall(r'atom\s+\d+\s+type\s+\d+\s+force\s*=\s*(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + ')', tail), dtype=float)
    stress_text = re.search(r'P=\s*' + NUM + r'\s*\n((?:[^\n]+\n){3})', tail).group(1)
    stress = np.array([[float(x) for x in line.split()[3:6]] for line in stress_text.splitlines()])
    assert forces.ndim == 2 and forces.shape[1] == 3 and stress.shape == (3, 3)
    return dict(energy_Ry=float(matches[-1].group(1)), accuracy_Ry=number(r'estimated scf accuracy\s*<\s*(' + NUM + ')', tail),
                pressure_kbar=number(r'\bP=\s*(' + NUM + ')', tail),
                total_force_Ry_bohr=number(r'Total force\s*=\s*(' + NUM + ')', tail),
                correction_Ry_bohr=number(r'Total SCF correction\s*=\s*(' + NUM + ')', tail),
                warning='SCF correction compared to forces is large' in tail,
                forces=forces, stress=stress)


def main():
    specs = json.loads((RUN / 'jobs.json').read_text())
    assert specs == json.loads((BASE / 'deployment/qe-final-force-check-20260909/jobs.json').read_text())
    assert (RUN / 'STATUS').read_text().strip() == 'DONE_REVIEW_FORCES'
    hashes, rows = [], []
    for spec in specs:
        job = RUN / spec['name']
        parent = DATA / spec['source_run']
        if spec['source_run'] == 'kdense3_check_20260909':
            parent = DATA / 'qe-kdense3-results-20260909' / spec['source_run']
        source = parent / spec['source_job']
        assert sha(source / spec['source_log']) == spec['source_log_sha256']
        inp = (job / 'input.in').read_text()
        old_inp = (source / 'input.in').read_text()
        assert canonical(inp) == canonical(old_inp)
        assert (job / 'source_input.in').read_text().strip() == old_inp.strip()
        assert "startingpot = 'file'" in inp and "startingwfc = 'file'" in inp
        assert number(r'conv_thr\s*=\s*(' + NUM + ')', inp) == 1e-10
        parts = sorted(job.glob('output.part*.log'))
        latest = parts[-1]
        part = latest.stem.split('.')[-1]
        assert (job / ('returncode.' + part)).read_text().strip() == '0'
        cmd = json.loads((job / ('command.' + part + '.json')).read_text())
        assert sha(job / ('input.' + part + '.in')) == cmd['input_sha256']
        assert sha(job / 'input.in') == cmd['input_sha256']
        assert cmd['argv'][2] == str(spec['ranks']) and cmd['argv'][5] == str(spec['pools'])
        log = latest.read_text(errors='replace')
        assert (job / 'output.log').read_text(errors='replace').rstrip().endswith(log.rstrip())
        assert 'Starting wfcs from file' in log and 'The initial density is read from file' in log
        old = parse((source / spec['source_log']).read_text(errors='replace'))
        new = parse(log)
        assert new['accuracy_Ry'] < 1e-10
        assert (job / 'STATUS').read_text().strip() == ('DONE_FORCE_WARNING' if new['warning'] else 'DONE')
        atoms = read(job / 'input.in', format='espresso-in')
        actual = read(latest, format='espresso-out', index=-1)
        assert atoms.get_chemical_symbols() == actual.get_chemical_symbols()
        assert np.allclose(atoms.cell, actual.cell, rtol=0, atol=1e-4)
        assert np.allclose(atoms.positions, actual.positions, rtol=0, atol=1e-4)
        assert len(new['forces']) == len(atoms) == len(old['forces'])
        for name, expected in spec['pseudo_sha256'].items():
            assert sha(job / 'pseudo' / name) == expected
        n = len(atoms)
        row = dict(job=spec['name'], nat=n, old_energy_Ry=old['energy_Ry'], new_energy_Ry=new['energy_Ry'],
                   delta_meV_atom=(new['energy_Ry'] - old['energy_Ry']) * RY_EV * 1000 / n,
                   scf_accuracy_Ry=new['accuracy_Ry'], force_warning=new['warning'],
                   old_correction_Ry_bohr=old['correction_Ry_bohr'], correction_Ry_bohr=new['correction_Ry_bohr'],
                   correction_eV_A=new['correction_Ry_bohr'] * FORCE_FACTOR,
                   total_force_Ry_bohr=new['total_force_Ry_bohr'],
                   correction_to_total_force=new['correction_Ry_bohr'] / new['total_force_Ry_bohr'],
                   max_atom_force_eV_A=float(np.linalg.norm(new['forces'], axis=1).max()) * FORCE_FACTOR,
                   max_atom_force_change_eV_A=float(np.linalg.norm(new['forces'] - old['forces'], axis=1).max()) * FORCE_FACTOR,
                   old_pressure_kbar=old['pressure_kbar'], pressure_kbar=new['pressure_kbar'],
                   max_abs_stress_kbar=float(np.abs(new['stress']).max()))
        for i in range(3):
            for j in range(3):
                row[f'stress_{i+1}{j+1}_kbar'] = float(new['stress'][i, j])
        rows.append(row)
        for folder in (job, source):
            for p in sorted(folder.rglob('*')):
                if p.is_file() and 'scratch' not in p.parts:
                    hashes.append(sha(p) + '  ' + p.relative_to(DATA).as_posix())
    OUT.mkdir(exist_ok=True)
    with (OUT / 'comparison.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = dict(validated_jobs=len(rows), transfer_archive_checksum_verified=False, rows=rows)
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (OUT / 'source_SHA256SUMS.txt').write_text('\n'.join(sorted(set(hashes))) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
