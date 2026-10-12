// Path policy for PR validation. Content scanning remains a separate control.
const sensitiveName = /(secret|credential|backup|dump)/i;
const sourceOrDocumentation = /\.(py|js|jsx|ts|tsx|mjs|cjs|sh|bash|ps1|md|rst|adoc)$/i;
const sensitiveExtension = /\.(sqlite|sqlite3|db|sql|dump|pem|key|p12|pfx|crt)$/i;
const artifactDirectory = /^(?:media|uploads|credentials|secrets|dumps|docker-data|backup|.*backups.*|.*backup[-_]data.*)$/i;

export function isForbiddenFile(filename) {
  if (filename === ".secrets.baseline") return false;

  const parts = filename.replaceAll("\\", "/").split("/");
  const basename = parts.at(-1);
  // These checks take precedence: a source suffix cannot disguise an artifact.
  if (parts.some((part) => /^\.env/i.test(part) && part !== ".env.example")) return true;
  if (sensitiveExtension.test(basename)) return true;
  if (parts.slice(0, -1).some((part, index) => {
    const backupScripts = index === 1 && parts[0] === "scripts" && part === "backup";
    return !backupScripts && artifactDirectory.test(part);
  })) return true;

  return sensitiveName.test(filename) && !sourceOrDocumentation.test(basename);
}

export function forbiddenFiles(filenames) {
  return filenames.filter(isForbiddenFile);
}
