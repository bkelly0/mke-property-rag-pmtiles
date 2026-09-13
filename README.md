# json-to-pmtiles Cloud Run Job

A Cloud Run Job that downloads a GeoJSON `FeatureCollection` (e.g. MapLibre-format)
JSON file from Cloud Storage, converts it to [PMTiles](https://github.com/protomaps/PMTiles)
using [tippecanoe](https://github.com/felt/tippecanoe), and uploads the resulting
`.pmtiles` file back to Cloud Storage.

## Files

- [Dockerfile](Dockerfile) — builds tippecanoe from source and packages it with the Python job.
- [main.py](main.py) — downloads input, runs tippecanoe, uploads output.
- [requirements.txt](requirements.txt) — Python dependencies.
- [cloudbuild.yaml](cloudbuild.yaml) — builds the image and deploys the Cloud Run Job with Cloud Build.

## Configuration

The job reads these environment variables at runtime:

| Variable | Required | Description |
|---|---|---|
| `SOURCE_URI` | yes | `gs://bucket/path/to/input.json` — the FeatureCollection to convert |
| `DEST_URI` | yes | `gs://bucket/path/to/output.pmtiles` — where to upload the result |
| `LAYER_NAME` | no | Tileset layer name (default: `data`) |
| `MIN_ZOOM` | no | Passed to tippecanoe as `-z` |
| `MAX_ZOOM` | no | Passed to tippecanoe as `-Z` |
| `TIPPECANOE_EXTRA_ARGS` | no | Extra space-separated tippecanoe flags, e.g. `--drop-densest-as-needed` |

## Deploy

Requires the [gcloud CLI](https://cloud.google.com/sdk/gcloud) authenticated against your project,
with the Cloud Build, Artifact Registry, and Cloud Run APIs enabled, and an Artifact Registry
docker repository already created:

```bash
gcloud artifacts repositories create cloud-run-jobs \
  --project my-project --location us-central1 --repository-format=docker
```

Then build and deploy with Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml --project my-project .
```

Override the region, repo, or job name via substitutions:

```bash
gcloud builds submit --config cloudbuild.yaml --project my-project \
  --substitutions=_REGION=us-central1,_REPO=cloud-run-jobs,_JOB_NAME=json-to-pmtiles .
```

This builds the container, pushes it to Artifact Registry, and creates (or updates) a Cloud Run
Job named `json-to-pmtiles`.

## Run

```bash
gcloud run jobs execute json-to-pmtiles \
  --project my-project --region us-central1 \
  --update-env-vars=SOURCE_URI=gs://my-src-bucket/input.json,DEST_URI=gs://my-dest-bucket/output.pmtiles
```

## Permissions

The Cloud Run Job's runtime service account needs:

- `roles/storage.objectViewer` (or equivalent) on the source bucket
- `roles/storage.objectCreator` (or equivalent) on the destination bucket

## Local testing

```bash
docker build -t json-to-pmtiles .
docker run --rm \
  -e SOURCE_URI=gs://my-src-bucket/input.json \
  -e DEST_URI=gs://my-dest-bucket/output.pmtiles \
  -v $HOME/.config/gcloud:/root/.config/gcloud:ro \
  json-to-pmtiles
```
