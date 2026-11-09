#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

for dir in master-standalone master-standalone-strict; do
    (cd "$dir" && FILENAME_FORMAT='{kind}-{group}-{version}' \
        uv run --with pyyaml ../scripts/openapi2jsonschema.py "$@" >/dev/null)
done

# The versioned catalog (going forward); the flat dirs are deprecated
# legacy, kept only while kube-ci still resolves them (see README).
FILENAME_FORMAT='{fullgroup}/{kind}_{version}' \
    uv run --with pyyaml scripts/openapi2jsonschema.py "$@" >/dev/null
