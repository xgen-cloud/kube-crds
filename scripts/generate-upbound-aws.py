#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///

"""Generate kubeconform schemas for the namespaced Upbound AWS managed resources."""

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

REGISTRY = "xpkg.upbound.io"
REPO_PREFIX = "upbound"
OUT_DIRS = ["master-standalone", "master-standalone-strict"]
FILENAME_FORMAT = "{kind}-{group}-{version}"
ACCEPT = ",".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])

# The lockfile exists because kube-resources is private and CI cannot reach it.
PINS_REPO = "xgen-cloud/kube-resources"
PINS_PATH = "apps/base/crossplane-v2/providers/upbound-provider-family-aws.yaml"

# Per-service groups only; the base group's ProviderConfig collides on filename. See README.
GROUP_SUFFIX = ".aws.m.upbound.io"

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "scripts" / "upbound-aws.lock"


def read_lock():
    if not LOCKFILE.exists():
        sys.exit(f"ERROR: {LOCKFILE} is missing. Run with --sync to create it.")
    with LOCKFILE.open() as lock:
        return json.load(lock)["providers"]


def sync_versions():
    result = subprocess.run(
        ["gh", "api", f"repos/{PINS_REPO}/contents/{PINS_PATH}", "--jq", ".content"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: cannot read {PINS_REPO}; it is private, so gh must be authenticated:\n{result.stderr}")
    versions = {}
    for doc in yaml.safe_load_all(base64.b64decode(result.stdout)):
        if not doc or doc.get("kind") != "Provider":
            continue
        matched = re.match(r".*/provider-aws-([a-z0-9]+):(v[\d.]+)$", doc["spec"]["package"])
        if matched:
            versions[matched.group(1)] = matched.group(2)
    if not versions:
        sys.exit(f"ERROR: no provider-aws-* pins found in {PINS_REPO}/{PINS_PATH}")
    with LOCKFILE.open("w") as lock:
        json.dump(
            {"source": f"{PINS_REPO}/{PINS_PATH}", "providers": versions},
            lock,
            indent=2,
            sort_keys=True,
        )
        lock.write("\n")
    return versions


def registry_token(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": ACCEPT}))
        return None
    except urllib.error.HTTPError as err:
        if err.code != 401:
            raise
        challenge = err.headers.get("WWW-Authenticate", "")
    fields = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
    if "realm" not in fields:
        sys.exit(f"ERROR: {url}: unsupported auth challenge: {challenge!r}")
    query = urllib.parse.urlencode({k: fields[k] for k in ("service", "scope") if k in fields})
    with urllib.request.urlopen(f"{fields['realm']}?{query}") as response:
        return json.load(response)["token"]


def registry_get(url, token, accept=ACCEPT):
    headers = {"Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
        return response.read()


def find_or_exit(items, match, what, where):
    found = next((i for i in items if match(i)), None)
    if found is None:
        sys.exit(f"ERROR: {where}: no {what}")
    return found


def fetch_package(repo, version):
    api = f"https://{REGISTRY}/v2/{repo}"
    ref = f"{repo}:{version}"
    token = registry_token(f"{api}/manifests/{version}")
    index = json.loads(registry_get(f"{api}/manifests/{version}", token))
    if "manifests" not in index:
        sys.exit(f"ERROR: {ref}: expected a multi-arch image index")
    digest = find_or_exit(
        index["manifests"],
        lambda m: m.get("platform", {}).get("architecture") == "amd64",
        "amd64 manifest",
        ref,
    )["digest"]
    manifest = json.loads(registry_get(f"{api}/manifests/{digest}", token))
    layer = find_or_exit(
        manifest["layers"],
        lambda l: (l.get("annotations") or {}).get("io.crossplane.xpkg") == "base",
        "layer annotated io.crossplane.xpkg=base",
        ref,
    )["digest"]
    blob = registry_get(f"{api}/blobs/{layer}", token, accept="*/*")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        member = find_or_exit(tar.getmembers(), lambda m: m.isfile(), "file in the base layer", ref)
        return tar.extractfile(member).read()


def namespaced_crds(package_yaml):
    return [
        doc
        for doc in yaml.safe_load_all(package_yaml)
        if doc
        and doc.get("kind") == "CustomResourceDefinition"
        and doc["spec"]["group"].endswith(GROUP_SUFFIX)
    ]


def convert(source, out_dir):
    result = subprocess.run(
        # sys.executable, not python3: pyyaml lives in the uv venv this script runs under.
        [sys.executable, str(ROOT / "scripts" / "openapi2jsonschema.py"), source],
        cwd=out_dir,
        env=dict(os.environ, FILENAME_FORMAT=FILENAME_FORMAT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: openapi2jsonschema.py failed:\n{result.stderr}")
    return set(re.findall(r"written to (\S+\.json)", result.stdout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync",
        action="store_true",
        help=f"refresh the lockfile from {PINS_REPO} before generating",
    )
    args = parser.parse_args()

    versions = sync_versions() if args.sync else read_lock()

    crds = []
    for service in sorted(versions):
        version = versions[service]
        print(f"fetching provider-aws-{service}:{version}", file=sys.stderr)
        kept = namespaced_crds(fetch_package(f"{REPO_PREFIX}/provider-aws-{service}", version))
        print(f"  {len(kept)} namespaced CRDs", file=sys.stderr)
        crds.extend(kept)

    generated_name = re.compile(rf"-({'|'.join(sorted(versions))})-[^-]+\.json$")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml") as source:
        yaml.safe_dump_all(crds, source, default_flow_style=False)
        source.flush()
        for out in OUT_DIRS:
            written = convert(source.name, ROOT / out)

    # Two kinds colliding on one filename would show up here as a short count.
    expected = sum(
        1
        for c in crds
        for v in c["spec"]["versions"]
        if "openAPIV3Schema" in v.get("schema", {})
    )
    if len(written) != expected:
        sys.exit(f"ERROR: expected {expected} schemas, wrote {len(written)}")

    # Drop schemas a previous run wrote for kinds upstream has since removed.
    for out in OUT_DIRS:
        for schema in (ROOT / out).iterdir():
            if generated_name.search(schema.name) and schema.name not in written:
                schema.unlink()

    print(f"wrote {len(written)} schemas to each of {', '.join(OUT_DIRS)}", file=sys.stderr)


if __name__ == "__main__":
    main()
