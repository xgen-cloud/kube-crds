Commonly used CRDs in a format that kubeval/kubeconform can use.

```
kubeconform -summary -strict -schema-location default -schema-location path/to/kube-crds path/to/hydrated.yaml
```

Schema files were created based on the script in the [kubeconform repo][1]. A lightly edited version of this script exists here as [scripts/openapi2jsonschema.py](scripts/openapi2jsonschema.py), specifically supporting the [`x-kubernetes-preserve-unknown-fields`](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#controlling-pruning) field.

Make sure to run with `export FILENAME_FORMAT='{kind}-{group}-{version}'`. Schema files should be in both `-strict` and non-strict directories.

Every schema written through `write-schemas.sh` — provider and XRD regenerations included, not just kro's — drops any `required` entry whose property carries a `default`. kubeconform applies no CRD defaults, so it would otherwise reject a manifest the API server accepts.

```sh
# in respective subdirectory, master-standalone and master-standalone-strict
../scripts/openapi2jsonschema.py path/to/source-crds.yaml
```

For Crossplane XRDs, point `scripts/update-xrd-schemas.sh` at the repo that defines them. It finds every XRD, including under `.infra/`, and writes both directories:

```sh
./scripts/update-xrd-schemas.sh path/to/tenant-repo
```

For kro, `scripts/update-kro-schemas.sh` writes the schemas a `ResourceGraphDefinition` needs: kro's own CRDs, out of the release manifest it is pinned to, and the kind the RGD defines. The second has no CRD until kro compiles the graph, so it comes from the RGD plus a cluster serving the CRDs the graph references. That needs kro's CLI, which ships no binaries — build it from the pinned tag:

```sh
git clone --depth 1 --branch v0.9.4 https://github.com/kubernetes-sigs/kro
go build -C kro/cmd/kro -o "$PWD/kro-cli" .

KUBECONFIG=<cluster> KRO=$PWD/kro-cli ./scripts/update-kro-schemas.sh path/to/rgd.yaml
```

The `-o` is absolute and named to miss the clone directory: `-C` moves the build's working directory before `-o` is resolved, so a bare `-o kro` lands at `kro/cmd/kro/kro`.

`KUBECONFIG` is the only way to aim it: `--context` and `--kubeconfig` exist on the root command but are never passed to the client, so they change nothing. Regenerate whenever the RGD changes — kro infers `status` and the generated names, which is exactly what a hand-written schema loses.

[1]: https://github.com/yannh/kubeconform/tree/932b35d71ffc806ff5845ced8a9cb52c0104e883#converting-an-openapi-file-to-a-json-schema
