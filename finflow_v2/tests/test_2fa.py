import unittest
from unittest.mock import patch

import security_utils
from security_utils import (
    build_otpauth_uri,
    generate_2fa_secret,
    generate_totp_code,
    verify_totp_code,
    validate_password,
)


class TwoFactorHelperTests(unittest.TestCase):
    def test_password_policy_rejects_weak_value(self):
        self.assertEqual(validate_password('weak'), 'Password must be 12–128 characters long.')

    def test_totp_helpers_round_trip(self):
        secret = generate_2fa_secret()
        code = generate_totp_code(secret)
        self.assertTrue(verify_totp_code(secret, code))
        self.assertFalse(verify_totp_code(secret, '000000'))

    def test_otpauth_uri_contains_expected_fields(self):
        uri = build_otpauth_uri('SECRET', 'demo@example.com', 'FinFlow')
        self.assertIn('otpauth://totp/', uri)
        self.assertIn('FinFlow%3Ademo%40example.com', uri)
        self.assertIn('issuer=FinFlow', uri)

    def test_qr_data_url_falls_back_to_svg_when_pillow_is_missing(self):
        class FakeSvgImage:
            def to_string(self, encoding='unicode'):
                return '<svg></svg>'

        with patch.object(security_utils.qrcode, 'make', side_effect=[ModuleNotFoundError('No module named PIL'), FakeSvgImage()]):
            data_url = security_utils.generate_qr_code_data_url('SECRET', 'demo@example.com', 'FinFlow')

        self.assertTrue(data_url.startswith('data:image/svg+xml;base64,'))


if __name__ == '__main__':
    unittest.main()
