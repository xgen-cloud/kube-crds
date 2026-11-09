# kube-crds Versioned Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the versioned `{group}/{kind}_{apiVersion}.json` catalog alongside the flat layout, fixing the stale HTTPRoute schema in place in the same PR — the normal maintainer flow: regenerate, move, document, PR.

**Architecture:** All work in the kube-crds worktree on branch `update-crds`. One small converter patch lets the documented regeneration write group-nested output directly. The five vendored CRD pins are regenerated into the catalog; the remaining legacy strict schemas are `git mv`-ed into group dirs (mapping shown in the PR); `disagg/` folds in; README + SOURCES.md document it. No migration framework, no bespoke gate script — verification is kubeconform against fixtures, output quoted in the PR.

**Tech Stack:** bash, python3 (uv-run pyyaml), kubeconform v0.8.0, kube-crds' vendored `scripts/openapi2jsonschema.py`.

**Spec:** `docs/2026-11-09-catalog-redesign-design.md` (same repo, same branch)

## Global Constraints

- Catalog layout: `{fullgroup}/{kind}_{apiVersion}.json`, kind **lowercase** (kubeconform lowercases `{{.ResourceKind}}` in templates; raw.githubusercontent is case-sensitive).
- Flat `master-standalone*/` dirs are NOT deleted; only gateway-api + envoy-gateway files are regenerated in place (the timeouts fix).
- No consumer repos touched in this PR. No CI infra added.
- Keep the converter's required-with-defaults and preserve-unknown-fields transforms as-is.
- Commits: session-marked identity, subject + body.

## Review Focus

1. **Case**: an uppercase-kind filename passes on macOS but 404s in CI — every catalog filename must be lowercase-kind (checked by the kubeconform fixture run, which 404s on a mismatch).
2. **Wrong full-group guess**: a `git mv` to the wrong group dir silently misroutes a kind — each move's mapping is shown in the PR for review; anything uncertain stays put.
3. **required-with-defaults**: a regenerated schema must still accept an omitted defaulted field — covered by a fixture.
4. **disagg split**: `vlagent-operator.victoriametrics.com-v1.json` = kind `vlagent`, group `operator.victoriametrics.com` — covered by a fixture.

---

### Task 1: Converter writes group-nested output

**Files:**
- Modify: `scripts/openapi2jsonschema.py`

**Interfaces:**
- Produces: `FILENAME_FORMAT='{fullgroup}/{kind}_{version}'` writes `gateway.networking.k8s.io/httproute_v1.json` (mkdir the group dir); all existing flat formats unchanged.

- [ ] **Step 1:** Reproduce: run the converter on kube-resources' gateway-api v1.6.1 source with `FILENAME_FORMAT='{fullgroup}/{kind}_{version}'` in a scratch dir — expect flat output or a missing-dir crash (no group subdirs).
- [ ] **Step 2:** Patch: stop basename-stripping the formatted filename; `os.makedirs(dirname, exist_ok=True)` before write. Leave `.lower()` and all transforms untouched.
- [ ] **Step 3:** Verify: scratch run produces group dirs with lowercase `_{version}` files; then `FILENAME_FORMAT='{kind}-{group}-{version}'` still produces the exact flat names the repo has today.
- [ ] **Step 4:** Commit: "converter: support group-nested FILENAME_FORMAT".

### Task 2: Fix the stale flat schemas (timeouts unblock)

**Files:**
- Modify: `master-standalone/`, `master-standalone-strict/` (gateway-api + envoy-gateway families only)

**Interfaces:**
- Consumes: converter (existing flat format).
- Produces: flat strict schema accepting `HTTPRouteRule.timeouts`.

- [ ] **Step 1:** Failing check — kubeconform against the live `master` catalog URL with a fixture HTTPRoute carrying `rules[0].timeouts.request: 370s`; expect "additional properties 'timeouts' not allowed".
- [ ] **Step 2:** Regenerate per the README process (run converter from inside each flat dir, `FILENAME_FORMAT='{kind}-{group}-{version}'`) against kube-resources' `crds/gateway-api/v1.6.1/standard-install.yaml` and `crds/envoy-gateway/v1.9.1/envoy-gateway.yaml`.
- [ ] **Step 3:** Verify locally: `grep -c timeouts master-standalone-strict/httproute-gateway-v1.json` → 3; the fixture validates against a local catalog copy of the regenerated strict file.
- [ ] **Step 4:** Commit: "regenerate gateway-api v1.6.1 + envoy-gateway v1.9.1 flat schemas (stale inputs rejected the valid HTTPRouteRule.timeouts field — kube-resources TODO(kube-crds#57))".

### Task 3: Build the catalog

**Files:**
- Create: catalog tree `{fullgroup}/{kind}_{version}.json` at repo root
- Delete: `disagg/` (into `operator.victoriametrics.com/`)

**Interfaces:**
- Consumes: Task 1 converter; kube-resources `crds/` pins.
- Produces: the complete catalog — regenerated entries for the five vendored pin sets (authoritative), `git mv`-ed legacy entries for the rest, disagg folded in.

- [ ] **Step 1:** Regenerate the five pins into the catalog (`FILENAME_FORMAT='{fullgroup}/{kind}_{version}'`): gateway-api v1.6.1, envoy-gateway v1.9.1, cert-manager (both sources), external-secrets bundle, prometheus-operator podmonitors.
- [ ] **Step 2:** `git mv` each remaining `master-standalone-strict/*.json` into its group dir as `{kind}_{version}.json` (parse filenames from the right: version, label, kind; kind lowercased). First-label → full-group mapping decided by the declaring CRD under kube-resources `crds/`, the `disagg/` filenames, or the sources named in `scripts/update-*.sh` — the mapping goes in the PR body; anything uncertain is left in place.
- [ ] **Step 3:** Fold `disagg/` in the same way; `git rm -r disagg`.
- [ ] **Step 4:** Commit: "add versioned catalog ({fullgroup}/{kind}_{version}); fold disagg/".

### Task 4: README + SOURCES.md

**Files:**
- Modify: `README.md` — Create: `SOURCES.md`

- [ ] **Step 1:** README: consumer invocation via the documented templated location
  (`-schema-location 'https://raw.githubusercontent.com/xgen-cloud/kube-crds/master/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'`),
  flat dirs marked deprecated (still served for kube-ci until it migrates), generation commands, required-with-defaults note preserved.
- [ ] **Step 2:** SOURCES.md: group → source (kube-resources pin + version / update-script repo / legacy-migrated) and generation path.
- [ ] **Step 3:** Commit: "document the versioned catalog contract".

### Task 5: Verify, push, PR

- [ ] **Step 1:** Verify: kubeconform `-strict` with the new templated location (local catalog path) over fixtures — HTTPRoute with `timeouts` (Valid), one disagg-migrated VM kind (Valid), one manifest omitting a defaulted field (Valid); then against `master-standalone-strict` flat (the un-migrated long tail still validates).
- [ ] **Step 2:** Push `update-crds` to upstream; re-run the Task 2 Step 1 check against `https://raw.githubusercontent.com/xgen-cloud/kube-crds/update-crds` — expect Valid: 1.
- [ ] **Step 3:** Open the draft PR (no reviewers): body carries the verification output, the migration mapping, and links the design doc.
