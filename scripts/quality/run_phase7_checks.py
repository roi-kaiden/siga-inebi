#!/usr/bin/env python3
"""Run Phase 7 automated gates in an isolated Compose project, retaining evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_EXCEPTIONS = (
    "PYSEC-2026-1845", "GHSA-6v7p-g79w-8964", "PYSEC-2026-1375",
    "PYSEC-2026-1374", "PYSEC-2026-2275", "PYSEC-2026-142", "PYSEC-2026-141",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Run:
    def __init__(self, root: Path, evidence: Path, run_id: str):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
            raise ValueError("RUN-ID debe tener 1–80 letras, numeros, guiones o guiones bajos")
        self.root = root.resolve()
        self.directory = evidence.resolve() / run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        for child in ("logs", "backend", "frontend", "frontend/dist"):
            (self.directory / child).mkdir(exist_ok=True)
        project = "siga_phase7_" + hashlib.sha256(str(self.directory).encode()).hexdigest()[:16]
        override = self.directory / "compose.evidence.json"
        override.write_text(json.dumps({"services": {
            "backend-test": {"volumes": [f"{self.directory}:/evidence"],
                             "user": f"{os.getuid()}:{os.getgid()}",
                             "environment": {"RUFF_CACHE_DIR": "/tmp/ruff",
                                             "COVERAGE_FILE": "/evidence/backend/.coverage"},
                             "tmpfs": [f"/app/media:uid={os.getuid()},gid={os.getgid()},mode=0700"]},
            "frontend": {"volumes": [f"{self.directory}:/evidence",
                                      f"{self.directory}/frontend/dist:/app/dist"],
                         "user": f"{os.getuid()}:{os.getgid()}", "entrypoint": [],
                         "environment": {"npm_config_cache": "/tmp/npm"},
                         "tmpfs": ["/app/node_modules/.vite-temp:mode=1777",
                                   "/app/node_modules/.vite:mode=1777"]},
        }}, indent=2) + "\n")
        self.compose = ["docker", "compose", "--env-file", "/dev/null", "-p", project,
                        "-f", str(self.root / "compose.yml"),
                        "-f", str(self.root / "compose.test.yml"), "-f", str(override)]
        self.report = {"run_id": run_id, "started_at_utc": now(), "project": project,
                       "candidate_sha": None, "working_tree_dirty": None,
                       "source_digest_sha256": None,
                       "status": "En curso", "checks": []}
        self.save()

    def save(self):
        (self.directory / "summary.json").write_text(
            json.dumps(self.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def check(self, name, command, *, ready=True, artifacts=()):
        result = {"name": name, "command": command, "started_at_utc": now(),
                  "exit_code": None, "status": "Bloqueado", "log": f"logs/{name}.log"}
        interrupted = False
        log_path = self.directory / result["log"]
        with log_path.open("w", encoding="utf-8") as log:
            if not ready:
                log.write("Bloqueado: preparacion requerida no aprobada.\n")
            else:
                print(f"[{name}]", flush=True)
                try:
                    process = subprocess.run(command, cwd=self.root, stdout=log,
                                             stderr=subprocess.STDOUT, check=False)
                    result["exit_code"] = process.returncode
                    result["status"] = "Aprobado" if process.returncode == 0 else "Fallido"
                except OSError as error:
                    log.write(f"No se pudo iniciar el comando: {error}\n")
                except KeyboardInterrupt:
                    interrupted = True
                    result["status"] = "Interrumpido"
                    log.write("Control interrumpido por el operador.\n")
                result["required_artifacts"] = list(artifacts)
                missing = [path for path in artifacts if not (self.directory / path).is_file()]
                result["missing_artifacts"] = missing
                if missing and result["status"] == "Aprobado":
                    result["status"] = "Fallido"
                    log.write(f"Evidencia requerida ausente: {', '.join(missing)}\n")
        result["finished_at_utc"] = now()
        self.report["checks"].append(result)
        self.save()
        if interrupted:
            raise KeyboardInterrupt
        return result["status"] == "Aprobado"

    def container(self, service, *args):
        return [*self.compose, "run", "--rm", "--no-deps", "-T", service, *args]

    def identify_source(self, suffix=""):
        snapshot = {"candidate_sha": None, "working_tree_dirty": None,
                    "source_digest_sha256": None}
        self.check("git-sha" + suffix, ["git", "rev-parse", "HEAD"])
        if self.report["checks"][-1]["exit_code"] == 0:
            snapshot["candidate_sha"] = (self.directory / f"logs/git-sha{suffix}.log").read_text().strip()
        self.check("git-status" + suffix, ["git", "status", "--porcelain"])
        if self.report["checks"][-1]["exit_code"] == 0:
            snapshot["working_tree_dirty"] = bool(
                (self.directory / f"logs/git-status{suffix}.log").read_text().strip()
            )
        if self.check("source-files" + suffix, ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]):
            digest = hashlib.sha256()
            paths = (self.directory / f"logs/source-files{suffix}.log").read_bytes().split(b"\0")
            for name in sorted(set(paths) - {b""}):
                path = self.root / os.fsdecode(name)
                digest.update(name + b"\0")
                if path.is_symlink():
                    digest.update(b"symlink\0" + os.fsencode(os.readlink(path)))
                elif path.is_file():
                    digest.update(str(path.stat().st_mode & 0o777).encode() + b"\0")
                    digest.update(hashlib.sha256(path.read_bytes()).digest())
                else:
                    digest.update(b"deleted\0")
            snapshot["source_digest_sha256"] = digest.hexdigest()
        if suffix:
            self.report["source_after_run"] = snapshot
        else:
            self.report.update(snapshot)
        self.save()
        return snapshot

    def execute(self) -> int:
        source_before = self.identify_source()
        docker = self.check("docker", ["docker", "version", "--format", "{{.Server.Version}}"])
        compose = self.check("compose", ["docker", "compose", "version"], ready=docker)
        cleanup = compose
        try:
            backend = self.check("build-backend", [*self.compose, "build", "backend-test"], ready=compose)
            frontend = self.check("build-frontend", [*self.compose, "build", "frontend"], ready=compose)
            database = self.check("database-start", [*self.compose, "up", "-d", "--wait", "db-test"], ready=compose)
            self.check("postgres-version", [*self.compose, "exec", "-T", "db-test", "postgres", "--version"], ready=database)
            self.check("python-version", self.container("backend-test", "python", "--version"), ready=backend)
            self.check("node-version", self.container("frontend", "node", "--version"), ready=frontend)
            migrated = self.check("migrations-apply", self.container("backend-test", "python", "manage.py", "migrate", "--noinput"), ready=backend and database)
            self.check("backend-tests", self.container("backend-test", "pytest", "-o", "cache_dir=/tmp/pytest-cache", "-o", "addopts=--strict-markers --cov=apps --cov=config/api --cov-report=term-missing --cov-fail-under=70", "--junitxml=/evidence/backend/junit.xml", "--cov-report=xml:/evidence/backend/coverage.xml"), ready=migrated, artifacts=("backend/junit.xml", "backend/coverage.xml"))
            for name, args in (
                ("backend-lint", ["ruff", "check", "."]),
                ("backend-format", ["ruff", "format", "--check", "."]),
                ("backend-bandit", ["bandit", "-q", "-r", "apps", "config"]),
                ("backend-audit", ["pip-audit", "--cache-dir", "/tmp/pip-audit", "-r", "requirements/dev.txt", *[arg for vulnerability in AUDIT_EXCEPTIONS for arg in ("--ignore-vuln", vulnerability)]]),
            ):
                self.check(name, self.container("backend-test", *args), ready=backend)
            for name, args in (
                ("django-check", ["check"]),
                ("migrations-check", ["makemigrations", "--check", "--dry-run"]),
            ):
                self.check(name, self.container("backend-test", "python", "manage.py", *args), ready=backend and database)
            self.check("frontend-tests", self.container("frontend", "npm", "run", "test:coverage", "--", "--maxWorkers=2", "--reporter=default", "--reporter=junit", "--outputFile=/evidence/frontend/junit.xml", "--coverage.reportsDirectory=/evidence/frontend/coverage"), ready=frontend, artifacts=("frontend/junit.xml", "frontend/coverage/coverage-final.json"))
            for name, script in (("frontend-lint", "lint"), ("frontend-format", "format:check")):
                self.check(name, self.container("frontend", "npm", "run", script), ready=frontend)
            self.check("frontend-build", self.container("frontend", "npm", "run", "build"), ready=frontend, artifacts=("frontend/dist/index.html", "frontend/dist/.vite/manifest.json"))
            self.check("frontend-audit", self.container("frontend", "npm", "audit", "--audit-level=high"), ready=frontend)
        except KeyboardInterrupt:
            self.report["interrupted"] = True
        finally:
            # Reports are bind-mounted and saved after each gate, before any cleanup.
            self.check("cleanup", [*self.compose, "down", "-v", "--remove-orphans"], ready=cleanup)
            source_after = self.identify_source("-end")
            self.report["source_stable"] = source_before == source_after and all(
                value is not None for value in source_after.values()
            )
            success = (self.report["source_stable"] and not self.report.get("interrupted") and
                       all(check["status"] == "Aprobado" for check in self.report["checks"]))
            self.report["status"] = "Aprobado" if success else "No aprobado"
            self.report["finished_at_utc"] = now()
            self.save()
        print(f"Evidencia: {self.directory}")
        return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, default=ROOT / "tmp/phase7")
    args = parser.parse_args()
    try:
        run = Run(ROOT, args.evidence_root, args.run_id)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return run.execute()


if __name__ == "__main__":
    raise SystemExit(main())
