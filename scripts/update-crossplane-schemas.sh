#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

for family in aws gcp azure; do
    echo "Processing ${family} provider..."

    pins=$(gh api repos/xgen-cloud/kube-resources/contents/apps/base/crossplane-v2/providers/upbound-provider-family-$family.yaml \
        --jq '.content | @base64d' | grep -o 'provider-'$family'-[a-z0-9]*:v[0-9.]*')

    for pin in $pins; do
        service=${pin#provider-$family-}; service=${service%%:*}
        # extract version like v2.9.2
        version=${pin##*:}
        # github releases are generally only made for minor versions
        # transform v2.9.2 -> v2.9.0
        version="${version%.*}.0"
        # [ "$family" = gcp ]  && version="v3.1.0" # override pinned version to get near-future CRDs
        [ -d "$work/$version" ] || { mkdir -p "$work/$version" && curl -fsSL \
            "https://codeload.github.com/crossplane-contrib/provider-upjet-$family/tar.gz/refs/tags/$version" |
            tar -xz -C "$work/$version" --strip-components=1; }
        ./scripts/write-schemas.sh "$work/$version/package/crds/$service.$family.m.upbound.io_"*.yaml
    done
done
