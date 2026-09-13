"""Cloud Run Job: download a GeoJSON FeatureCollection from Cloud Storage,
convert it to PMTiles with tippecanoe, and upload the result back to Cloud Storage.

Configuration is via environment variables:

  SOURCE_URI        gs://bucket/path/to/input.json (required)
  DEST_URI          gs://bucket/path/to/output.pmtiles (required)
  LAYER_NAME        name of the tileset layer (default: "data")
  MIN_ZOOM          minimum zoom level, passed as -z (optional)
  MAX_ZOOM          maximum zoom level, passed as -Z (optional)
  TIPPECANOE_EXTRA_ARGS  extra space-separated tippecanoe args (optional)
"""

import logging
import os
import shlex
import subprocess
import sys
import tempfile

from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("json-to-pmtiles")


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Expected a gs:// URI, got: {uri}")
    without_scheme = uri[len("gs://"):]
    bucket, _, blob_path = without_scheme.partition("/")
    if not bucket or not blob_path:
        raise ValueError(f"Malformed gs:// URI, expected gs://bucket/path: {uri}")
    return bucket, blob_path


def download_blob(client: storage.Client, uri: str, dest_path: str) -> None:
    bucket_name, blob_path = parse_gcs_uri(uri)
    log.info("Downloading %s to %s", uri, dest_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(dest_path)


def upload_blob(client: storage.Client, src_path: str, uri: str) -> None:
    bucket_name, blob_path = parse_gcs_uri(uri)
    log.info("Uploading %s to %s", src_path, uri)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(src_path)


def run_tippecanoe(input_path: str, output_path: str) -> None:
    layer_name = os.environ.get("LAYER_NAME", "data")
    min_zoom = os.environ.get("MIN_ZOOM")
    max_zoom = os.environ.get("MAX_ZOOM")
    extra_args = shlex.split(os.environ.get("TIPPECANOE_EXTRA_ARGS", ""))

    cmd = [
        "tippecanoe",
        "-o", output_path,
        "-l", layer_name,
        "--force",
    ]
    if min_zoom is not None:
        cmd += ["-z", min_zoom]
    if max_zoom is not None:
        cmd += ["-Z", max_zoom]
    cmd += extra_args
    cmd.append(input_path)

    log.info("Running: %s", " ".join(shlex.quote(c) for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        log.info("tippecanoe stdout:\n%s", result.stdout)
    if result.stderr:
        log.info("tippecanoe stderr:\n%s", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"tippecanoe exited with code {result.returncode}")


def main() -> int:
    source_uri = os.environ.get("SOURCE_URI")
    dest_uri = os.environ.get("DEST_URI")

    if not source_uri or not dest_uri:
        log.error("SOURCE_URI and DEST_URI environment variables are required")
        return 1

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, "input.json")
            output_path = os.path.join(tmp_dir, "output.pmtiles")

            client = storage.Client()
            download_blob(client, source_uri, input_path)
            run_tippecanoe(input_path, output_path)
            upload_blob(client, output_path, dest_uri)

        log.info("Done. Wrote %s", dest_uri)
        return 0
    except Exception:
        log.exception("Job failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
