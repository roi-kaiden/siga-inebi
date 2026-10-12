"""Evidence survival, isolation and gate semantics without Docker or network."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "phase7_runner", Path(__file__).resolve().parents[1] / "run_phase7_checks.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = runner.Run(self.root, self.root / "evidence", "RUN-D1-06")
        self.commands = []

    def simulate(self, command, *, cwd, stdout, stderr, check):
        self.commands.append(command)
        name = Path(stdout.name).stem.removesuffix("-end")
        if name == "git-sha":
            stdout.write("abc123\n")
        elif name == "git-status":
            stdout.write("?? candidate.py\n")
        elif name == "source-files":
            stdout.write("candidate.py\0")
        outputs = {
            "backend-tests": ("backend/junit.xml", "backend/coverage.xml"),
            "frontend-tests": ("frontend/junit.xml", "frontend/coverage/coverage-final.json"),
            "frontend-build": ("frontend/dist/index.html", "frontend/dist/.vite/manifest.json"),
        }
        for output in outputs.get(name, ()):
            target = self.run.directory / output
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("evidence\n")
        if name == "cleanup":
            # Evidence must have been persisted while containers still exist.
            summary = json.loads((self.run.directory / "summary.json").read_text())
            self.assertTrue(any(item["name"] == "frontend-tests" for item in summary["checks"]))
        return subprocess.CompletedProcess(command, 0)

    def test_success_has_reports_dirty_identity_and_isolated_commands(self):
        (self.root / "candidate.py").write_text("print('synthetic')\n")
        with patch.object(runner.subprocess, "run", side_effect=self.simulate):
            self.assertEqual(self.run.execute(), 0)
        self.assertTrue(self.run.report["working_tree_dirty"])
        self.assertEqual(len(self.run.report["source_digest_sha256"]), 64)
        self.assertEqual(self.run.report["candidate_sha"], "abc123")
        for command in self.commands:
            if "run" in command:
                self.assertIn("--no-deps", command)
            if command[:2] == ["docker", "compose"] and command[2] != "version":
                self.assertIn(self.run.report["project"], command)
        other = runner.Run(self.root, self.root / "evidence", "RUN-D1-07")
        self.assertNotEqual(other.report["project"], self.run.report["project"])

    def test_failed_backend_preserves_reports_and_continues_frontend(self):
        def fail_tests(command, **kwargs):
            result = self.simulate(command, **kwargs)
            if Path(kwargs["stdout"].name).stem == "backend-tests":
                kwargs["stdout"].write("AssertionError: synthetic failure\n")
                result.returncode = 1
            return result

        with patch.object(runner.subprocess, "run", side_effect=fail_tests):
            self.assertEqual(self.run.execute(), 1)
        checks = {item["name"]: item for item in self.run.report["checks"]}
        self.assertEqual(checks["backend-tests"]["status"], "Fallido")
        self.assertEqual(checks["frontend-tests"]["status"], "Aprobado")
        self.assertEqual(checks["cleanup"]["status"], "Aprobado")
        self.assertTrue((self.run.directory / "backend/junit.xml").is_file())
        self.assertIn("AssertionError", (self.run.directory / checks["backend-tests"]["log"]).read_text())

    def test_preparation_failure_blocks_only_dependents(self):
        def fail_build(command, **kwargs):
            result = self.simulate(command, **kwargs)
            if Path(kwargs["stdout"].name).stem == "build-backend":
                result.returncode = 2
            return result

        with patch.object(runner.subprocess, "run", side_effect=fail_build):
            self.assertEqual(self.run.execute(), 1)
        checks = {item["name"]: item for item in self.run.report["checks"]}
        self.assertEqual(checks["backend-tests"]["status"], "Bloqueado")
        self.assertIsNone(checks["backend-tests"]["exit_code"])
        self.assertEqual(checks["frontend-tests"]["status"], "Aprobado")

    def test_missing_artifact_fails_even_if_process_succeeds(self):
        with patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            self.assertFalse(self.run.check("tests", ["test"], artifacts=("backend/junit.xml",)))
        self.assertEqual(self.run.report["checks"][-1]["exit_code"], 0)
        self.assertEqual(self.run.report["checks"][-1]["missing_artifacts"], ["backend/junit.xml"])

    def test_missing_docker_returns_nonzero_without_running_containers(self):
        def missing_docker(command, **kwargs):
            if command[0] == "docker":
                raise FileNotFoundError("docker unavailable")
            return self.simulate(command, **kwargs)

        with patch.object(runner.subprocess, "run", side_effect=missing_docker):
            self.assertEqual(self.run.execute(), 1)
        self.assertEqual(self.run.report["status"], "No aprobado")
        self.assertFalse(any("run" in command for command in self.commands))

    def test_duplicate_and_invalid_ids_do_not_replace_evidence(self):
        original = (self.run.directory / "summary.json").read_text()
        with self.assertRaises(FileExistsError):
            runner.Run(self.root, self.root / "evidence", "RUN-D1-06")
        with self.assertRaises(ValueError):
            runner.Run(self.root, self.root / "evidence", "../escape")
        self.assertEqual((self.run.directory / "summary.json").read_text(), original)

    def test_source_digest_changes_when_untracked_source_changes(self):
        candidate = self.root / "candidate.py"
        candidate.write_text("first\n")
        with patch.object(runner.subprocess, "run", side_effect=self.simulate):
            self.run.identify_source()
            first = self.run.report["source_digest_sha256"]
            candidate.write_text("second\n")
            self.run.identify_source()
        self.assertNotEqual(first, self.run.report["source_digest_sha256"])

    def test_interrupted_gate_records_evidence_and_cleans_up(self):
        def interrupt_tests(command, **kwargs):
            if Path(kwargs["stdout"].name).stem == "backend-tests":
                raise KeyboardInterrupt
            if Path(kwargs["stdout"].name).stem == "cleanup":
                return subprocess.CompletedProcess(command, 0)
            return self.simulate(command, **kwargs)

        with patch.object(runner.subprocess, "run", side_effect=interrupt_tests):
            self.assertEqual(self.run.execute(), 1)
        checks = {item["name"]: item for item in self.run.report["checks"]}
        self.assertEqual(checks["backend-tests"]["status"], "Interrumpido")
        self.assertEqual(checks["cleanup"]["status"], "Aprobado")
        self.assertTrue(self.run.report["interrupted"])

    def test_changed_source_invalidates_otherwise_successful_run(self):
        source = self.root / "candidate.py"
        source.write_text("before\n")

        def modify_source(command, **kwargs):
            result = self.simulate(command, **kwargs)
            if Path(kwargs["stdout"].name).stem == "frontend-build":
                source.write_text("after\n")
            return result

        with patch.object(runner.subprocess, "run", side_effect=modify_source):
            self.assertEqual(self.run.execute(), 1)
        self.assertFalse(self.run.report["source_stable"])
        self.assertNotEqual(self.run.report["source_digest_sha256"],
                            self.run.report["source_after_run"]["source_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
