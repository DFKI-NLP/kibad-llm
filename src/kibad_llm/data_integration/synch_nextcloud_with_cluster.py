#!/usr/bin/env python3
import os
from urllib.parse import quote, unquote, urlparse

import defusedxml.ElementTree as ET
import requests
from tqdm import tqdm

# ---------- CONFIGURATION ----------
NEXTCLOUD_BASE_URL = "https://cloud.dfki.de/owncloud/"  # Your Nextcloud domain
SHARE_TOKEN = "dPc2BSDDEAT4R2W"  # nosec # Share token from your public link
LOCAL_DIR = "/ds/text/kiba-d/zotero_literaturdatenbank/"
NEXTCLOUD_BASE_FOLDER = "PDFs%20Literaturdatenbank/"
# ----------------------------------

# Derived URL
NEXTCLOUD_WEBDAV_URL = f"{NEXTCLOUD_BASE_URL}/public.php/webdav/{NEXTCLOUD_BASE_FOLDER}"

# Auth for public share: (share_token, password) if password protected; else just token
# if SHARE_PASSWORD:
#    AUTH = (SHARE_TOKEN, SHARE_PASSWORD)
# else:
#    AUTH = (SHARE_TOKEN, "")
AUTH = (SHARE_TOKEN, "")

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


def list_nextcloud_files():
    """
    Returns a list of filenames that are direct (non-directory) children
    of the public share root. Uses PROPFIND with Depth: 1 and parses XML.
    """
    headers = {"Depth": "1", "Content-Type": 'application/xml; charset="utf-8"'}

    resp = requests.request(
        "PROPFIND",
        NEXTCLOUD_WEBDAV_URL,
        data=PROPFIND_BODY.encode("utf-8"),
        headers=headers,
        auth=AUTH,
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
    requested_path = urlparse(NEXTCLOUD_WEBDAV_URL).path.rstrip("/")

    # Iterate over all <d:response> entries
    for response_elem in root.findall(".//{DAV:}response"):
        href_elem = response_elem.find("{DAV:}href")
        if href_elem is None or (href_elem.text or "") == "":
            continue
        href_text = href_elem.text
        href_path = urlparse(href_text).path  # path part only
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


def list_local_files():
    """Non-recursive listing of files in LOCAL_DIR (files only)."""
    return [f for f in os.listdir(LOCAL_DIR) if os.path.isfile(os.path.join(LOCAL_DIR, f))]


def download_file(filename):
    url = NEXTCLOUD_WEBDAV_URL + quote(filename, safe="")
    local_path = os.path.join(LOCAL_DIR, filename)
    print(f"Downloading {url} to {local_path}")
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with requests.get(url, auth=AUTH, stream=True, timeout=30) as r:
        if r.status_code == 200:
            with open(local_path, "wb") as fh:
                for chunk in tqdm(
                    r.iter_content(chunk_size=8192), desc=f"Downloading {filename}", unit="KB"
                ):
                    if chunk:
                        fh.write(chunk)
        else:
            raise RuntimeError(f"Failed to download {filename}: {r.status_code} {r.text[:200]}")


def upload_file(filename):
    url = NEXTCLOUD_WEBDAV_URL + quote(filename, safe="")
    local_path = os.path.join(LOCAL_DIR, filename)
    print(f"Uploading {local_path} to {url}")
    with open(local_path, "rb") as fh:
        resp = requests.put(url, auth=AUTH, data=fh, timeout=30)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Failed to upload {filename}: {resp.status_code} {resp.text[:500]}")


def sync_nextcloud():
    print("Listing Nextcloud files...")
    nc_files = set(list_nextcloud_files())
    print("Listing local files...")
    local_files = set(list_local_files())

    to_download = nc_files - local_files
    to_upload = local_files - nc_files

    if not to_download and not to_upload:
        print("Folders are already in sync.")
        return

    if to_download:
        print(f"Downloading {len(to_download)} file(s) from Nextcloud...")
        for f in sorted(to_download):
            download_file(f)

    if to_upload:
        print(f"Uploading {len(to_upload)} file(s) to Nextcloud...")
        for f in sorted(to_upload):
            upload_file(f)

    print("Sync complete.")


if __name__ == "__main__":
    # quick sanity checks
    if not os.path.isdir(LOCAL_DIR):
        raise SystemExit(f"Local folder does not exist: {LOCAL_DIR}")
    sync_nextcloud()
