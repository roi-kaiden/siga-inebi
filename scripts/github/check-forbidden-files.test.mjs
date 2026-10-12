import assert from "node:assert/strict";
import test from "node:test";

import { forbiddenFiles, isForbiddenFile } from "./check-forbidden-files.mjs";

test("backup, secrets and credentials source/docs remain reviewable", () => {
  const legitimate = [
    "scripts/backup/backup-db.sh",
    "scripts/backup/restore-files.sh",
    "backend/apps/backups.py",
    "backend/tests/test_credentials.py",
    "frontend/src/auth/secret-validation.js",
    "docs/manuals/09-backup-and-recovery-plan.md",
    "docs/credentials-configuration.md",
    "scripts/github/credential-check.ps1",
    ".secrets.baseline",
    ".env.example",
    "backend/.env.example",
    "frontend/src/app/main.jsx",
  ];
  assert.deepEqual(forbiddenFiles(legitimate), []);
});

test("nested private environments and database/key files are forbidden", () => {
  const artifacts = [
    ".env", ".env.secret", ".envsecret", "backend/.env.production",
    "nested/.envsecret", "nested/.env.example.local", "nested/.env/key.md",
    "backend/db.sqlite", "db.sqlite3", "nested/export.sql", "nested/export.SQL",
    "nested/export.dump", "nested/app.db", "cert.pem", "cert.key", "cert.p12",
    "cert.pfx", "cert.crt", "scripts/backup/source.sql", "docs/private.key",
    "nested/.secrets.baseline",
  ];
  for (const filename of artifacts) assert.equal(isForbiddenFile(filename), true, filename);
});

test("artifact directories cannot be bypassed with a code or docs suffix", () => {
  const artifacts = [
    "backups/export.md", "realbackups/file.anything", "backups/export.py",
    "nested/backups/copy.sh", "backup/export.md", "backup-data/source.js",
    "backups-data/source.sh", "nested/media/config.py", "uploads/notes.md",
    "media/uploads/photo.jpg", "nested/credentials/config.py", "secrets/guide.md",
    "dumps/notes.md", "docker-data/README.md", "scripts/backup/backups/source.py",
    "scripts/backup/data.dump", "credentials\\notes.md",
  ];
  for (const filename of artifacts) assert.equal(isForbiddenFile(filename), true, filename);
});

test("sensitive names without an explicit code/docs suffix stay forbidden", () => {
  const filenames = ["password-secret", "credential.json", "backup.zip", "dump.tar.gz",
    "nested/secret.txt", "nested/credentials.yaml", "nested/token-secret.csv"];
  assert.deepEqual(forbiddenFiles(filenames), filenames);
  assert.deepEqual(forbiddenFiles(["docs/backup.md", "backup.zip", "app.py"]), ["backup.zip"]);
});
