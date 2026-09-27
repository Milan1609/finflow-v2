import unittest

import app as app_module


class ThemeAndGoogleAuthTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def test_login_exposes_all_three_appearance_modes(self):
        response = self.client.get('/login')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Light', response.data)
        self.assertIn(b'Dark', response.data)
        self.assertIn(b'System default', response.data)

    def test_google_route_is_unavailable_when_not_configured(self):
        if app_module.GOOGLE_AUTH_ENABLED:
            self.skipTest('Google OAuth is configured in this environment.')

        response = self.client.get('/auth/google')

        self.assertEqual(response.status_code, 404)

    def test_google_email_verification_accepts_oidc_boolean_values(self):
        self.assertTrue(app_module.google_email_is_verified(True))
        self.assertTrue(app_module.google_email_is_verified('true'))
        self.assertFalse(app_module.google_email_is_verified(False))
        self.assertFalse(app_module.google_email_is_verified(None))


if __name__ == '__main__':
    unittest.main()
