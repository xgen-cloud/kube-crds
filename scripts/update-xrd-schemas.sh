#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-repo-or-directory>" >&2
    exit 1
fi

target=$(cd "$1" && pwd)

xrds=()
while IFS= read -r f; do xrds+=("$f"); done < <(grep -rl --include='*.yaml' --include='*.yml' \
    '^kind: CompositeResourceDefinition$' "$target" 2>/dev/null)

if [ ${#xrds[@]} -eq 0 ]; then
    echo "No CompositeResourceDefinition manifests found under $target" >&2
    exit 1
fi

./scripts/write-schemas.sh "${xrds[@]}"
