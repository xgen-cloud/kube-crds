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

- **Layout**: `{group}/{kind}_{apiVersion}.json` with a **lowercase kind**
  (e.g. `gateway.networking.k8s.io/httproute_v1.json`,
  `monitoring.coreos.com/podmonitor_v1.json`). kubeconform lowercases
  `{{.ResourceKind}}` itself when expanding the consumer template
  (`strings.ToLower` in `pkg/registry/registry.go`, verified in v0.6.7 and
  v0.8.0) and raw.githubusercontent.com is case-sensitive — verified against
  the live datree catalog: `httproute_v1.json` → 200,
  `HTTPRoute_v1.json` → 404. Files match the template expansion
  byte-for-byte. (An earlier draft of this document stored original-case
  kinds; that design would 404 in Linux CI while passing locally on macOS's
  case-insensitive filesystem.)
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
- **`disagg/` folds into the catalog and the directory is deleted**: its
  schemas become `operator.victoriametrics.com/{kind}_{version}.json` in the
  one tree. Nothing in the three consumer repos references `disagg/`
  anymore (gosre dropped its reference in 693adbac), and keeping a second
  layout defeats the "one tree" goal. Residual risk — an unknown *public*
  consumer of `disagg/` paths — is accepted as small and called out in the
  PR body. (Builder's call, recorded here for review.)
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

Order: kube-ci's location is embedded in a fleet-gating Go service that
runs with `IgnoreMissingSchemas: false` — for kube-ci, the gap between
"kube-crds merge" and "kube-ci redeployed" is a fleet-wide **hard fail**
("could not find schema"), not a skip. **[OPEN — needs operator input:**
how kube-ci is rolled out/pinned to the gate, and whether that window is
acceptable; if not, the order inverts — the gosre PR carries both
locations (new templated first, old flat as fallback), deploys first, and
a cleanup PR drops the flat location after kube-crds merges]**.

For the `-ignore-missing-schemas` consumers (kube-resources CI,
recursive-flux-render.py), the same window is a *skip*, not a false pass;
their PRs land with or after the kube-crds merge.

The edge-workbench change is **consistency-only, not critical path**: its
schema cache is generated locally from vendored CRDs and never fetches
kube-crds, so nothing breaks if it lags. It aligns
`generate-schemas.py`, `validate.py` rung 2, and `validate_live.py` to the
new layout as a follow-up. (Builder's call.)

## Verification

- Every migrated schema file parses as JSON and self-describes (kind/group
  sanity-checked against its path).
- Self-check: run kubeconform with the new templated location against a
  fixture set exercising the migrated kinds — CRs validate; unknown fields
  (e.g. `timeouts` on HTTPRoute rules) validate against the regenerated
  schemas.
- The migration script lists anything unmoved; the PR carries the triage list.

**[OPEN — needs operator input:** the repo has no CI at all (no workflows in
git history), so "the gate is green" needs a decision on infrastructure:
GitHub Actions on self-hosted runners (kube-resources' pattern) vs
GitHub-hosted, the kubeconform pin, and whether wiring the check as a
required branch-protection check is in scope (needs repo admin). Until
decided, the self-check runs as a manual script with its output quoted in
the PR.**]**

## Left to the builder

- The exact full-group mapping entries for the legacy long tail (the script's
  table (c) above) — each is a mechanical lookup, flagged for human review.
- Whether `SOURCES.md` is one file or per-group annotations — one file unless
  the table exceeds ~40 lines.
