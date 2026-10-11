# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import subprocess
import tempfile
import time
import copy
from contextlib import nullcontext
import unittest
from unittest.mock import patch
import runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.request = dict(target=runner.TARGET, code='// synthetic fixture\n',
                            timeout_seconds=10, sha256=runner.source_hash('// synthetic fixture\n'))

    def test_newline_hash(self):
        self.assertEqual(runner.source_hash(' A\r\nB '), runner.source_hash('A\nB'))

    def test_target_rejected_before_launch(self):
        self.request['target'] = 'ExistingStrategy'
        with patch('runner.subprocess.run') as launch:
            with self.assertRaisesRegex(ValueError, 'TARGET_MISMATCH'):
                runner.run_job('unused', 'unused', self.request, 'unused')
            launch.assert_not_called()

    def test_invalid_requests(self):
        for fields in [dict(code=''), dict(code='\x00'), dict(code='x'*20001),
                       dict(sha256='bad'), dict(timeout_seconds=0), dict(timeout_seconds=46),
                       dict(timeout_seconds=True), dict(test_force_compile_timeout=True)]:
            with self.subTest(fields=list(fields)):
                with self.assertRaises(ValueError):
                    runner.validate(dict(self.request, **fields))

    def invoke(self, result=None, error=None, returncode=0):
        result=copy.deepcopy(result)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'case'
            def fake(args, **kwargs):
                self.assertFalse(kwargs['shell'])
                self.assertEqual(kwargs['timeout'], 55)
                if error:
                    raise error
                if result is not None:
                    if isinstance(result, dict) and result.get('ok'):
                        result.setdefault('compile_epoch', time.time())
                    (folder/'result.json').write_text(json.dumps(result), encoding='utf-8')
                return subprocess.CompletedProcess(args, returncode)
            with patch('runner.subprocess.run', side_effect=fake) as launch, patch('runner.verify_release'), patch('runner.desktop_lock', return_value=nullcontext()):
                output = runner.run_job('unused', 'unused', self.request, folder, 'approved-fixture')
                self.assertEqual(launch.call_count, 1)  # no uncertain UI replay
                self.assertEqual(json.loads((folder/'outcome.json').read_text(encoding='utf-8'))['status'], output['status'])
                return output

    def evidence(self, **updates):
        value = dict(ok=True, compile_passed=True, error_count=0, warning_count=0, errors='',
                     summary=runner.TARGET+' 編譯成功，0項錯誤，0項警告',
                     trace=['preflight_guard_pass','source_pasted','source_hash_verified','saved','compile_invoked','fresh_summary_captured'],
                     source_readback=self.request['code'])
        value.update(updates)
        return value

    def test_pass(self):
        self.assertEqual(self.invoke(self.evidence())['status'], 'PASS')

    def test_compile_error_is_failure(self):
        evidence=self.evidence(compile_passed=False,error_count=1,errors='synthetic error',summary=runner.TARGET+' 編譯發生錯誤，1項錯誤，0項警告')
        evidence['trace'].append('errors_captured')
        self.assertEqual(self.invoke(evidence)['reason'], 'COMPILE_ERROR')

    def test_popup_and_window_failure(self):
        for reason in ['POPUP_BLOCKED', 'WINDOW_MISMATCH']:
            self.assertEqual(self.invoke(dict(ok=False,error=reason),returncode=1)['reason'], reason)

    def test_timeout(self):
        self.assertEqual(self.invoke(error=subprocess.TimeoutExpired('fixture',55))['reason'], 'WATCHDOG_TIMEOUT')

    def test_os_block(self):
        self.assertEqual(self.invoke(error=PermissionError('blocked'))['status'], 'FAIL')

    def test_missing_evidence(self):
        self.assertEqual(self.invoke()['status'], 'FAIL')

    def test_invalid_evidence_shape(self):
        self.assertEqual(self.invoke([])['status'], 'FAIL')

    def test_wrong_source(self):
        self.assertEqual(self.invoke(self.evidence(source_readback='other'))['detail'], 'EVIDENCE_HASH_MISMATCH')

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch('runner.subprocess.run') as launch, patch('runner.verify_release'), patch('runner.desktop_lock',return_value=nullcontext()):
            self.assertEqual(runner.run_job('unused','unused',self.request,tmp,'fixture')['status'],'FAIL')
            launch.assert_not_called()

    def test_stale_and_future_evidence(self):
        for epoch in [0, time.time()+1000, float('nan'), True]:
            self.assertEqual(self.invoke(self.evidence(compile_epoch=epoch))['status'],'FAIL')

    def test_malformed_and_conflicting_evidence(self):
        for fields in [dict(source_readback=[]),dict(error_count=True),dict(warning_count=-1),
                       dict(summary='old unrelated message'),dict(compile_passed=False),
                       dict(trace=[]),dict(summary=(runner.TARGET+' 編譯成功，0項錯誤，0項警告')*2)]:
            self.assertEqual(self.invoke(self.evidence(**fields))['status'],'FAIL')

    def test_runtime_guard_failures_are_terminal(self):
        for reason in ['CLIPBOARD_CHANGED','SOURCE_CHANGED_DURING_COMPILE','UNSAVED_TEST_DOCUMENT','DESKTOP_TIMEOUT']:
            self.assertEqual(self.invoke(dict(ok=False,error=reason),returncode=1)['reason'],reason)

    def test_multiple_errors_captured(self):
        evidence=self.evidence(compile_passed=False,error_count=2,errors='first synthetic error\nsecond synthetic error',summary=runner.TARGET+' 編譯發生錯誤，2項錯誤，0項警告')
        evidence['trace'].append('errors_captured')
        self.assertEqual(self.invoke(evidence)['reason'],'COMPILE_ERROR')
        evidence['errors']=''
        self.assertEqual(self.invoke(evidence)['detail'],'ERROR_DETAILS_MISSING')

    def test_invalid_request_container(self):
        for request in [None,[],True,'text']:
            with self.assertRaisesRegex(ValueError,'INVALID_REQUEST'):
                runner.validate(request)

    def test_interrupted_job_keeps_claim_and_cannot_replay(self):
        with tempfile.TemporaryDirectory() as tmp, patch('runner.verify_release'), patch('runner.desktop_lock',return_value=nullcontext()):
            folder=Path(tmp)/'interrupted'
            with patch('runner.subprocess.run',side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                runner.run_job('unused','unused',self.request,folder,'fixture')
            self.assertTrue((folder/'claimed.json').exists())
            self.assertEqual(json.loads((folder/'outcome.json').read_text())['reason'],'INTERRUPTED_OR_INCOMPLETE')
            with patch('runner.subprocess.run') as launch:
                self.assertEqual(runner.run_job('unused','unused',self.request,folder,'fixture')['status'],'FAIL')
                launch.assert_not_called()

    def test_signature_gate_stops_launch(self):
        with patch('runner.subprocess.run') as launch, patch('runner.desktop_lock',return_value=nullcontext()), patch('runner.verify_release',side_effect=ValueError('SIGNATURE_NOT_VALID')):
            self.assertEqual(runner.run_job('unused','unused',self.request,'unused','fixture')['reason'],'SIGNATURE_NOT_VALID')
            launch.assert_not_called()

    def test_release_policy_required(self):
        with patch('runner.subprocess.run') as launch:
            self.assertEqual(runner.run_job('unused','unused',self.request,'unused')['reason'],'RELEASE_POLICY_REQUIRED')
            launch.assert_not_called()

    @unittest.skipUnless(__import__('os').name=='nt','Windows locking test')
    def test_concurrent_launch_blocked(self):
        with runner.desktop_lock(), patch('runner.subprocess.run') as launch:
            self.assertEqual(runner.run_job('unused','unused',self.request,'unused','fixture')['reason'],'DESKTOP_BUSY')
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
