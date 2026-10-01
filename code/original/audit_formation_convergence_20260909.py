"""Audit the returned QE sidecar using final SCF energies, not BFGS enthalpies."""
import csv
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / 'data/dft_runs/formation_convergence_20260908_134907'
OUT = BASE / 'data/dft_runs/convergence-analysis-20260909'
PACKAGE = BASE / 'deployment/qe-formation-convergence-sidecar-20260908'
RY_EV = 13.605693122994
NUM = r'[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?'


def last(pattern, text, required=True):
    matches = re.findall(pattern, text, re.M)
    if not matches and required:
        raise ValueError(pattern)
    return float(matches[-1].replace('D', 'E').replace('d', 'e')) if matches else None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    names = (RUN / 'JOB_ORDER.txt').read_text().split()
    assert len(names) == len(set(names)) == 32
    metadata = json.loads((RUN / 'pseudopotential_metadata.json').read_text())
    rows = []
    hashes = []
    for name in names:
        job = RUN / name
        inp = (job / 'input.in').read_text()
        log = (job / 'output.log').read_text(errors='replace')
        nat = int(last(r'^\s*nat\s*=\s*(\d+)', inp))
        energy_matches = list(re.finditer(r'^!\s+total energy\s*=\s*(' + NUM + r')\s+Ry', log, re.M))
        assert energy_matches, name
        final = energy_matches[-1]
        final_tail = log[final.end():]
        assert 'convergence has been achieved' in final_tail, name
        assert 'JOB DONE.' in final_tail and 'Error in routine' not in log, name
        assert (job / 'STATUS').read_text().strip() == 'DONE', name
        assert (job / 'returncode').read_text().strip() == '0', name
        if '_ref_' in name:
            assert 'bfgs converged' in log and 'End of BFGS Geometry Optimization' in log, name
        mesh = re.search(r'K_POINTS\s+automatic\s*\n([^\n]+)', inp).group(1).split()
        positions = re.search(r'ATOMIC_POSITIONS[^\n]*\n((?:[^\n]+\n){' + str(nat) + '})', inp).group(1)
        elements = [line.split()[0] for line in positions.splitlines()]
        assert (sorted(elements) == sorted(['Pt'] * 11 + ['Pd'] * 7 + ['Rh'] * 2)) if name.endswith('_alloy') else (nat == 1)
        forces = re.findall(r'atom\s+\d+\s+type\s+\d+\s+force\s*=\s*(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + ')', final_tail)
        max_force = max((sum(float(x)**2 for x in f)**0.5 for f in forces), default=None)
        pressure = last(r'\bP=\s*(' + NUM + ')', final_tail)
        row = dict(job=name, nat=nat, ecutwfc_Ry=last(r'ecutwfc\s*=\s*(' + NUM + ')', inp),
                   ecutrho_Ry=last(r'ecutrho\s*=\s*(' + NUM + ')', inp),
                   kmesh='x'.join(mesh[:3]), kshift=' '.join(mesh[3:]),
                   final_energy_Ry=float(final.group(1)), final_enthalpy_Ry=last(r'Final enthalpy\s*=\s*(' + NUM + ')', log, False),
                   accuracy_Ry=last(r'estimated scf accuracy\s*<\s*(' + NUM + ')', final_tail),
                   pressure_kbar=pressure, max_atom_force_Ry_bohr=max_force,
                   degauss_Ry=last(r'degauss\s*=\s*(' + NUM + ')', inp),
                   input_matches_package=sha(job / 'input.in') == sha(PACKAGE / 'inputs' / (name + '.in')))
        assert row['accuracy_Ry'] < 1e-8
        for f in metadata['files']:
            assert sha(job / 'pseudo' / f['filename']) == f['sha256'], (name, f['filename'])
        for f in ('input.in', 'output.log', 'STATUS', 'returncode'):
            hashes.append(f'{sha(job / f)}  {name}/{f}')
        rows.append(row)
    (OUT / 'source_SHA256SUMS.txt').write_text('\n'.join(hashes) + '\n')
    by_name = {r['job']: r for r in rows}
    groups = []
    for group in ('c080', 'c090', 'c100', 'c110', 'c120', 'k_coarse', 'k_dense1', 'k_dense2'):
        a = by_name[group + '_alloy']
        refs = {e: by_name[group + '_ref_' + e] for e in ('Pt', 'Pd', 'Rh')}
        ef = (a['final_energy_Ry'] - sum(n * refs[e]['final_energy_Ry'] for e, n in [('Pt', 11), ('Pd', 7), ('Rh', 2)])) * RY_EV / 20
        groups.append(dict(group=group, ecutwfc_Ry=a['ecutwfc_Ry'], alloy_kmesh=a['kmesh'], ref_kmesh=refs['Pt']['kmesh'],
                           formation_eV_atom=ef, formation_meV_atom=ef*1000, alloy_energy_Ry=a['final_energy_Ry'],
                           Pt_Ry_atom=refs['Pt']['final_energy_Ry'], Pd_Ry_atom=refs['Pd']['final_energy_Ry'], Rh_Ry_atom=refs['Rh']['final_energy_Ry'],
                           alloy_pressure_kbar=a['pressure_kbar'], alloy_max_force_Ry_bohr=a['max_atom_force_Ry_bohr']))
    gmap = {r['group']: r for r in groups}
    for g in groups:
        ref = 'c120' if g['group'].startswith('c') else 'k_dense2'
        g['delta_to_series_reference_meV_atom'] = g['formation_meV_atom'] - gmap[ref]['formation_meV_atom']
        g['delta_to_c110_meV_atom'] = g['formation_meV_atom'] - gmap['c110']['formation_meV_atom']
    for filename, data in [('job_audit.csv', rows), ('formation_convergence.csv', groups)]:
        with (OUT / filename).open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (OUT / 'audit.json').write_text(json.dumps(dict(ry_to_eV=RY_EV, jobs=rows, groups=groups), indent=2))
    geometries = [re.search(r'CELL_PARAMETERS[\s\S]+?(?=K_POINTS)', (RUN / n / 'input.in').read_text()).group(0) for n in names if n.endswith('_alloy')]
    assert len(set(geometries)) == 1, 'Alloy geometry differs across convergence groups'
    env = (RUN / 'environment.txt').read_text()
    env_checks = []
    for digest, remote in re.findall(r'^([a-f0-9]{64})\s+(.+)$', env, re.M):
        if '/inputs/' in remote:
            local = PACKAGE / 'inputs' / Path(remote).name
        elif '/pseudo/' in remote:
            local = PACKAGE / 'pseudo' / Path(remote).name
        else:
            continue
        assert sha(local) == digest, remote
        env_checks.append(remote)
    assert len(env_checks) == 35
    make_plot(groups)
    print(json.dumps(groups, indent=2))
    print('INPUT_MATCHES', sum(r['input_matches_package'] for r in rows), '/32')
    print('MAX_REFERENCE_PRESSURE', max(abs(r['pressure_kbar']) for r in rows if '_ref_' in r['job']))


def make_plot(groups):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'pdf.fonttype': 42})
    g = {r['group']: r for r in groups}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), layout='constrained')
    sets = [['c080', 'c090', 'c100', 'c110', 'c120'], ['k_coarse', 'c110', 'k_dense1', 'k_dense2']]
    for i, (ax, names) in enumerate(zip(axes, sets)):
        x = [g[n]['ecutwfc_Ry'] for n in names] if i == 0 else list(range(4))
        ax.plot(x, [g[n]['formation_meV_atom'] for n in names], '-o', color=['#007F79', '#B44E35'][i], lw=1.6)
        ax.set_ylabel('Formation energy (meV/atom)')
        ax.set_title(['(a) Plane-wave cutoff', '(b) Paired k-point meshes'][i], loc='left', fontsize=12)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=0.2)
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)
        if i == 0:
            ax.set_xlabel('Wavefunction cutoff (Ry)')
            ax.set_xticks(x)
        else:
            ax.set_xticks(x, [g[n]['alloy_kmesh'] + '\n' + g[n]['ref_kmesh'] for n in names], fontsize=9)
            ax.set_xlabel('Alloy mesh / elemental-reference mesh')
    fig.savefig(OUT / 'formation_convergence.png', dpi=300)
    fig.savefig(OUT / 'formation_convergence.pdf')
    plt.close(fig)


if __name__ == '__main__':
    main()
