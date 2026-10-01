"""Standard-library QE queue; Linux runner with detached, locked execution."""
import argparse
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

ROOT = Path(__file__).resolve().parent
HOME_RUNS = Path.home() / 'qe-paper-runs'
RUN = HOME_RUNS / 'pair_ranking_check_20260909'
LOCK = HOME_RUNS / '.pair_ranking_check_20260909.lock'
PW = Path.home() / 'software/q-e-qe-7.5/bin/pw.x'
RANKS, POOLS = 24, 4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(value + '\n', encoding='utf-8')
    temp.replace(path)


def event(message):
    print(f'[{dt.datetime.now().astimezone().isoformat(timespec="seconds")}] {message}', flush=True)


def names():
    result = json.loads((ROOT / 'jobs.json').read_text())
    if len(result) != 4 or len(set(result)) != 4:
        raise RuntimeError('Expected four unique jobs')
    return result


def verify():
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        expected, rel = line.split('  ', 1)
        target = (ROOT / rel).resolve()
        if not target.is_relative_to(ROOT) or digest(target) != expected:
            raise RuntimeError('Package checksum mismatch: ' + rel)


def verdict(log, reference):
    energies = list(re.finditer(r'^!\s+total energy\s*=\s*([-+0-9.Ee]+)\s+Ry', log, re.M))
    if not energies or 'Error in routine' in log:
        return False
    tail = log[energies[-1].end():]
    ok = 'convergence has been achieved' in tail and 'JOB DONE.' in tail
    return ok and (not reference or ('bfgs converged' in log and 'End of BFGS Geometry Optimization' in log))


def job_done(job, reference):
    if not (job / 'STATUS').exists() or (job / 'STATUS').read_text().strip() != 'DONE':
        return False
    parts = sorted(job.glob('output.part*.log'))
    return bool(parts) and verdict(parts[-1].read_text(errors='replace'), reference) and (job / ('returncode.' + parts[-1].stem.split('.')[-1])).read_text().strip() == '0'


def checkpoints(job):
    return list((job / 'scratch').glob('*.save/data-file-schema.xml'))


def worker():
    # The parent passes the flock descriptor; keeping it open holds the queue lock.
    lock_fd = int(os.environ['QE_DENSE3_LOCK_FD'])
    os.fstat(lock_fd)
    os.set_inheritable(lock_fd, False)
    try:
        verify()
        save(RUN / 'STATUS', 'RUNNING')
        for name in names():
            job = RUN / name
            reference = '_ref_' in name
            if job_done(job, reference):
                event('Skipping validated completed ' + name)
                continue
            if job.exists():
                raise RuntimeError('Unfinished job exists; preserve its checkpoint and inspect before retry: ' + str(job))
            (job / 'scratch').mkdir(parents=True)
            shutil.copytree(ROOT / 'pseudo', job / 'pseudo')
            shutil.copyfile(ROOT / 'inputs' / (name + '.in'), job / 'input.in')
            save(job / 'STATUS', 'RUNNING')
            complete = False
            for attempt in (1, 2):
                part = f'part{attempt:02d}'
                if attempt == 2:
                    inp = (job / 'input.in').read_text()
                    save(job / 'input.in', re.sub(r"restart_mode\s*=\s*'from_scratch'", "restart_mode = 'restart'", inp, count=1))
                cmd = ['mpirun', '-np', str(RANKS), str(PW), '-nk', str(POOLS), '-in', 'input.in']
                save(job / ('command.' + part + '.json'), json.dumps(dict(argv=cmd, cwd=str(job), stdin='DEVNULL', threads=1), indent=2))
                env = os.environ.copy()
                for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
                    env[key] = '1'
                event(f'Starting {name} attempt {attempt}/2')
                with (job / ('output.' + part + '.log')).open('wb') as stream:
                    rc = subprocess.run(cmd, cwd=job, env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT).returncode
                save(job / ('returncode.' + part), str(rc))
                log = (job / ('output.' + part + '.log')).read_text(errors='replace')
                save(job / 'output.log', '\n'.join(p.read_text(errors='replace') for p in sorted(job.glob('output.part*.log'))))
                if rc == 0 and verdict(log, reference):
                    save(job / 'STATUS', 'DONE')
                    complete = True
                    event('Completed ' + name)
                    break
                if attempt == 1 and 'Maximum CPU time exceeded' in log and 'JOB DONE.' in log and 'Error in routine' not in log and checkpoints(job):
                    event('Clean time-limit checkpoint; resuming ' + name)
                    continue
                break
            if not complete:
                save(job / 'STATUS', 'INCOMPLETE')
                raise RuntimeError('Job incomplete: ' + name + '; saved logs/checkpoints retained')
        if not all(job_done(RUN / n, '_ref_' in n) for n in names()):
            raise RuntimeError('Final completion count failed')
        save(RUN / 'STATUS', 'DONE')
        event('All 4 jobs validated complete')
    except Exception as exc:
        save(RUN / 'STATUS', 'INCOMPLETE')
        event(str(exc))
        return 1
    return 0


def start():
    import fcntl
    verify()
    if not PW.is_file() or not os.access(PW, os.X_OK) or not shutil.which('mpirun'):
        raise RuntimeError('QE executable or mpirun not available')
    HOME_RUNS.mkdir(parents=True, exist_ok=True)
    lock = LOCK.open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('This queue is already running; use status')
    existing = subprocess.run(['pgrep', '-x', 'pw.x'], capture_output=True, text=True)
    if existing.returncode not in (0, 1):
        raise RuntimeError('Cannot count active QE processes')
    count = len(existing.stdout.split())
    if count > 12:
        raise RuntimeError(f'{count} QE processes active; need at most 12 before launching')
    free_kib = int(re.search(r'MemAvailable:\s+(\d+)', Path('/proc/meminfo').read_text()).group(1))
    if free_kib < 24 * 1024**2:
        raise RuntimeError('Less than 24 GiB available memory')
    if shutil.disk_usage(HOME_RUNS).free < 15 * 1024**3:
        raise RuntimeError('Less than 15 GiB available disk space')
    if RUN.exists():
        for name in names():
            job = RUN / name
            if job.exists() and not job_done(job, '_ref_' in name):
                raise RuntimeError('Unfinished existing job; do not overwrite: ' + str(job))
        if all(job_done(RUN / n, '_ref_' in n) for n in names()):
            print('All 4 jobs already complete; use export')
            return
    RUN.mkdir(exist_ok=True)
    if not (RUN / 'environment.json').exists():
        save(RUN / 'environment.json', json.dumps(dict(created=dt.datetime.now().astimezone().isoformat(), pw=str(PW), pw_sha256=digest(PW), ranks=RANKS, pools=POOLS, existing_pw_processes=count, python=sys.version, uname=list(os.uname())), indent=2))
        for filename in ('jobs.json', 'SHA256SUMS', 'pseudopotential_metadata.json', 'queue.py', 'README_ZH.md'):
            shutil.copyfile(ROOT / filename, RUN / filename)
    env = os.environ.copy()
    env['QE_DENSE3_LOCK_FD'] = str(lock.fileno())
    with (RUN / 'queue.log').open('ab') as log:
        proc = subprocess.Popen([sys.executable, str(ROOT / 'queue.py'), '_worker'], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),), env=env)
    save(RUN / 'pid', str(proc.pid))
    print(f'Started PID {proc.pid}\nRun directory: {RUN}\n24 MPI ranks, 4 pools. Use status to check progress.')


def status():
    if not RUN.exists():
        print('Not started')
        return
    print('Run directory:', RUN)
    print('Queue status:', (RUN / 'STATUS').read_text().strip() if (RUN / 'STATUS').exists() else 'STARTING')
    complete = 0
    for name in names():
        file = RUN / name / 'STATUS'
        state = file.read_text().strip() if file.exists() else 'PENDING'
        complete += job_done(RUN / name, '_ref_' in name)
        print(name + ': ' + state)
    print(f'Validated completed jobs: {complete}/4')
    if (RUN / 'queue.log').exists():
        print('\n'.join((RUN / 'queue.log').read_text(errors='replace').splitlines()[-10:]))


def export():
    if not all(job_done(RUN / n, '_ref_' in n) for n in names()):
        raise RuntimeError('Export requires four validated complete jobs')
    archive = Path('/mnt/d/qe-pair-ranking-results-20260909.tar.gz')
    def filtered(info):
        return None if 'scratch' in Path(info.name).parts else info
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(RUN, arcname=RUN.name, filter=filtered)
    print(str(archive))
    print(digest(archive))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('start', 'status', 'export', '_worker'))
    args = parser.parse_args()
    try:
        result = {'start': start, 'status': status, 'export': export, '_worker': worker}[args.action]()
        sys.exit(result or 0)
    except Exception as exc:
        print('STOP:', exc, file=sys.stderr)
        sys.exit(1)
