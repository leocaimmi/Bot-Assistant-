#!/bin/sh
# Prepares the data directory, applies database migrations and starts the bot as an
# unprivileged user.
set -eu

if [ "$(id -u)" = "0" ]; then
    # Volumes (e.g. on Railway) are mounted owned by root: hand the data directory to
    # "app" and re-run this script without privileges.
    mkdir -p "$DATA_DIR"
    chown -R app:app "$DATA_DIR"
    exec setpriv --reuid=app --regid=app --init-groups --no-new-privs "$0" "$@"
fi

# Migrations run here and not in Railway's pre-deploy step: that step runs in a separate
# container where the volume (and so the SQLite file) is not mounted.
alembic upgrade head

exec "$@"
