#!/usr/bin/env python3
import argparse
import logging
import os
from urllib.parse import quote, unquote, urlparse

import defusedxml.ElementTree as ET
import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)

# ---------- DEFAULT CONFIGURATION ----------
NEXTCLOUD_BASE_URL = "https://cloud.dfki.de/owncloud"  # Your Nextcloud domain
NEXTCLOUD_WEBDAV_ENDPOINT = "public.php/webdav/"  # WebDAV endpoint for public shares
SHARE_TOKEN = "AC2XCHfDoza2rkb"  # nosec # Share token from your public link
SHARE_PASSWORD = os.getenv("NEXTCLOUD_SHARE_PASSWORD", "")  # password for the share (if set)
LOCAL_DIR = "/ds/text/kiba-d/zotero_literaturdatenbank/"
# ----------------------------------


# A small PROPFIND body asking for resource type so we can detect collections
PROPFIND_BODY = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:getcontentlength/>
    <d:getlastmodified/>
    <d:resourcetype/>
  </d:prop>
</d:propfind>
"""


def list_nextcloud_files(nextcloud_webdev_url: str, auth: tuple[str, str]) -> list[str]:
    """
    Returns a list of filenames that are direct (non-directory) children
    of the public share root. Uses PROPFIND with Depth: 1 and parses XML.
    """
    headers = {"Depth": "1", "Content-Type": 'application/xml; charset="utf-8"'}

    resp = requests.request(
        "PROPFIND",
        nextcloud_webdev_url,
        data=PROPFIND_BODY.encode("utf-8"),
        headers=headers,
        auth=auth,
        timeout=30,
    )
    if resp.status_code not in (207, 200):
        raise RuntimeError(f"PROPFIND failed: {resp.status_code} {resp.text[:500]}")

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise RuntimeError(
            f"Failed to parse PROPFIND XML: {e}\nResponse (truncated): {resp.text[:1000]}"
        )

    files = []
    # canonicalize root path (so we can skip the entry for the folder itself)
    requested_path = urlparse(nextcloud_webdev_url).path.rstrip("/")

    # Iterate over all <d:response> entries
    for response_elem in root.findall(".//{DAV:}response"):
        href_elem = response_elem.find("{DAV:}href")
        if href_elem is None or (href_elem.text or "") == "":
            continue
        href_text = href_elem.text
        href_path = str(urlparse(href_text).path)  # path part only
        # skip the entry for the folder itself
        if href_path.rstrip("/") == requested_path:
            continue

        # determine if this response is a collection (directory)
        # look for resourcetype/collection
        is_collection = False
        resourcetype = response_elem.find(".//{DAV:}resourcetype")
        if resourcetype is not None and resourcetype.find("{DAV:}collection") is not None:
            is_collection = True

        if is_collection:
            # skip directories (only top-level files returned)
            continue

        # filename is the last path segment (decoded)
        name = href_path.rstrip("/").split("/")[-1]
        if not name:
            continue
        name = unquote(name)
        files.append(name)

    return files


def list_local_files(local_dir: str) -> list[str]:
    """Non-recursive listing of files in LOCAL_DIR (files only)."""
    return [f for f in os.listdir(local_dir) if os.path.isfile(os.path.join(local_dir, f))]


def download_file(
    filename: str, local_dir: str, nextcloud_webdev_url: str, auth: tuple[str, str]
) -> None:
    url = nextcloud_webdev_url + quote(filename, safe="")
    local_path = os.path.join(local_dir, filename)
    logging.info(f"Downloading {url} to {local_path}")
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with requests.get(url, auth=auth, stream=True, timeout=30) as r:
        if r.status_code == 200:
            with open(local_path, "wb") as fh:
                for chunk in tqdm(
                    r.iter_content(chunk_size=8192),
                    desc=f"Downloading {url} to {local_path}",
                    unit="KB",
                ):
                    if chunk:
                        fh.write(chunk)
        else:
            raise RuntimeError(f"Failed to download {url}: {r.status_code} {r.text[:200]}")


def upload_file(
    filename: str, local_dir: str, nextcloud_webdev_url: str, auth=tuple[str, str]
) -> None:
    url = nextcloud_webdev_url + quote(filename, safe="")
    local_path = os.path.join(local_dir, filename)
    logging.info(f"Uploading {local_path} to {url}")
    with open(local_path, "rb") as fh:
        resp = requests.put(url, auth=auth, data=fh, timeout=30)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Failed to upload {local_path}: {resp.status_code} {resp.text[:500]}")


def sync_nextcloud(
    local_dir: str, share_token: str, share_password: str, base_url: str, webdav_endpoint: str
) -> None:
    # quick sanity checks
    if not os.path.isdir(local_dir):
        raise SystemExit(f"Local folder does not exist: {local_dir}")

    auth = (share_token, share_password)

    nextcloud_webdev_url = f'{base_url.rstrip("/")}/{webdav_endpoint}'
    logging.info(
        f"Listing Nextcloud files from {nextcloud_webdev_url}, share token {share_token} ..."
    )
    nc_files = set(list_nextcloud_files(nextcloud_webdev_url, auth=auth))
    logging.info(f"Listing local files from {local_dir} ...")
    local_files = set(list_local_files(local_dir))

    to_download = nc_files - local_files
    to_upload = local_files - nc_files

    if not to_download and not to_upload:
        logging.info("Folders are already in sync.")
        return

    if to_download:
        logging.info(f"Downloading {len(to_download)} file(s) from Nextcloud...")
        for f in sorted(to_download):
            download_file(
                f, local_dir=local_dir, nextcloud_webdev_url=nextcloud_webdev_url, auth=auth
            )

    if to_upload:
        logging.info(f"Uploading {len(to_upload)} file(s) to Nextcloud...")
        for f in sorted(to_upload):
            upload_file(
                f, local_dir=local_dir, nextcloud_webdev_url=nextcloud_webdev_url, auth=auth
            )

    logging.info("Sync complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync with Nextcloud public share. Downloads files that are in the share but not locally, "
        "and uploads files that are local but not in the share.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--local-dir", type=str, default=LOCAL_DIR, help="Local directory to sync with Nextcloud"
    )
    parser.add_argument(
        "--share-token", type=str, default=SHARE_TOKEN, help="Nextcloud share token"
    )
    parser.add_argument(
        "--share-password",
        type=str,
        default=SHARE_PASSWORD,
        help="Password for the Nextcloud share (if it is password protected), loaded from .env file "
        "(key: NEXTCLOUD_SHARE_PASSWORD) per default",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=NEXTCLOUD_BASE_URL,
        help="Base URL of the Nextcloud instance",
    )
    parser.add_argument(
        "--webdav-endpoint",
        type=str,
        default=NEXTCLOUD_WEBDAV_ENDPOINT,
        help="WebDAV endpoint for public shares (relative to base URL)",
    )
    args = parser.parse_args()

    kwargs = vars(parser.parse_args())
    sync_nextcloud(**kwargs)
