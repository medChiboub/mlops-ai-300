# Data assets

## The one idea

A **data asset** is a *named, versioned pointer* to data in a datastore. It
doesn't hold the data. It says "`diabetes-data` version 1 **is** this exact
path." Jobs refer to `azureml:diabetes-data:1` instead of a storage URL, so:

- the path can be long and ugly, and nobody needs to know it
- versions are **immutable**: `:1` always means the same bytes, so a job's
  lineage records exactly which data it used
- new data means a new version (`:2`), not overwriting `:1`

## The three types

| Type | Points at | Read in code as | Use for |
|---|---|---|---|
| `uri_file` | One file | A path to that file (`pd.read_csv(path)`) | One CSV, one parquet file, etc. |
| `uri_folder` | A folder | A path to a directory | Many files, images, anything not tabular |
| `mltable` | A folder containing an **`MLTable`** file | `mltable.load(path).to_pandas_dataframe()` | **Tabular data with a read recipe. Required by AutoML** |

## What `az ml data create` actually did (lab 01 §1)

```bash
az ml data create --type uri_file --name diabetes-data     --path ../data/diabetes-data/diabetes.csv
az ml data create --type mltable  --name diabetes-training --path ../data/diabetes-data
```

The path is **local**, so the CLI:

1. **uploads** the file or folder to the default datastore, `workspaceblobstore`,
   under `LocalUpload/<content-hash>/…`
2. **registers** the asset with the resulting `azureml://` URI and version 1

Real result:

```
diabetes-data:1      → azureml://…/datastores/workspaceblobstore/paths/LocalUpload/3d8efe6c…/diabetes.csv
diabetes-training:1  → azureml://…/datastores/workspaceblobstore/paths/LocalUpload/03f6bb5b…/diabetes-data/
```

The same local CSV was uploaded **twice**, into two different hash folders,
because the two commands uploaded different things (a single file vs. the
whole folder). The folder is named after the hash of its contents, so
re-running with unchanged data reuses the existing upload.

If `--path` had already been an `azureml://` or `https://` URI, nothing
would be uploaded. The asset would simply point there.

## What's in an MLTable

`data/diabetes-data/MLTable`:

```yaml
paths:
  - file: ./diabetes.csv
transformations:
  - read_delimited:
        delimiter: ','
        encoding: 'ascii'
```

It's a **recipe, not a schema**. It says which files to read and how to parse
them. Column names and types are inferred when the data is read. Recipes can
also filter rows, select columns, glob many files into one table, or split
one field into several. This is why AutoML wants MLTable: it needs to
materialize a *table* from whatever files you have, the same way every time.

The data itself (from a local check):
- 10,000 rows, 10 columns (`PatientID`, 8 clinical features, and `Diabetic`
  as the label)
- 33.4% positive, so mildly imbalanced
- no missing values
- `PatientID` has 9,959 unique values out of 10,000: it's an ID, not a
  feature. The MLflow notebook drops it by hand. What AutoML does with it is
  in [automl.md](automl.md).

## How a job reads an asset

A job input declares an asset plus a **mode**:
- `ro_mount` is the default for uri types: the files are streamed from blob
  storage on demand.
- `download` copies the files to the node's disk first.
- `rw_mount` is for outputs.
- `eval_mount` / `direct` apply to mltable.

On the exam: huge data → mount; many small files read repeatedly →
download.

## Lab vs. my project

My project has one asset, `diabetes-raw` (uri_file, declared in YAML and
versioned in Git). For AutoML it pointed at a local, **unregistered** MLTable
folder, because its only registered asset was uri_file. The lab registers
both types up front.
