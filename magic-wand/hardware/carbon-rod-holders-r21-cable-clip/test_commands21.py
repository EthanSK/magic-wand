#!/usr/bin/env python3
"""Exercise the one-object temperature boundary with real R21 code and unsafe mutations."""
from pathlib import Path
import json
import re
import unittest
import zipfile
import project21 as project


class ExecutableTemperatureBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        archive = Path(__file__).parent / 'exports/R21-A1-mini-PETG.gcode.3mf'
        with zipfile.ZipFile(archive) as z:
            cls.config = json.loads(z.read('Metadata/project_settings.config'))
            cls.text = z.read('Metadata/plate_1.gcode').decode()
        cls.expected = project.p19.settings()

    def check(self, text):
        return project.check_commands(self.config, text, self.expected)

    def test_real_one_object_file_without_cancellation_labels(self):
        self.assertNotIn('; start printing object,', self.text)
        self.assertTrue(self.check(self.text)['passed'])

    def test_rejects_205_degree_wait(self):
        text, count = re.subn(r'(?m)^(M109\s+S)255\b', r'\g<1>205', self.text)
        self.assertGreater(count, 0)
        with self.assertRaises(AssertionError): self.check(text)

    def test_rejects_only_conditional_printing_waits(self):
        text, count = re.subn(r'(?m)^(M109\s+S255[^\n]*)', r'M622 J1\n\1\nM623', self.text)
        self.assertGreater(count, 0)
        with self.assertRaises(AssertionError): self.check(text)

    def test_rejects_a_bed_target_without_a_wait(self):
        text, count = re.subn(r'(?m)^M190(\s+S70\b)', r'M140\1', self.text)
        self.assertGreater(count, 0)
        with self.assertRaises(AssertionError): self.check(text)

    def test_rejects_temperature_drop_during_model_work(self):
        match = re.search(r'^; FEATURE: (?!Custom\b)\S[^\n]*\n', self.text, re.M)
        self.assertIsNotNone(match)
        text = self.text[:match.end()] + 'M104 S205\n' + self.text[match.end():]
        with self.assertRaises(AssertionError): self.check(text)


if __name__ == '__main__':
    unittest.main()
