"""SPDX-License-Identifier: MIT. Plan by default; real desktop actions require explicit opt-in."""
import argparse
import json
from pathlib import Path
import runner

CASES = {
    'normal': ('PASS', None),
    'syntax_error': ('FAIL', 'COMPILE_ERROR'),
    'wrong_window': ('FAIL', 'WINDOW_MISMATCH'),
    'popup': ('FAIL', 'POPUP_BLOCKED'),
    'unsaved': ('FAIL', 'UNSAVED_TEST_DOCUMENT'),
    'deadline': ('FAIL', 'DESKTOP_TIMEOUT'),
}
INSTRUCTIONS = {
    'normal': 'Open and save the disposable OSS_CompileProbe trading-type document; no other editor or modal dialog.',
    'syntax_error': 'Same disposable document; the tool submits a deliberately unknown identifier, not an order.',
    'wrong_window': 'Activate a different document manually. Expected: WINDOW_MISMATCH before any source write.',
    'popup': 'Open a genuine modal XQ dialog manually. Expected: POPUP_BLOCKED before any source write. Dismiss it yourself afterwards.',
    'unsaved': 'Make an unsaved edit in the disposable document. Expected: stop before any source write.',
    'deadline': 'Disposable document only. Uses a one-second desktop deadline; PASS requires an actual timeout response. If compilation finishes first, the test is FAIL, not a timeout proof.',
}


def assess(case, outcome):
    expected_status, expected_reason = CASES[case]
    if outcome.get('status') != expected_status:
        return 'FAIL'
    if expected_reason and not str(outcome.get('reason','')).startswith(expected_reason):
        return 'FAIL'
    if case in ('wrong_window','popup','unsaved'):
        trace=outcome.get('evidence',{}).get('trace')
        if not isinstance(trace,list) or trace:
            return 'FAIL'
    return 'PASS'


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--case',choices=CASES)
    parser.add_argument('--confirm-disposable-target')
    parser.add_argument('--executable')
    parser.add_argument('--config')
    parser.add_argument('--release')
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    report={'suite':'DESKTOP','overall':'NOT_RUN','cases':{k:{'test_status':'NOT_RUN','setup':v} for k,v in INSTRUCTIONS.items()}}
    path=Path(args.output)
    path.mkdir(parents=True,exist_ok=False)
    if args.execute:
        required=[args.case,args.executable,args.config,args.release]
        if not all(required) or args.confirm_disposable_target != runner.TARGET:
            report.update(overall='FAIL',reason='EXPLICIT_DISPOSABLE_TARGET_AND_RELEASE_REQUIRED')
        else:
            code='var: CompileProbeValue(0);\nCompileProbeValue = Close;'
            if args.case=='syntax_error':
                code='var: CompileProbeValue(0);\nCompileProbeValue = DeliberatelyUnknownCompileProbe;'
            request=dict(target=runner.TARGET,code=code,sha256=runner.source_hash(code),timeout_seconds=1 if args.case=='deadline' else 40)
            try:
                outcome=runner.run_job(args.executable,args.config,request,path/'job',args.release)
            except Exception as exc:
                outcome={'status':'FAIL','reason':str(exc)}
            test_status=assess(args.case,outcome)
            report['cases'][args.case].update(test_status=test_status,operation=outcome)
            # One case cannot qualify the entire suite.
            report.update(overall='FAIL' if test_status=='FAIL' else 'INCOMPLETE',selected_case=args.case)
    (path/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 1 if report['overall']=='FAIL' else 2

if __name__=='__main__':
    raise SystemExit(main())
