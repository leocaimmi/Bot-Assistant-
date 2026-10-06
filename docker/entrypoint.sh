#!/bin/sh
# Prepares the data directory, applies database migrations and starts the bot as an
# unprivileged user.
set -eu

# A relative SQLite path (e.g. copied from a local .env) points inside the image, where the
# bot cannot write and nothing survives a deploy: stop with a hint instead of a traceback.
case "${DATABASE_URL:-}" in
    sqlite*:///[!/:]*)
        echo "DATABASE_URL points to a relative SQLite path. Remove it in Docker and Railway:" \
            "the image already keeps the database in $DATA_DIR (mount the volume there)." >&2
        exit 1
        ;;
esac

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
