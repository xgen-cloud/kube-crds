Commonly used CRDs in a format that kubeval/kubeconform can use.

```
kubeconform -summary -strict -schema-location default -schema-location path/to/kube-crds path/to/hydrated.yaml
```

Schema files were created based on the script in the [kubeconform repo][1]. A lightly edited version of this script exists here as [scripts/openapi2jsonschema.py](scripts/openapi2jsonschema.py), specifcally supporting the [`x-kubernetes-preserve-unknown-fields`](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#controlling-pruning) field.

Make sure to run with `export FILENAME_FORMAT='{kind}-{group}-{version}'`. Schema files should be in both `-strict` and non-strict directories.

```sh
# in respective subdirectory, master-standalone and master-standalone-strict
../scripts/openapi2jsonschema.py path/to/source-crds.yaml
```

[1]: https://github.com/yannh/kubeconform/tree/932b35d71ffc806ff5845ced8a9cb52c0104e883#converting-an-openapi-file-to-a-json-schema

## Upbound AWS schemas

The `*.aws.m.upbound.io` schemas are generated rather than hand-added, from the provider packages
pinned in `xgen-cloud/kube-resources`
(`apps/base/crossplane-v2/providers/upbound-provider-family-aws.yaml`). That file is the only
hand-maintained copy of these versions.

```sh
uv run scripts/generate-upbound-aws.py          # rebuild from scripts/upbound-aws.lock
uv run scripts/generate-upbound-aws.py --sync   # refresh the lock from kube-resources first
```

`scripts/upbound-aws.lock` is a generated record of what the committed schemas were built from.
CI rebuilds from it and fails if the result differs, so a PR is checked without needing
private-repo credentials. `--sync` does need an authenticated `gh`, so run it deliberately, when
the provider version in kube-resources moves.

### Details

Only the per-service groups are generated. The base group `aws.m.upbound.io` is deliberately left
out: it holds `ProviderConfig`, and kubeconform derives the same filename from the legacy
`aws.upbound.io` group, whose ProviderConfigs are live in `kube-resources/apps` and validated by
`make test-flux`.

That collision is not unique to `ProviderConfig`: kubeconform builds the filename from the first
label of the group alone, so `s3.aws.m.upbound.io` and the legacy `s3.aws.upbound.io` both resolve
to `bucket-s3-v1beta1.json`. The two schemas are not identical (the legacy one has
`deletionPolicy`), so a legacy manifest now validates against the namespaced schema and can fail on
a field that is valid for it. Nothing in the validated corpus authors legacy managed resources as
top-level documents today, which is why this is acceptable. If that changes, the fix is a
`disagg/`-style directory keyed on `{fullgroup}` plus a `{{.Group}}` schema location in each
consumer.
