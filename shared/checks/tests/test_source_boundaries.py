"""Check that dependency folders stay out of source validation, without touching hardware."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest

REPOSITORY = Path(__file__).resolve().parents[3]

def load(relative):
    spec = importlib.util.spec_from_file_location(relative.replace('/', '_'), REPOSITORY / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class SourceBoundaryTests(unittest.TestCase):
    def test_privacy_excludes_only_root_local_ledgers(self):
        scanner = load('shared/checks/privacy.py')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scanner.ROOT = root
            private_value = str(PurePosixPath("/", "Users", "fixture-user", "private.txt"))
            local = root / '.outstanding-items' / 'task'
            local.mkdir(parents=True)
            (local / 'outstanding-items.json').write_text(private_value)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(scanner.main(), 0)
                nested = root / 'component' / '.outstanding-items'
                nested.mkdir(parents=True)
                (nested / 'source.txt').write_text(private_value)
                self.assertEqual(scanner.main(), 1)

    def test_privacy_ignores_dependencies_but_checks_sibling_components(self):
        scanner = load('shared/checks/privacy.py')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scanner.ROOT = root
            private_value = str(PurePosixPath("/", "Users", "fixture-user", "private.txt"))
            for name in ['.venv', 'venv', 'node_modules', 'build.noindex']:
                folder = root / 'component' / name
                folder.mkdir(parents=True)
                (folder / 'metadata.txt').write_text(private_value)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(scanner.main(), 0)
                (root / 'component' / 'source.py').write_text(private_value)
                self.assertEqual(scanner.main(), 1)

    def test_stones_checks_only_owned_python_source(self):
        checker = load('control-stones/scripts/check.py')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for folder in ['debug', 'scripts', '.venv', 'firmware/imu_debug', 'docs']:
                (root / folder).mkdir(parents=True)
            (root / 'profile.json').write_text(json.dumps({'id': 'control-stones'}))
            (root / 'firmware/imu_debug/imu_debug.ino').touch()
            (root / 'docs/wiring.html').touch()
            for folder in ['.venv', 'debug/.venv', 'scripts/venv']:
                (root / folder).mkdir(parents=True, exist_ok=True)
                (root / folder / 'broken.py').write_text('not valid python !!!')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(checker.main(root), 0)
            (root / 'debug/broken.py').write_text('not valid python !!!')
            with self.assertRaises(SyntaxError):
                checker.main(root)

if __name__ == '__main__':
    unittest.main()
