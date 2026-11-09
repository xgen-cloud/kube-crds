# Design: kube-crds versioned catalog redesign

Date: 2026-11-09
Status: draft for review
Supersedes: PR #57 (closed unmerged 2026-10-02 — flat `master-standalone{,-strict}` dump)

## Intent and why

kube-crds is the kubeconform schema registry for the fleet: kube-ci, the
kube-resources CI gate, `recursive-flux-render.py`, and the edge-workbench
validation ladder all resolve CRD schemas from this repo. Today the schemas
sit in two flat root directories, `master-standalone/` and
`master-standalone-strict/` (307 files each), named `{kind}-{group}-{version}.json`.

That layout was never chosen — it is what kubeconform's *defaults* produce
for a bare (non-templated) `-schema-location`: kubeconform's default
`-kubernetes-version` is literally `master`, so a bare location resolves to
`{location}/master-standalone{{.StrictSuffix}}/{kind}{KindSuffix}.json`. The
layout is a naming accident, which is why PR #57's "huge number of new files
in two root folders without a clear reason" was closed unmerged.

The layout is also **unversioned**: a schema file carries the CRD's apiVersion
in its name but nothing pins the *source* CRD release — a gateway-api bump
overwrites files in place, with no per-version artifacts. And the
strict/non-strict split doubles every file even though every consumer in the
fleet runs `-strict` (the converter bakes strictness into the schema as
`additionalProperties: false`; that strict schema is what made the stale
`HTTPRoute` schema reject the valid Gateway API v1 `timeouts` field and
block the voyage ingress route — kube-resources TODO(kube-crds#57)).

The redesign: rebuild the registry as a **versioned catalog in the
datree-CRDs-catalog layout**, served through kubeconform's documented
templated `-schema-location` mechanism.

## Goals

- One tree, laid out as `{group}/{Kind}_{apiVersion}.json` (e.g.
  `gateway.networking.k8s.io/HTTPRoute_v1.json`) — self-explaining,
  group-nested, one file per kind per apiVersion.
- Consumers resolve schemas with a templated `-schema-location`
  (`.../{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json`) —
  kubeconform's documented, first-class CRD mechanism.
- Provenance: a `SOURCES.md` mapping every group to its source CRDs and the
  generation path (vendored pin in kube-resources, update script, or manual).
- Unblocks the voyage HTTPRoute `timeouts` field (regenerating the Gateway
  API v1 schema from the pinned v1.6.1 CRDs includes `timeouts`; verified:
  the fresh schema validates the route).

## Non-goals

- Replacing kubeconform's `default` location for core Kubernetes kinds —
  consumers keep `-schema-location default` first.
- Serving non-CRD schemas differently than today.
- Multi-generation source pinning (serving two gateway-api releases
  simultaneously). kubeconform can template only on the manifest's
  **apiVersion**, not on the source CRD release; two releases of the same
  CRD serve the same apiVersion, so the catalog's latest conversion wins and
  git history is the version record for source bumps.

## Anti-goals

- Silent skips. `-ignore-missing-schemas` stays (the long tail of core kinds
  needs it), but a missing CRD schema must not look like a pass: consumers
  of the fleet gate on kube-ci, which hard-fails unknown kinds; the
  edge-workbench ladder treats SKIPPED as a defect.

## Approaches considered

1. **Keep the flat layout, regenerate in place** (what a fixed #57 would
   have been). Cheapest, but carries every complaint: unexplained root dirs,
   in-place overwrites with no versioning, strict/non-strict doubling.
   Rejected — it re-proposes the rejected PR.
2. **Versioned catalog, templated locations** (chosen). The layout kubeconform
   documents and the ecosystem standardized on: datreeio/CRDs-catalog
   (876★, 475 forks) is built exactly this way, and kube-ci already consumes
   that catalog layout as a supplement (gosre#24481, SRE-21966). Consumers
   change one line each.
3. **Per-source-release generations** (e.g. a `gateway-api-v1.6.1/` tree per
   source pin). Truly pinned, but nothing in a manifest tells kubeconform
   which generation to use — consumers would hardcode generation names, and
   the tree would fork per bump. Rejected as over-engineering for a registry
   whose consumers validate live manifests.

## Decided

- **Layout**: `{group}/{Kind}_{apiVersion}.json`, full group as the directory
  (e.g. `gateway.networking.k8s.io/HTTPRoute_v1.json`,
  `monitoring.coreos.com/PodMonitor_v1.json`). File names are the exact
  expansion of the consumer template `{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json`
  — we control the writer, so files match the template byte-for-byte (datree
  lowercases kinds for cosmetic reasons; we do not — no case-sensitivity risk).
- **Single tree, no strict split.** All fleet consumers run `-strict`; the
  converter's strictness is baked in. The old `master-standalone/` (non-strict)
  tree is not migrated.
- **Migration of the existing 307 strict schemas**: a one-time script moves
  each flat file to its group directory. The flat filename's group is only
  the first DNS label (`iam`, `storage`, `pkg`…), so the script maps to the
  full group from three sources, in order: (a) groups regenerated from known
  sources (see below) — authoritative; (b) the full groups of kinds appearing
  in `disagg/` (which already uses full-group filenames); (c) an explicit
  mapping table in the script for the remainder, reviewed by a human in the
  PR. Any file whose full group cannot be established is left in place and
  listed in the PR for triage rather than guessed.
- **Regeneration from known sources where they exist**: the vendored pins in
  kube-resources `crds/` (gateway-api v1.6.1, envoy-gateway v1.9.1,
  cert-manager, external-secrets, prometheus-operator) are reconverted with
  this repo's `scripts/openapi2jsonschema.py` into the new layout — this is
  what fixes the stale `HTTPRoute` schema. The update-*.sh scripts (XRD,
  kro, crossplane) are updated to write the new layout for future runs.
- **README rewritten**: the catalog layout, the consumer invocation, the
  generation commands, and `SOURCES.md` become the documented contract.
- **Compatibility**: the old flat directories are deleted in the same PR
  (consumers are in-repo-known and migrated in lockstep — see rollout).

## Rollout

Consumer touch points (each a one-line template change):

| Consumer | Location |
|---|---|
| kube-resources CI (`.github/workflows/test.yml`) | kube-resources |
| `recursive-flux-render.py` | kube-resources |
| kube-ci Go constant (`cmd/kube-ci/internal/kubeconform/kubeconform.go`) | gosre |
| edge-workbench `generate-schemas.py` + `validate.py` rung 2 | edge-workbench |

Order: kube-crds PR first (old layout deleted, new catalog + docs); each
consumer PR lands with or after it. Between kube-crds merge and a consumer's
switch, that consumer's CRD validation falls back to `default` only — with
`-ignore-missing-schemas` this is a *skip*, not a false pass, for fleet-gated
manifests (kube-ci hard-fails unknown kinds independently). The consumer PRs
are coordinated by SRE-22556 follow-ups; this PR is mergeable only when its
own gate (kubeconform self-check over the new catalog, below) is green.

## Verification

- Every migrated schema file parses as JSON and self-describes (kind/group
  sanity-checked against its path).
- Self-check: run kubeconform with the new templated location against a
  fixture set exercising the migrated kinds — CRs validate; unknown fields
  (e.g. `timeouts` on HTTPRoute rules) validate against the regenerated
  schemas.
- The migration script lists anything unmoved; the PR carries the triage list.

## Left to the builder

- The exact full-group mapping entries for the legacy long tail (the script's
  table (c) above) — each is a mechanical lookup, flagged for human review.
- Whether `SOURCES.md` is one file or per-group annotations — one file unless
  the table exceeds ~40 lines.
