Commonly used CRDs in a format that kubeval/kubeconform can use.


```
kubeval --strict --additional-schema-locations https://raw.githubusercontent.com/dmichel1/kube-crds/master kube-resources.yaml
```

Schema files were created based on the script in the [kubeconform repo][1].

Make sure to run with `export FILENAME_FORMAT='{kind}-{group}-{version}'`. Schema files should be in both `-strict` and non-strict directories.


[1]: https://github.com/yannh/kubeconform/tree/932b35d71ffc806ff5845ced8a9cb52c0104e883#converting-an-openapi-file-to-a-json-schema
