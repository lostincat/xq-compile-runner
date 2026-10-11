# SPDX-License-Identifier: MIT
import json
from pathlib import Path
import subprocess
import tempfile
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
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'case'
            def fake(args, **kwargs):
                self.assertFalse(kwargs['shell'])
                self.assertEqual(kwargs['timeout'], 55)
                if error:
                    raise error
                if result is not None:
                    (folder/'result.json').write_text(json.dumps(result), encoding='utf-8')
                return subprocess.CompletedProcess(args, returncode)
            with patch('runner.subprocess.run', side_effect=fake) as launch:
                output = runner.run_job('unused', 'unused', self.request, folder)
                self.assertEqual(launch.call_count, 1)  # no uncertain UI replay
                return output

    def evidence(self, **updates):
        return dict(dict(ok=True, compile_passed=True, error_count=0,
                         source_readback=self.request['code']), **updates)

    def test_pass(self):
        self.assertEqual(self.invoke(self.evidence())['status'], 'PASS')

    def test_compile_error_is_failure(self):
        self.assertEqual(self.invoke(self.evidence(compile_passed=False,error_count=1))['reason'], 'COMPILE_ERROR')

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
        self.assertEqual(self.invoke(self.evidence(source_readback='other'))['reason'], 'EVIDENCE_HASH_MISMATCH')

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch('runner.subprocess.run') as launch:
            with self.assertRaises(FileExistsError):
                runner.run_job('unused','unused',self.request,tmp)
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
