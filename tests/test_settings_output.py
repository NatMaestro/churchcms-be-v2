"""
Loading settings must not write anything to stdout: on Render, stdout is the
log stream, and settings used to print the full DATABASES dict (password included).
"""
import contextlib
import importlib
import io

from django.test import SimpleTestCase


class SettingsOutputTests(SimpleTestCase):
    def test_loading_settings_prints_nothing(self):
        import config.settings as settings_module

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            importlib.reload(settings_module)

        self.assertEqual(buffer.getvalue(), '')
