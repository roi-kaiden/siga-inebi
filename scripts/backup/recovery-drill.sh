#!/usr/bin/env sh
# Simulacro de recuperacion: mide el RTO real (RNF-RES-002).
#
# El requerimiento pide que el tiempo objetivo de recuperacion este "declarado y
# probado antes de la entrega". Declararlo es escribir un numero; probarlo es
# esto: restaurar de verdad en una base desechable, cronometrar, y comparar
# contra el objetivo.
#
# Se restaura SOBRE UNA BASE APARTE ($DRILL_DATABASE_NAME), nunca sobre la de
# produccion. Si esa variable no esta puesta, el script se niega a correr: un
# simulacro que borra la base real no es un simulacro.
#
# Uso:
#   DRILL_DATABASE_NAME=siga_inebi_drill DATABASE_USER=siga_inebi \
#   DATABASE_HOST=localhost PGPASSWORD=... \
#   sh scripts/backup/recovery-drill.sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command pg_restore
require_command psql
require_command tar
require_command python3

drill_db="${DRILL_DATABASE_NAME:-}"
[ -n "$drill_db" ] ||
  die "defina DRILL_DATABASE_NAME con una base desechable; nunca se restaura sobre la de produccion"
case "$drill_db" in
  [0-9]*|*[!a-zA-Z0-9_]*|[!a-zA-Z_]*) die "DRILL_DATABASE_NAME debe ser un identificador ASCII sencillo" ;;
esac
case "$drill_db" in
  *_drill) ;;
  *) die "DRILL_DATABASE_NAME debe terminar en _drill" ;;
esac
[ "${#drill_db}" -le 63 ] || die "DRILL_DATABASE_NAME excede 63 caracteres"
[ "$drill_db" != "${DATABASE_NAME:-siga_inebi}" ] || die "la base desechable coincide con la base de origen"

db_user="${DATABASE_USER:-siga_inebi}"
db_host="${DATABASE_HOST:-localhost}"
db_port="${DATABASE_PORT:-5432}"
rto_hours="${RECOVERY_TIME_OBJECTIVE_HOURS:-4}"
case "$rto_hours" in
  ''|*[!0-9]*) die "RECOVERY_TIME_OBJECTIVE_HOURS debe ser un entero positivo" ;;
esac
[ "$rto_hours" -gt 0 ] || die "RECOVERY_TIME_OBJECTIVE_HOURS debe ser positivo"

db_artifact=$(latest_artifact "$DATABASE_BACKUP_DIR" .dump)
[ -n "$db_artifact" ] || die "no hay respaldo de base de datos que restaurar"
files_artifact=$(latest_artifact "$FILES_BACKUP_DIR" .tar.gz)
[ -n "$files_artifact" ] || die "no hay respaldo de archivos que restaurar"

drill_media="${DRILL_MEDIA_ROOT:-$(mktemp -d)}"
db_manifest="${db_artifact%.dump}.manifest.json"
files_manifest="${files_artifact%.tar.gz}.manifest.json"

# Validar las dos pilas y todos los destinos antes de destruir la base desechable.
# JSON real y rutas canonicas evitan aceptar manifiestos incompletos o aliases
# del almacenamiento de origen (incluidos enlaces simbolicos).
dump_version=$(python3 - "$db_artifact" "$db_manifest" "$files_artifact" "$files_manifest" \
  "$drill_db" "$drill_media" "${MEDIA_ROOT:-backend/media}" <<'PY'
import json
import re
import sys
from pathlib import Path

try:
    db_artifact, db_manifest, files_artifact, files_manifest, drill_db, target, source = sys.argv[1:]
    manifests = []
    for artifact, manifest, kind in (
        (db_artifact, db_manifest, "database"),
        (files_artifact, files_manifest, "files"),
    ):
        data = json.loads(Path(manifest).read_text())
        if (
            data["kind"] != kind
            or data["artifact"] != Path(artifact).name
            or not re.fullmatch(r"[a-f0-9]{64}", data["sha256"])
        ):
            raise ValueError("contenido de manifiesto invalido")
        manifests.append(data)
    database, files = manifests
    if not isinstance(database["database_name"], str) or not database["database_name"]:
        raise ValueError("manifiesto sin base de origen")
    if database["database_name"] == drill_db:
        raise ValueError("la base desechable coincide con la base del manifiesto")
    # Los clientes Debian incluyen su revision de paquete en --version.
    if not isinstance(database["pg_dump_version"], str) or not re.match(r"[0-9]+", database["pg_dump_version"]):
        raise ValueError("version de pg_dump invalida")
    destination = Path(target).resolve()
    if not isinstance(files["source_path"], str) or not files["source_path"]:
        raise ValueError("manifiesto sin almacenamiento de origen")
    for origin in (Path(source).resolve(), Path(files["source_path"]).resolve()):
        if destination == origin or destination in origin.parents or origin in destination.parents:
            raise ValueError("DRILL_MEDIA_ROOT se superpone al almacenamiento de origen")
    print(database["pg_dump_version"])
except (OSError, ValueError, KeyError, TypeError) as error:
    print(f"error: prevalidacion del simulacro: {error}", file=sys.stderr)
    sys.exit(1)
PY
)
verify_artifact "$db_artifact" "$db_manifest"
verify_artifact "$files_artifact" "$files_manifest"
restore_version=$(pg_restore --version | awk '{print $NF}')
server_version=$(server_major_version "$db_host" "$db_port" "$db_user" postgres)
[ -n "$(major_version "$server_version")" ] || die "no se pudo verificar la version del servidor"
require_matching_pg_version "$restore_version" "$server_version" "simulacro de recuperacion"
require_matching_pg_version "$dump_version" "$server_version" "respaldo del simulacro"
mkdir -p "$drill_media"

started=$(date -u +%s)

echo "== 1/2 base de datos =="
psql --host="$db_host" --port="$db_port" --username="$db_user" --dbname=postgres \
  -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$drill_db\";"
psql --host="$db_host" --port="$db_port" --username="$db_user" --dbname=postgres \
  -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$drill_db\";"
DATABASE_NAME="$drill_db" sh "$script_dir/restore-database.sh" "$db_artifact"

echo "== 2/2 archivos =="
MEDIA_ROOT="$drill_media" sh "$script_dir/restore-files.sh" "$files_artifact"

finished=$(date -u +%s)
elapsed=$((finished - started))
budget=$((rto_hours * 3600))

cat <<REPORT

Simulacro de recuperacion
- base restaurada en: $drill_db
- archivos restaurados en: $drill_media
- duracion: ${elapsed}s
- RTO declarado: ${rto_hours}h (${budget}s)
REPORT

if [ "$elapsed" -gt "$budget" ]; then
  die "el simulacro tardo ${elapsed}s y excede el RTO declarado de ${budget}s"
fi

echo "resultado: dentro del RTO declarado"
