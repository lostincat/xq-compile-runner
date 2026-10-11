"""SPDX-License-Identifier: MIT
Bounded one-job launcher. No service, network listener or shell commands.
Runtime evidence is private. Only a trusted local caller may submit requests.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import re
from contextlib import contextmanager
from signature_gate import verify_release

TARGET = 'OSS_CompileProbe'


def source_hash(code):
    return hashlib.sha256(code.replace('\r\n', '\n').strip().encode('utf-8')).hexdigest()


def validate(request):
    if not isinstance(request, dict):
        raise ValueError('INVALID_REQUEST')
    code = request.get('code')
    if request.get('target') != TARGET:
        raise ValueError('TARGET_MISMATCH')
    if not isinstance(code, str) or not code.strip() or '\x00' in code:
        raise ValueError('INVALID_SOURCE')
    # C# string length counts UTF-16 code units.
    if len(code.encode('utf-16-le')) // 2 > 20000:
        raise ValueError('SOURCE_TOO_LONG')
    if request.get('sha256') != source_hash(code):
        raise ValueError('HASH_MISMATCH')
    if type(request.get('timeout_seconds')) is not int or not 1 <= request['timeout_seconds'] <= 45:
        raise ValueError('INVALID_TIMEOUT')
    if set(request) != {'target', 'code', 'sha256', 'timeout_seconds'}:
        raise ValueError('UNSUPPORTED_FIELDS')


@contextmanager
def desktop_lock():
    import msvcrt
    path = Path(__file__).with_name('desktop.lock')
    with path.open('a+b') as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise ValueError('DESKTOP_BUSY')
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def check_evidence(result, request, started, finished):
    if not isinstance(result.get('source_readback'), str):
        raise ValueError('INVALID_SOURCE_EVIDENCE')
    if source_hash(result['source_readback']) != request['sha256']:
        raise ValueError('EVIDENCE_HASH_MISMATCH')
    epoch = result.get('compile_epoch')
    if type(epoch) not in (float, int) or not started <= epoch <= finished:
        raise ValueError('STALE_OR_INVALID_EVIDENCE')
    for field in ('error_count', 'warning_count'):
        if type(result.get(field)) is not int or result[field] < 0:
            raise ValueError('INVALID_COUNTS')
    if type(result.get('compile_passed')) is not bool:
        raise ValueError('INVALID_COMPILE_STATUS')
    if not isinstance(result.get('summary'), str) or not isinstance(result.get('errors'), str):
        raise ValueError('INVALID_COMPILER_TEXT')
    matches = re.findall(re.escape(TARGET) + r' 編譯(成功|發生錯誤)，\s*(\d+)項錯誤，\s*(\d+)項警告', result['summary'])
    if len(matches) != 1:
        raise ValueError('AMBIGUOUS_OR_MISSING_SUMMARY')
    state, errors, warnings = matches[0]
    if (int(errors), int(warnings)) != (result['error_count'], result['warning_count']):
        raise ValueError('SUMMARY_COUNT_MISMATCH')
    if result['compile_passed'] != (state == '成功' and int(errors) == 0):
        raise ValueError('CONTRADICTORY_COMPILE_STATUS')
    trace = result.get('trace')
    required = ['preflight_guard_pass', 'source_pasted', 'source_hash_verified', 'saved', 'compile_invoked', 'fresh_summary_captured']
    if not isinstance(trace, list) or trace[:6] != required:
        raise ValueError('INVALID_OPERATION_TRACE')
    if result['error_count'] and (not result['errors'].strip() or 'errors_captured' not in trace):
        raise ValueError('ERROR_DETAILS_MISSING')


def run_job(executable, config, request, evidence_dir, release=None):
    validate(request)
    if release is None:
        return {'status': 'FAIL', 'reason': 'RELEASE_POLICY_REQUIRED'}
    try:
        with desktop_lock():
            verify_release(executable, release)
            return _run_verified(executable, config, request, evidence_dir)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        return {'status': 'FAIL', 'reason': str(exc)}


def _run_verified(executable, config, request, evidence_dir):
    folder = Path(evidence_dir)
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite another run
    input_file, result_file = folder / 'input.json', folder / 'result.json'
    input_file.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
    (folder/'claimed.json').write_text(json.dumps({'status':'STARTED_NO_REPLAY','started':time.time()}), encoding='utf-8')
    outcome = {'status': 'FAIL', 'reason': 'INTERRUPTED_OR_INCOMPLETE'}
    try:
        started = time.time()
        completed = subprocess.run(
            [str(Path(executable).resolve()), 'run', str(Path(config).resolve()),
             str(input_file.resolve()), str(result_file.resolve())],
            capture_output=True, encoding='utf-8-sig', errors='replace', timeout=55,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), shell=False)
        result = json.loads(result_file.read_text(encoding='utf-8-sig'))
        if not isinstance(result, dict):
            raise ValueError('INVALID_EVIDENCE')
        if completed.returncode != 0 or result.get('ok') is not True:
            outcome = {'status': 'FAIL', 'reason': result.get('error', 'DESKTOP_FAILED'), 'evidence': result}
            return outcome
        check_evidence(result, request, started, time.time())
        if result.get('compile_passed') is not True or result.get('error_count') != 0:
            outcome = {'status': 'FAIL', 'reason': 'COMPILE_ERROR', 'evidence': result}
        else:
            outcome = {'status': 'PASS', 'evidence': result}
        return outcome
    except subprocess.TimeoutExpired:
        outcome = {'status': 'FAIL', 'reason': 'WATCHDOG_TIMEOUT'}
        return outcome
    except (OSError, ValueError, TypeError) as exc:
        outcome = {'status': 'FAIL', 'reason': 'EXECUTION_OR_EVIDENCE_FAILED', 'detail': str(exc)}
        return outcome
    finally:
        (folder/'outcome.json').write_text(json.dumps(outcome,ensure_ascii=False),encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    parser.add_argument('config')
    parser.add_argument('request')
    parser.add_argument('evidence_dir')
    parser.add_argument('--release', required=True)
    args = parser.parse_args()
    try:
        outcome = run_job(args.executable, args.config,
                          json.loads(Path(args.request).read_text(encoding='utf-8-sig')),
                          args.evidence_dir, args.release)
    except (OSError, ValueError) as exc:
        outcome = {'status': 'FAIL', 'reason': str(exc)}
    print(json.dumps(outcome, ensure_ascii=False))
    raise SystemExit(0 if outcome['status'] == 'PASS' else 1)
