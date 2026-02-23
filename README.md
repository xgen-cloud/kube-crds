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
