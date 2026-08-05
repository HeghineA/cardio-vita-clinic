#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/app}"
DB_PATH="${CLINIC_DB:-$APP_DIR/data/clinic.sqlite}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/clinic-$STAMP.sqlite'"
find "$BACKUP_DIR" -name "clinic-*.sqlite" -type f -mtime +30 -delete

echo "Backup created: $BACKUP_DIR/clinic-$STAMP.sqlite"
