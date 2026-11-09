# Schema sources

Where each group's schemas come from and how they are generated.
Generation is `scripts/write-schemas.sh` unless noted; "CRD pin" means
the manifest vendored in xgen-cloud/kube-resources `crds/`.

| Group | Source | Generated from |
|---|---|---|
| `acme.cert-manager.io` | CRD pin (cert-manager v1.21.2) | `crds/cert-manager/cert-manager.crds.v1.21.2.yaml` |
| `cert-manager.io` | CRD pin (cert-manager v1.21.2) | `crds/cert-manager/cert-manager.crds.v1.21.2.yaml` |
| `policy.cert-manager.io` | CRD pin (approver-policy v0.22.0) | `crds/cert-manager/approver-policy/approver-policy.crds.v0.22.0.yaml` |
| `external-secrets.io`, `generators.external-secrets.io` | CRD pin (external-secrets) | `crds/external-secrets/bundle.yaml` |
| `monitoring.coreos.com` | CRD pin (prometheus-operator) | `crds/prometheus-operator/monitoring.coreos.com_podmonitors.yaml` |
| `gateway.networking.k8s.io` | CRD pin (gateway-api v1.6.1) | `crds/gateway-api/v1.6.1/standard-install.yaml` |
| `gateway.envoyproxy.io` | CRD pin (envoy-gateway v1.9.1) | `crds/envoy-gateway/v1.9.1/envoy-gateway.yaml` |
| `operator.victoriametrics.com` | CRD pin (vm-operator + rcell) | `crds/victoria-metrics-operator/crds.yaml`, `crds/victoria-metrics-operator-rcell/crds.yaml` |
| `clickhouse.altinity.com`, `clickhouse-keeper.altinity.com` | CRD pin | `crds/clickhouse-operator/` |
| `chaos-mesh.org` | CRD pin | `crds/chaos-mesh/` |
| `sloth.slok.dev` | CRD pin | `crds/sloth/` |
| `kuberhealthy.github.io` | CRD pin | `crds/kuberhealthy/` |
| `autoscaling.k8s.io` | CRD pin (VPA) | `crds/vertical-pod-autoscaler/` |
| `deployment.10gen.cc`, `pagerduty.10gen.cc`, `networking.10gen.com` | CRD pin | `crds/dev/` |
| `agentengine.mongodb.com`, `agentic.mongodb.com` | CRD pin | `crds/agentic-platform/`, `crds/api-gateway/` |
| `config.gatekeeper.sh` (+ other gatekeeper subgroups) | CRD pin | `crds/gatekeeper/` |
| `aws.elbv2.k8s.io`-family (`elbv2.k8s.aws`) | CRD pin | `crds/aws-load-balancer-controller/` |
| `s3.aws.upbound.io`, `iam.aws.upbound.io`, `ecr.aws.upbound.io`, `dynamodb.aws.upbound.io`, `sns.aws.upbound.io`, `sqs.aws.upbound.io`, `kinesis.aws.upbound.io` | upbound provider-aws pin | `update-crossplane-schemas.sh` (pins from kube-resources `apps/base/crossplane-v2/providers/`) |
| `authorization.azure.upbound.io`, `managedidentity.azure.upbound.io` | upbound provider-azure pin | `update-crossplane-schemas.sh` |
| `networking.istio.io`, `security.istio.io`, `telemetry.istio.io`, `extensions.istio.io` | Istio CRDs (manual import) | `write-schemas.sh` on the istio CRD manifests |
| `argoproj.io` | Argo Rollouts CRDs (manual import) | `write-schemas.sh` |
| `flink.apache.org` | Flink operator CRDs (manual import) | `write-schemas.sh` |
| `keda.sh` | KEDA CRDs (manual import) | `write-schemas.sh` |
| `olm.operatorframework.io` | OLM v1.11.0 | `write-schemas.sh` on the OLM release CRDs |
| `kro.run`, `internal.kro.run` | kro v0.9.4 release + RGD | `update-kro-schemas.sh` |
| tenant XRD groups | tenant repos (10gen-internal) | `update-xrd-schemas.sh <tenant-repo>` |

## Legacy files still flat (triage)

These remain in `master-standalone-strict/` because their full group
could not be established from in-repo evidence; they are served only
via the deprecated flat layout:

- `storage/*` (32 files) — mixed Azure (`*.azure.upbound.io`) and GCS
  (`*.gcp.upbound.io`) kinds; the per-kind provider split needs the
  upbound provider pins pulled per kind.
- `generators/*` (7 files) — legacy external-secrets generator
  `v1alpha1` kinds the current bundle no longer serves
  (`acraccesstoken`, `ecrauthorizationtoken`, `fake`, `gcraccesstoken`,
  `password`, `vaultdynamicsecret`, `webhook`).
- `hello-helix/*` (4 files) and `overrides/*` (1 file) — tenant XRD
  groups; regenerate via `update-xrd-schemas.sh` against the tenant
  repo to establish them.
