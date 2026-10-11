"""SPDX-License-Identifier: MIT. Inspect signatures without executing the target."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def check_policy(policy, evidence):
    if not isinstance(policy, dict) or not isinstance(evidence, dict):
        raise ValueError('INVALID_SIGNATURE_DATA')
    if not policy.get('release_id') or not re.fullmatch('[0-9a-fA-F]{64}', policy.get('sha256', '')):
        raise ValueError('RELEASE_NOT_APPROVED')
    if not policy.get('signer_subject') or not re.fullmatch('[0-9a-fA-F]{40}', policy.get('signer_thumbprint', '')):
        raise ValueError('PUBLISHER_NOT_APPROVED')
    if evidence.get('status') != 'Valid':
        raise ValueError('SIGNATURE_NOT_VALID')
    if evidence.get('timestamp_present') is not True:
        raise ValueError('TIMESTAMP_MISSING')
    for key in ('sha256', 'signer_thumbprint'):
        if str(evidence.get(key, '')).lower() != policy[key].lower():
            raise ValueError('RELEASE_OR_SIGNER_MISMATCH')
    if evidence.get('signer_subject') != policy['signer_subject']:
        raise ValueError('PUBLISHER_MISMATCH')


def verify_release(executable, policy_path):
    policy = json.loads(Path(policy_path).read_text(encoding='utf-8-sig'))
    # Validate the approval template before any OS command, fail closed on blank fields.
    check_policy(policy, dict(policy, status='Valid', timestamp_present=True))
    if hashlib.sha256(Path(executable).read_bytes()).hexdigest() != policy['sha256'].lower():
        raise ValueError('RELEASE_HASH_MISMATCH')
    if os.name != 'nt':
        raise ValueError('WINDOWS_REQUIRED')
    shell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-File',
                             str(Path(__file__).with_name('Inspect-Signature.ps1')),
                             '-Executable', str(Path(executable).resolve())],
                            capture_output=True, text=True, timeout=30,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), shell=False)
    if result.returncode:
        raise ValueError('SIGNATURE_INSPECTION_FAILED')
    evidence = json.loads(result.stdout.lstrip('\ufeff'))
    check_policy(policy, evidence)
    return evidence


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    parser.add_argument('release')
    args = parser.parse_args()
    try:
        verify_release(args.executable, args.release)
        report = {'status': 'PASS', 'scope': 'signature_and_release_only', 'desktop': 'NOT_RUN'}
    except Exception as exc:
        report = {'status': 'FAIL', 'reason': str(exc), 'desktop': 'NOT_RUN'}
    print(json.dumps(report))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
