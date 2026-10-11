# SPDX-License-Identifier: MIT
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
import acceptance

class AcceptanceTests(unittest.TestCase):
    def test_plan_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp, patch('acceptance.runner.run_job') as job, patch('builtins.print'):
            self.assertEqual(acceptance.main(['--output',str(Path(tmp)/'plan')]),2)
            job.assert_not_called()
    def test_execution_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp, patch('acceptance.runner.run_job') as job, patch('builtins.print'):
            self.assertEqual(acceptance.main(['--execute','--case','normal','--output',str(Path(tmp)/'plan')]),1)
            job.assert_not_called()
    def test_expected_failure_is_not_compile_success(self):
        self.assertEqual(acceptance.assess('syntax_error',dict(status='FAIL',reason='COMPILE_ERROR')),'PASS')
        self.assertEqual(acceptance.assess('syntax_error',dict(status='PASS')),'FAIL')
    def test_popup_requires_zero_actions(self):
        for trace in [None,['source_pasted']]:
            self.assertEqual(acceptance.assess('popup',dict(status='FAIL',reason='POPUP_BLOCKED',evidence={'trace':trace})),'FAIL')
        self.assertEqual(acceptance.assess('popup',dict(status='FAIL',reason='POPUP_BLOCKED',evidence={'trace':[]})),'PASS')
    def test_signature_failure_cannot_pass_negative_case(self):
        for case in acceptance.CASES:
            self.assertEqual(acceptance.assess(case,dict(status='FAIL',reason='SIGNATURE_NOT_VALID')),'FAIL')
