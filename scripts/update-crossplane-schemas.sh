#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

pins=$(gh api repos/xgen-cloud/kube-resources/contents/apps/base/crossplane-v2/providers/upbound-provider-family-aws.yaml \
    --jq '.content | @base64d' | grep -o 'provider-aws-[a-z0-9]*:v[0-9.]*')

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

for pin in $pins; do
    service=${pin#provider-aws-}; service=${service%%:*}
    version=${pin##*:}
    [ -d "$work/$version" ] || { mkdir -p "$work/$version" && curl -fsSL \
        "https://codeload.github.com/crossplane-contrib/provider-upjet-aws/tar.gz/refs/tags/$version" |
        tar -xz -C "$work/$version" --strip-components=1; }
    for dir in master-standalone master-standalone-strict; do
        (cd "$dir" && FILENAME_FORMAT='{kind}-{group}-{version}' \
            uv run --with pyyaml ../scripts/openapi2jsonschema.py \
            "$work/$version/package/crds/$service.aws.m.upbound.io_"*.yaml >/dev/null)
    done
done
