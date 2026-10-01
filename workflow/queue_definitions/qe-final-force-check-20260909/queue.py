"""Warm-start precision checks in two bounded MPI lanes, using copied checkpoints."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parent
HOME_RUNS = Path.home() / 'qe-paper-runs'
RUN = HOME_RUNS / 'final_force_check_20260909'
LOCK = HOME_RUNS / '.final_force_check_20260909.lock'
PW = Path.home() / 'software/q-e-qe-7.5/bin/pw.x'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, text):
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(text + '\n', encoding='utf-8')
    tmp.replace(p)


def event(text):
    print(f'[{dt.datetime.now().astimezone().isoformat(timespec="seconds")}] {text}', flush=True)


def specs():
    return json.loads((ROOT / 'jobs.json').read_text())


def verify():
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        checksum, rel = line.split('  ', 1)
        p = (ROOT / rel).resolve()
        if not p.is_relative_to(ROOT) or sha(p) != checksum:
            raise RuntimeError('Package checksum mismatch: ' + rel)


def normalized(text):
    return re.sub(r"restart_mode\s*=\s*'(restart|from_scratch)'", "restart_mode = 'from_scratch'", text).strip()


def source_for(spec):
    return HOME_RUNS / spec['source_run'] / spec['source_job']


def checkpoint_for(spec):
    return source_for(spec) / 'scratch' / (spec['prefix'] + '.save')


def verdict(log):
    matches = list(re.finditer(r'^!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry', log, re.M))
    if not matches or 'Error in routine' in log:
        return False
    tail = log[matches[-1].end():]
    accuracy = re.search(r'estimated scf accuracy\s*<\s*([-+0-9.Ee]+)', tail)
    return bool(accuracy and float(accuracy.group(1)) < 1e-10 and 'convergence has been achieved' in tail and 'JOB DONE.' in tail)


def complete(job):
    parts = sorted(job.glob('output.part*.log'))
    if not parts or not (job / 'STATUS').exists():
        return False
    rc = job / ('returncode.' + parts[-1].stem.split('.')[-1])
    return rc.exists() and rc.read_text().strip() == '0' and verdict(parts[-1].read_text(errors='replace'))


def input_text(text, seconds, restart=False):
    text, n = re.subn(r"restart_mode\s*=\s*'[^']+'", "restart_mode = '" + ('restart' if restart else 'from_scratch') + "'", text)
    if n != 1:
        raise RuntimeError('Expected one restart_mode')
    text, n = re.subn(r'conv_thr\s*=\s*[-+0-9.eEdD]+', 'conv_thr = 1.0d-10', text)
    if n != 1:
        raise RuntimeError('Expected one conv_thr')
    text, n = re.subn(r'max_seconds\s*=\s*[-+0-9.eEdD]+', 'max_seconds = ' + str(seconds), text)
    if n != 1:
        raise RuntimeError('Expected one max_seconds')
    if not restart:
        text = re.sub(r'(&ELECTRONS\s*\n)', r"\1  startingpot = 'file'\n  startingwfc = 'file'\n", text, count=1, flags=re.I)
    return text


def run_job(spec, deadline):
    job = RUN / spec['name']
    if complete(job):
        event('Skipping validated complete ' + spec['name'])
        return True
    if job.exists():
        event('Unfinished directory retained; inspect before retry: ' + str(job))
        return False
    if deadline - time.time() < 1200:
        event('Budget exhausted before starting ' + spec['name'])
        return False
    job.mkdir()
    save(job / 'STATUS', 'COPYING_CHECKPOINT')
    source = source_for(spec)
    shutil.copytree(source / 'pseudo', job / 'pseudo')
    dest = job / 'scratch' / (spec['prefix'] + '.save')
    event('Copying converged checkpoint for ' + spec['name'])
    shutil.copytree(checkpoint_for(spec), dest)
    save(job / 'checkpoint_source.json', json.dumps(dict(source=str(checkpoint_for(spec)), xml_sha256=sha(dest / 'data-file-schema.xml'), copied=True), indent=2))
    original = (ROOT / 'inputs' / (spec['name'] + '.in')).read_text()
    save(job / 'source_input.in', original)
    for attempt in (1, 2):
        seconds = min(14400, int(deadline - time.time()) - 600)
        if seconds < 600:
            save(job / 'STATUS', 'BUDGET_EXHAUSTED')
            return False
        part = f'part{attempt:02d}'
        text = input_text(original, seconds, restart=attempt > 1)
        save(job / 'input.in', text)
        save(job / ('input.' + part + '.in'), text)
        cmd = ['mpirun', '-np', str(spec['ranks']), str(PW), '-nk', str(spec['pools']), '-in', 'input.in']
        save(job / ('command.' + part + '.json'), json.dumps(dict(argv=cmd, cwd=str(job), threads=1, max_seconds=seconds, input_sha256=sha(job / 'input.in')), indent=2))
        env = os.environ.copy()
        for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
            env[key] = '1'
        save(job / 'STATUS', 'RUNNING')
        event(f'Starting {spec["name"]} attempt {attempt}/2 ({spec["ranks"]} ranks)')
        with (job / ('output.' + part + '.log')).open('wb') as stream:
            rc = subprocess.run(cmd, cwd=job, env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT).returncode
        save(job / ('returncode.' + part), str(rc))
        log = (job / ('output.' + part + '.log')).read_text(errors='replace')
        save(job / 'output.log', '\n'.join(p.read_text(errors='replace') for p in sorted(job.glob('output.part*.log'))))
        if rc == 0 and verdict(log):
            tail = log[list(re.finditer(r'^!\s+total energy', log, re.M))[-1].start():]
            warning = 'SCF correction compared to forces is large' in tail
            save(job / 'STATUS', 'DONE_FORCE_WARNING' if warning else 'DONE')
            event('Completed ' + spec['name'] + ('; force warning remains' if warning else ''))
            return True
        if attempt == 1 and 'Maximum CPU time exceeded' in log and 'JOB DONE.' in log and 'Error in routine' not in log and (dest / 'data-file-schema.xml').exists():
            event('Clean timeout; continuing ' + spec['name'])
            continue
        break
    save(job / 'STATUS', 'INCOMPLETE')
    event('Incomplete ' + spec['name'])
    return False


def lane(jobs, deadline):
    for spec in jobs:
        try:
            if not run_job(spec, deadline):
                return False
        except Exception as exc:
            job = RUN / spec['name']
            if job.exists() and not complete(job):
                save(job / 'STATUS', 'FAILED')
            event(spec['name'] + ': ' + str(exc))
            return False
    return True


def worker():
    fd = int(os.environ['QE_FORCE_LOCK_FD'])
    os.fstat(fd)
    os.set_inheritable(fd, False)
    save(RUN / 'STATUS', 'RUNNING')
    deadline = float(os.environ['QE_FORCE_DEADLINE'])
    jobs = specs()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(lane, [s for s in jobs if s['ranks'] == ranks], deadline) for ranks in (12, 24)]
        ok = all([result.result() for result in results])
    ok = ok and all(complete(RUN / s['name']) for s in jobs)
    warnings = any((RUN / s['name'] / 'STATUS').exists() and 'WARNING' in (RUN / s['name'] / 'STATUS').read_text() for s in jobs)
    save(RUN / 'STATUS', ('DONE_REVIEW_FORCES' if warnings else 'DONE') if ok else 'INCOMPLETE')
    event('Queue finished; inspect all forces and stresses before accepting geometry quality')
    return 0 if ok else 1


def start(hours):
    import fcntl
    verify()
    HOME_RUNS.mkdir(exist_ok=True, parents=True)
    lock = LOCK.open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    active = subprocess.run(['pgrep', '-x', 'pw.x'], capture_output=True, text=True)
    if active.returncode not in (0, 1) or active.stdout.strip():
        raise RuntimeError('QE is already active or process check failed; do not start another queue')
    if not PW.is_file() or not os.access(PW, os.X_OK) or not shutil.which('mpirun'):
        raise RuntimeError('QE/MPI executable unavailable')
    available = int(re.search(r'MemAvailable:\s+(\d+)', Path('/proc/meminfo').read_text()).group(1))
    if available < 40 * 1024**2:
        raise RuntimeError('Need at least 40 GiB available memory')
    needed = 0
    for spec in specs():
        source = source_for(spec)
        log = source / spec['source_log']
        rc = source / ('returncode.' + log.stem.split('.')[-1])
        if sha(log) != spec['source_log_sha256'] or rc.read_text().strip() != '0' or (source / 'STATUS').read_text().strip() != 'DONE':
            raise RuntimeError('Source differs from audited successful result: ' + str(source))
        if normalized((source / 'input.in').read_text()) != normalized((ROOT / 'inputs' / (spec['name'] + '.in')).read_text()):
            raise RuntimeError('Source input mismatch: ' + spec['name'])
        for filename, expected in spec['pseudo_sha256'].items():
            if sha(source / 'pseudo' / filename) != expected:
                raise RuntimeError('Source pseudo mismatch: ' + filename)
        cp = checkpoint_for(spec)
        if not (cp / 'data-file-schema.xml').is_file() or not list(cp.glob('charge-density*')) or not list(cp.glob('wfc*')):
            raise RuntimeError('Saved density/wavefunctions missing: ' + str(cp) + '; refusing a cold start')
        needed += sum(p.stat().st_size for p in cp.rglob('*') if p.is_file())
        if (RUN / spec['name']).exists() and not complete(RUN / spec['name']):
            raise RuntimeError('Unfinished target retained; inspect before retry: ' + spec['name'])
    if shutil.disk_usage(HOME_RUNS).free < needed + 20*1024**3:
        raise RuntimeError('Not enough space to copy checkpoints and retain original data')
    if all(complete(RUN / s['name']) for s in specs()):
        print('All four already complete; use export')
        return
    RUN.mkdir(exist_ok=True)
    for filename in ('jobs.json', 'queue.py', 'README_ZH.md', 'SHA256SUMS'):
        if not (RUN / filename).exists():
            shutil.copyfile(ROOT / filename, RUN / filename)
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    save(RUN / ('environment_' + stamp + '.json'), json.dumps(dict(created=stamp, pw_sha256=sha(PW), python=sys.version, hours=hours, memory_available_kib=available, checkpoint_copy_bytes=needed, argv=sys.argv), indent=2))
    env = os.environ.copy()
    env['QE_FORCE_LOCK_FD'] = str(lock.fileno())
    env['QE_FORCE_DEADLINE'] = str(time.time() + hours*3600)
    with (RUN / 'queue.log').open('ab') as stream:
        proc = subprocess.Popen([sys.executable, '-I', str(ROOT / 'queue.py'), '_worker'], stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),), env=env)
    save(RUN / 'pid', str(proc.pid))
    print(f'Started PID {proc.pid}; 12+24 MPI ranks; planning budget {hours} hours\nRun directory: {RUN}')


def status():
    if not RUN.exists():
        print('Not started')
        return
    print('Run directory:', RUN)
    print('Queue status:', (RUN / 'STATUS').read_text().strip() if (RUN / 'STATUS').exists() else 'STARTING')
    for spec in specs():
        path = RUN / spec['name'] / 'STATUS'
        print(spec['name'] + ': ' + (path.read_text().strip() if path.exists() else 'PENDING'))
    print('SCF completed:', sum(complete(RUN / s['name']) for s in specs()), '/4')
    if (RUN / 'queue.log').exists():
        print('\n'.join((RUN / 'queue.log').read_text(errors='replace').splitlines()[-12:]))


def export():
    if not RUN.exists():
        raise RuntimeError('No results')
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = Path('/mnt/d') / ('qe-final-force-results-' + stamp + '.tar.gz')
    with tarfile.open(path, 'w:gz') as tar:
        tar.add(RUN, arcname=RUN.name, filter=lambda info: None if 'scratch' in Path(info.name).parts else info)
    print(path)
    print('SHA256:', sha(path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'status', 'export', '_worker'])
    parser.add_argument('--hours', type=float, default=10)
    args = parser.parse_args()
    try:
        if not 1 <= args.hours <= 12:
            raise RuntimeError('Hours must be between 1 and 12')
        result = start(args.hours) if args.action == 'start' else {'status': status, 'export': export, '_worker': worker}[args.action]()
        sys.exit(result or 0)
    except Exception as exc:
        print('STOP:', exc, file=sys.stderr)
        sys.exit(1)
