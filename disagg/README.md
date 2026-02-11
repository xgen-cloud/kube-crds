# disagg CRDs

Due to the way `kubeconform` treats the `.Group` variable in the `-schema-location` differently from `{group}` in the `openapi2jsonschema.py` script, we must use a different file format when converting YAML CRDs to JSON in this `disagg` folder (or any other "non-standard" folder).

```sh
export FILENAME_FORMAT={kind}-{fullgroup}-{version}
# cd disagg
../../kubeconform/scripts/openapi2jsonschema.py ../../kube-resources/crds/victoria-metrics-operator-rcell/crds.yaml
```

### Details

Given an `apiVersion: operator.victoriametrics.com/v1`, the [`-schema-location` template](https://github.com/yannh/kubeconform/blob/e60892483e5b7e5dffa95fc3f121646a96ca270f/pkg/registry/registry.go#L33) uses everything before the `/` for `{{.Group}}` (i.e. `operator.victoriametrics.com`) while the [`openapi2jsonschema.py` script](https://github.com/yannh/kubeconform/blob/e60892483e5b7e5dffa95fc3f121646a96ca270f/scripts/openapi2jsonschema.py#L157-L158) has `{group}` that is split at the first `.` (i.e. `operator`) and `{fullgroup}` that is the full group name.
