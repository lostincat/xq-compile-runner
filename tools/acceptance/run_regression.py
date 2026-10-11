"""SPDX-License-Identifier: MIT. Local isolated tests only; never launches XQ."""
import argparse
import json
from pathlib import Path
import unittest

parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
args=parser.parse_args()
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
report=dict(suite='SIMULATED',status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',
            tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
            desktop_status='NOT_RUN',unsigned_executable_executed=False,
            note='Desktop subprocess and signature inspection mocked; Windows file-lock contention tested directly.')
with Path(args.output).open('x',encoding='utf-8') as f:
    json.dump(report,f,ensure_ascii=False,indent=2)
raise SystemExit(0 if report['status']=='PASS' else 1)
