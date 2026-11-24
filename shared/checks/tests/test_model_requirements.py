"""Exercise the same staged files and Git hook used by model authors."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SKILL = Path(".agents/skills/model-user-requirements")
SOURCE = Path(__file__).resolve().parents[3]
SCRIPT = SKILL / "scripts/requirements.py"


class ModelRequirementsTest(unittest.TestCase):
    def run_cmd(self, *args, ok=True):
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True,
                                env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        shutil.copytree(SOURCE / SKILL, self.root / SKILL)
        self.run_cmd("git", "init", "-q")
        self.run_cmd("git", "config", "user.name", "Test")
        self.run_cmd("git", "config", "user.email", "test@example.invalid")
        self.run_cmd("git", "add", ".")
        self.run_cmd("git", "commit", "-qm", "baseline")
        self.run_cmd("sh", str(SKILL / "scripts/install-hook.sh"))
        self.path = self.root / "magic-wand/hardware/carbon-rod-holders-test/design.py"
        self.path.parent.mkdir(parents=True)

    def cli(self, *args, ok=True):
        return self.run_cmd("python3", str(SCRIPT), *args, ok=ok)

    def test_current_lookup_and_supersession(self):
        current = self.cli("show", "carbon-rod/base").stdout
        self.assertIn("proportionate-bases", current)
        self.assertNotIn("large-bases-all", current)
        self.assertIn("large-bases-all", self.cli("show", "carbon-rod/base", "--history").stdout)
        self.assertNotIn("proportionate-bases", self.cli("show", "printed-loop").stdout)
        self.assertNotEqual(self.cli("show", "unknown", ok=False).returncode, 0)

    def test_actual_hook_rejects_missing_stale_and_invalid_reviews(self):
        self.path.write_text("one")
        self.run_cmd("git", "add", ".")
        self.assertNotEqual(self.run_cmd("git", "commit", "-qm", "missing", ok=False).returncode, 0)
        self.assertNotEqual(self.cli("reconcile", "missing-record", ok=False).returncode, 0)
        self.assertNotEqual(self.cli("reconcile", "bottom-access", ok=False).returncode, 0)
        trailer = self.cli("reconcile", "guard-lower-blend").stdout.splitlines()[-1]
        self.path.write_text("two")
        self.run_cmd("git", "add", ".")
        self.assertNotEqual(self.run_cmd("git", "commit", "-qm", trailer, ok=False).returncode, 0)
        current = self.cli("reconcile", "no-new", "--base", "HEAD").stdout.splitlines()[-1]
        self.run_cmd("git", "commit", "-qm", "model update\n\n" + current)
        self.run_cmd("git", "rm", str(self.path.relative_to(self.root)))
        self.assertNotEqual(self.run_cmd("git", "commit", "-qm", "delete model", ok=False).returncode, 0)

    def test_record_change_invalidates_review_and_unrelated_commit_passes(self):
        (self.root / "readme.md").write_text("documentation")
        self.run_cmd("git", "add", ".")
        self.run_cmd("git", "commit", "-qm", "docs")
        self.path.touch()
        self.run_cmd("git", "add", ".")
        trailer = self.cli("reconcile", "no-new").stdout.splitlines()[-1]
        file = self.root / SKILL / "catalog/carbon-rod/base.json"
        records = json.loads(file.read_text())
        old = next(r for r in records if r["id"] == "proportionate-bases")
        old["status"] = "superseded"
        records.append({"id": "updated-base", "text": "Test correction", "status": "active",
                        "supersedes": [old["id"]]})
        file.write_text(json.dumps(records))
        self.run_cmd("git", "add", ".")
        self.assertNotEqual(self.run_cmd("git", "commit", "-qm", trailer, ok=False).returncode, 0)
        result = self.cli("reconcile", "updated-base").stdout
        self.assertNotIn(" / proportionate-bases", result)
        self.run_cmd("git", "commit", "-qm", result.splitlines()[-1])
        records[-1]["supersedes"] = ["nonexistent"]
        file.write_text(json.dumps(records))
        self.assertNotEqual(self.cli("validate", ok=False).returncode, 0)
        self.run_cmd("git", "add", ".")
        self.assertNotEqual(self.run_cmd("git", "commit", "-qm", "broken planning record", ok=False).returncode, 0)
