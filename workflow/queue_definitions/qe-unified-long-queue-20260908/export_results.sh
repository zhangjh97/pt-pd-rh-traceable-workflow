#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="${1:-$(cat "$ROOT/LATEST_RUN.txt")}" 
NAME="$(basename "$RUN")"
ARCHIVE="/mnt/d/qe-unified-validation-results-${NAME}.tar.gz"

tar --exclude='./*/scratch' -czf "$ARCHIVE" -C "$RUN" .
ls -lh "$ARCHIVE"
sha256sum "$ARCHIVE"
