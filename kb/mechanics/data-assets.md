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

## Path formats: recognize the scheme by its shape

📘 From *Create data assets* and *Access data in a job* (read 2026-10-31).
Added after practice question [Q1](../../practice/mlops/q001-data-asset-public-blob-uri.md),
where the site's answer got this wrong.

| Where the data is | Path | Notes |
|---|---|---|
| Local folder | `./data/my_data` | Uploaded to the default datastore on create |
| Public web / **public** blob container | `https://<account>.blob.core.windows.net/<container>/<path>` | Input only; no auth, so public only |
| Azure Blob (private) | `wasbs://<container>@<account>.blob.core.windows.net/<path>` | **Container before the `@`**; identity-based auth |
| ADLS Gen2 | `abfss://<filesystem>@<account>.dfs.core.windows.net/<path>` | Note **`.dfs.`**, not `.blob.` |
| Datastore | `azureml://datastores/<datastore>/paths/<path>` | Uses the datastore's credentials. The **recommended** form inside Azure ML (input *and* output) |
| Existing data asset | `azureml:<name>:<version>` | What jobs should reference |

How to read a question's URL:
- `<container>@<account>` → `wasbs` (blob) or `abfss` (dfs).
- `<account>/<container>` → `https`.
- If the dropdown only offers a scheme and the rest of the URL is fixed,
  **the URL's shape decides**, not the word "blob".

## Loading an MLTable in code

From practice question [Q47](../../practice/mlops/q047-load-mltable.md).

```python
import mltable
tbl = mltable.load("./sample_data")      # the FOLDER that contains the file named MLTable
df  = tbl.to_pandas_dataframe()
```

- `load()` takes the **folder**, not `./sample_data/MLTable`, and not a glob
  of the raw files (that skips the recipe).
- The folder can also be a datastore URI
  (`azureml://datastores/<ds>/paths/sample_data`) or a data asset's path.
- `mltable.load` reads; `save` writes a definition; `take(n)` samples rows.

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

## Datastores and versions in SDK v2

From practice questions [Q124](../../practice/mlops/q124-blob-datastore-account-key.md), [Q125](../../practice/mlops/q125-image-files-uri-folder-wasbs.md), [Q126](../../practice/mlops/q126-cluster-and-registered-data.md), [Q130](../../practice/mlops/q130-versioned-data-reproducibility.md).

```python
from azure.ai.ml.entities import AzureBlobDatastore, AccountKeyConfiguration
store = AzureBlobDatastore(
    name="blobdatastore",
    account_name="sampleaccount1",
    container_name="samplecontainer1",   # the container parameter
    protocol="wasbs",                     # or "https" (default)
    credentials=AccountKeyConfiguration(account_key="..."),
)
ml_client.create_or_update(store)
```

- Images and other unstructured files → `uri_folder`; tabular data for
  AutoML → MLTable ("tabular dataset" is the v1 name).
- **Reproducibility:** each data asset version is immutable and a job input
  `azureml:<name>:<version>` records exactly what a run used. Write each data
  refresh to a new path, because a version points at a path, not a copy.
