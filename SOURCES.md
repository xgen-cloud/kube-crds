# Schema sources

Where each group's schemas come from and how they are generated.
Generation is `scripts/write-schemas.sh` unless noted; "CRD pin" means
the manifest vendored in xgen-cloud/kube-resources `crds/`.

| Group | Source |
|---|---|
| `acme.cert-manager.io`, `cert-manager.io` | CRD pin: `crds/cert-manager/cert-manager.crds.v1.21.2.yaml` (regenerated) |
| `policy.cert-manager.io` | CRD pin: `crds/cert-manager/approver-policy/approver-policy.crds.v0.22.0.yaml` (regenerated) |
| `external-secrets.io`, `generators.external-secrets.io` | CRD pin: `crds/external-secrets/bundle.yaml` (regenerated) |
| `monitoring.coreos.com` | CRD pin for PodMonitor; remaining kinds are legacy migrations — regenerate from the full prometheus-operator CRDs to refresh |
| `gateway.networking.k8s.io` | CRD pin: `crds/gateway-api/v1.6.1/standard-install.yaml` (regenerated) |
| `gateway.envoyproxy.io` | CRD pin: `crds/envoy-gateway/v1.9.1/envoy-gateway.yaml` (regenerated) |
| `operator.victoriametrics.com` | CRD pins: `crds/victoria-metrics-operator/crds.yaml` + `crds/victoria-metrics-operator-rcell/crds.yaml` (regenerated; supersedes the old `disagg/` copies) |
| `clickhouse.altinity.com`, `clickhouse-keeper.altinity.com` | legacy migration (chaos/clickhouse kinds re-named to un-mangled form); source CRDs: `crds/clickhouse-operator/` |
| `chaos-mesh.org` | legacy migration (re-named to un-mangled form); source CRDs: `crds/chaos-mesh/` |
| `sloth.slok.dev`, `kuberhealthy.github.io`, `autoscaling.k8s.io` (VPA), `deployment.10gen.cc`, `pagerduty.10gen.cc`, `crossplane.io` (StoreConfig) | legacy migration (manual imports originally) |
| `networking.10gen.com` | legacy migration (meshclown kinds); source CRDs: `crds/meshclown/crds.yaml` |
| `config.gatekeeper.sh`-family | CRD pin: `crds/gatekeeper/` |
| `elbv2.k8s.aws`, `aga.k8s.aws` | CRD pin: `crds/aws-load-balancer-controller/` |
| `agentengine.mongodb.com`, `agentic.mongodb.com` | CRD pin: `crds/agentic-platform/`, `crds/api-gateway/` |
| `s3/iam/ecr/dynamodb/sns/sqs/kinesis .aws.upbound.io`, `authorization/managedidentity .azure.upbound.io` | upbound provider pins — `scripts/update-crossplane-schemas.sh` (pins from kube-resources `apps/base/crossplane-v2/providers/`) |
| `networking/security/telemetry/extensions .istio.io` | Istio CRDs (legacy migration; kinds un-mangled) |
| `argoproj.io` (Argo Rollouts), `flink.apache.org`, `keda.sh` | CRDs from the operator releases (legacy migration) |
| `olm.operatorframework.io` | OLM v1.11.0 release CRDs |
| `kro.run`, `internal.kro.run` | kro v0.9.4 release + RGD — `scripts/update-kro-schemas.sh` |
| tenant XRD groups | tenant repos (10gen-internal) — `scripts/update-xrd-schemas.sh <tenant-repo>` |

Kinds whose group's first DNS label contains a dash (`chaos-mesh.org`,
`cert-manager.io`, `external-secrets.io`, `clickhouse-keeper.altinity.com`,
`kubernetes-client.io`, `networking.10gen.com`, …) were originally
mis-filed with a residual group-label fragment in the kind name; the
catalog carries the corrected names.

## Legacy files still flat (triage, 37 files)

These remain in `master-standalone-strict/` because their full group
could not be established from in-repo evidence; they are served only
via the deprecated flat layout:

- `storage/*` (32 files) — mixed Azure (`*.azure.upbound.io`) and GCS
  (`*.gcp.upbound.io`) kinds; the per-kind provider split needs the
  upbound provider pins pulled per kind.
- `hello-helix/*` (3 files), `helix/*` (1 file) and `overrides/*`
  (1 file) — tenant XRD groups; regenerate via
  `update-xrd-schemas.sh` against the tenant repo to establish them.
