#!/bin/sh
set -eu
PORT="${PORT:-8080}"
case "$PORT" in
  ''|*[!0-9]*) echo "PORT must be numeric" >&2; exit 1 ;;
esac
export PORT
# Substitute only PORT: preserve nginx's request variables.
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
