"""SPDX-License-Identifier: MIT
Bounded one-job launcher. No service, network listener or shell commands.
Runtime evidence is private. Only a trusted local caller may submit requests.
"""
import hashlib
import json
from pathlib import Path
import subprocess

TARGET = 'OSS_CompileProbe'


def source_hash(code):
    return hashlib.sha256(code.replace('\r\n', '\n').strip().encode('utf-8')).hexdigest()


def validate(request):
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


def run_job(executable, config, request, evidence_dir):
    validate(request)
    folder = Path(evidence_dir)
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite another run
    input_file, result_file = folder / 'input.json', folder / 'result.json'
    input_file.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
    try:
        completed = subprocess.run(
            [str(Path(executable).resolve()), 'run', str(Path(config).resolve()),
             str(input_file.resolve()), str(result_file.resolve())],
            capture_output=True, encoding='utf-8-sig', errors='replace', timeout=55,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), shell=False)
        result = json.loads(result_file.read_text(encoding='utf-8-sig'))
        if not isinstance(result, dict):
            raise ValueError('INVALID_EVIDENCE')
        if completed.returncode != 0 or result.get('ok') is not True:
            return {'status': 'FAIL', 'reason': result.get('error', 'DESKTOP_FAILED')}
        if source_hash(result.get('source_readback', '')) != request['sha256']:
            return {'status': 'FAIL', 'reason': 'EVIDENCE_HASH_MISMATCH'}
        if result.get('compile_passed') is not True or result.get('error_count') != 0:
            return {'status': 'FAIL', 'reason': 'COMPILE_ERROR', 'evidence': result}
        return {'status': 'PASS', 'evidence': result}
    except subprocess.TimeoutExpired:
        return {'status': 'FAIL', 'reason': 'WATCHDOG_TIMEOUT'}
    except (OSError, ValueError, TypeError) as exc:
        return {'status': 'FAIL', 'reason': 'EXECUTION_OR_EVIDENCE_FAILED', 'detail': str(exc)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    parser.add_argument('config')
    parser.add_argument('request')
    parser.add_argument('evidence_dir')
    args = parser.parse_args()
    try:
        outcome = run_job(args.executable, args.config,
                          json.loads(Path(args.request).read_text(encoding='utf-8-sig')),
                          args.evidence_dir)
    except (OSError, ValueError) as exc:
        outcome = {'status': 'FAIL', 'reason': str(exc)}
    print(json.dumps(outcome, ensure_ascii=False))
    raise SystemExit(0 if outcome['status'] == 'PASS' else 1)
