Commonly used CRDs in a format that kubeval/kubeconform can use.

```
kubeconform -summary -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/xgen-cloud/kube-crds/master/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  path/to/hydrated.yaml
```

## Layout

Schemas live in the **versioned catalog**: one file per kind per
apiVersion, under the resource's full API group —
`{group}/{kind}_{apiVersion}.json`, kinds lowercase (e.g.
`gateway.networking.k8s.io/httproute_v1.json`,
`cert-manager.io/certificate_v1.json`). Consumer location values must
be the templated form shown above: kubeconform expands
`{{.Group}}`, `{{.ResourceKind}}` (lowercased), and
`{{.ResourceAPIVersion}}` per manifest and fetches the file.
raw.githubusercontent.com is case-sensitive — kind case in the
filenames is not cosmetic.

The flat `master-standalone/` and `master-standalone-strict/`
directories are **deprecated legacy**, kept only until kube-ci (the
last consumer resolving the flat layout) migrates to the templated
location. They follow the kubernetesjsonschema.dev naming that
kubeconform's defaults produce for a bare (non-templated)
`-schema-location`.

## Schema sources

Every group's schema source and generation path is recorded in
[SOURCES.md](SOURCES.md).

Schemas were created based on the script in the [kubeconform repo][1]
— a lightly edited version lives here as
[scripts/openapi2jsonschema.py](scripts/openapi2jsonschema.py),
specifically supporting the
[`x-kubernetes-preserve-unknown-fields`](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#controlling-pruning)
field.

Every schema written through `scripts/write-schemas.sh` — provider and
XRD regenerations included — drops any `required` entry whose property
carries a `default`. kubeconform applies no CRD defaults, so it would
otherwise reject a manifest the API server accepts.

```sh
# writes both the deprecated flat dirs and the versioned catalog
./scripts/write-schemas.sh path/to/source-crds.yaml
```

For Crossplane XRDs, point `scripts/update-xrd-schemas.sh` at the repo
that defines them. It finds every XRD, including under `.infra/`, and
writes both layouts:

```sh
./scripts/update-xrd-schemas.sh path/to/tenant-repo
```

For kro, `scripts/update-kro-schemas.sh` writes the schemas a
`ResourceGraphDefinition` needs: kro's own CRDs, out of the release
manifest it is pinned to, and the kind the RGD defines. The second has
no CRD until kro compiles the graph, so it comes from the RGD plus a
cluster serving the CRDs the graph references. That needs kro's CLI,
which ships no binaries — build it from the pinned tag:

```sh
git clone --depth 1 --branch v0.9.4 https://github.com/kubernetes-sigs/kro
go build -C kro/cmd/kro -o "$PWD/kro-cli" .

KUBECONFIG=<cluster> KRO=$PWD/kro-cli ./scripts/update-kro-schemas.sh path/to/rgd.yaml
```

The `-o` is absolute and named to miss the clone directory: `-C` moves
the build's working directory before `-o` is resolved, so a bare
`-o kro` lands at `kro/cmd/kro/kro`.

`KUBECONFIG` is the only way to aim it: `--context` and `--kubeconfig`
exist on the root command but are never passed to the client, so they
change nothing. Regenerate whenever the RGD changes — kro infers
`status` and the generated names, which is exactly what a hand-written
schema loses.

[1]: https://github.com/yannh/kubeconform/tree/932b35d71ffc806ff5845ced8a9cb52c0104e883#converting-an-openapi-file-to-a-json-schema
