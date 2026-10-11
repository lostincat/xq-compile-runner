# SPDX-License-Identifier: MIT
import unittest
from signature_gate import check_policy

class SignatureTests(unittest.TestCase):
    def setUp(self):
        self.policy=dict(release_id='fixture',sha256='a'*64,signer_subject='CN=Test only',signer_thumbprint='b'*40)
        self.evidence=dict(self.policy,status='Valid',timestamp_present=True)
    def test_valid_pins(self):
        check_policy(self.policy,self.evidence)
    def test_invalid_signature_conditions(self):
        for changes in [dict(status='NotSigned'),dict(status='HashMismatch'),dict(timestamp_present=False),dict(sha256='c'*64),dict(signer_thumbprint='c'*40),dict(signer_subject='CN=Other')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check_policy(self.policy,dict(self.evidence,**changes))
    def test_blank_approval_not_allowed(self):
        for field in self.policy:
            with self.subTest(field=field),self.assertRaises(ValueError):
                check_policy(dict(self.policy,**{field:''}),self.evidence)
