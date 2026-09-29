#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-rgd.yaml>   (the kro CLI on PATH, or \$KRO pointing at one)" >&2
    exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# kro's own CRDs, out of its release manifest — nothing serves them yet, so there is no cluster to read.
curl -fsSL https://github.com/kubernetes-sigs/kro/releases/download/v0.9.4/kro-core-install-manifests.yaml \
    -o "$work/kro.yaml"

# The kind the RGD defines, which has no CRD until kro compiles the graph. kro's CLI omits TypeMeta, and
# the generator only reads documents typed as a CRD, so the two fields go on the first line of the JSON.
"${KRO:-kro}" generate crd -f "$1" -o json |
    sed '1s|^{|{"apiVersion":"apiextensions.k8s.io/v1","kind":"CustomResourceDefinition",|' \
    > "$work/instance.json"

./scripts/write-schemas.sh "$work/kro.yaml" "$work/instance.json"
