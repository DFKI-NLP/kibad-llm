"""One-off script to download open-access PDFs for papers listed in a Zotero CSV export.

Uses the Semantic Scholar (S2) API to resolve open-access PDF URLs from DOIs, paper
titles, or direct Zotero URLs.  Supports three download strategies (``--download-type``):

- ``doi`` (default) – batch-resolves DOIs against S2, then downloads open-access PDFs.
- ``direct`` – downloads the URL provided by Zotero for papers without a DOI.
- ``title`` – resolves paper IDs via S2 title search and then downloads open-access PDFs.

Run with ``uv run -m kibad_llm.data_integration.zotero_download``.  PDFs are saved
using the Zotero ``Key`` field as the filename (``<Key>.pdf``).
"""

DESCRIPTION = """
This script downloads papers using the open-access url from Semantic Scholar API
starting from a Zotero group library exported to CSV.
The script uses three arguments indicating the path to the CSV file with an
exported Zotero group. The script can search the open-access url using the DOI
of the paper, the title or a direct url found in the CSV. The final argument is
the local path where to store the downloaded PDF files.
"""

import argparse
from math import ceil
from pathlib import Path
import time

from loguru import logger
import pandas as pd
import requests
from retry import retry
from tqdm import tqdm

from kibad_llm.config import DATA_DIR, INTERIM_DATA_DIR


def get_s2_data(ids: list[str]) -> dict:
    """Returns a dict with data about a paper from SemanticScholar (S2) API.
    Using DOIs as ID is a very effective way to find the correct paper from S2.

    S2 API call documented here:
        https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/post_graph_get_papers

    Limitations:
        Can only process 500 paper ids at a time.
        Can only return up to 10 MB of data at a time.
        Can only return up to 9999 citations at a time.
        For a list of supported IDs reference the "Details about a paper"
            endpoint.

    Args:
        ids (list[str]): List of paper ids to query SemanticScholar.
            i.e.: ["649def34f8be52c8b66281af98ae884c09aef38b",
            "ARXIV:2106.15928"]

    Returns:
        dict: dict with all requested fields. One item per paper id.
    """
    response = requests.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch",
        params={
            "fields": "referenceCount,citationCount,title,isOpenAccess,openAccessPdf,externalIds"
        },
        json={"ids": ids},
        timeout=60,
    )
    return response.json()


def download_file(
    url: str,
    file_name: str,
    output_dir: Path,
    chunk_size: int = 10 * 1024,
    overwrite: bool = False,
) -> None:
    """Download a file from a given 'url' to a given `output_dir`.

    Args:
        url (str): URL to download.
        file_name (str): Name and extension of the target file.
        output_dir (Path, optional): Path to store the file.
        chunk_size (int, optional): Size of the temporary file to store while
            downloading. Defaults to 10*1024.
        overwrite (bool, optional): Whether or not to overwrite a file with the
            same name. Defaults to False.
    """

    if (output_dir / file_name).exists() and not overwrite:
        return

    try:
        with requests.get(url, stream=True, allow_redirects=True, timeout=60) as response:
            with open(output_dir / file_name, mode="wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    file.write(chunk)
    except Exception:
        logger.exception(f"{url} not responding...")
        time.sleep(5)
        pass


@retry(tries=10, delay=5)
def get_s2_data_by_title(title: str) -> requests.Response:
    """Returns a dict with paperId, title and matchScore.

    Giving the limitations of the API this function uses a

    API request documented in:
        https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_paper_title_search

    Args:
        title (str): Title of the paper or publication.

    Returns:
        requests.Response: The response from the S2 API.
    """
    response = requests.get(
        f"https://api.semanticscholar.org/graph/v1/paper/search/match?query={title}", timeout=60
    )
    return response


def get_paper_ids_by_title(df: pd.DataFrame, paper_ids_file: Path | str) -> Path | str:
    """Query to S2 API to find IDs of papers based on their title.

    Args:
        df (pd.DataFrame): pd.DataFrame with exported Zotero list.
        paper_ids_file (Path | str): Text file to keep state of downloaded
            papers.

    Returns:
        None | Path | str: Path to the `paper_ids_file` that contains ID for S2.
    """
    if not Path(paper_ids_file).exists():
        Path(paper_ids_file).parent.mkdir(exist_ok=True, parents=True)
        with open(paper_ids_file, "a+", encoding="utf-8") as f:
            f.write("Key|paperId|Title|matchScore\n")

    logger.info(f"Papers with S2 IDs will be saved to {paper_ids_file}")
    pbar = tqdm(df.iterrows(), total=df.shape[0])
    for _, row in pbar:
        pbar.set_description(f"{row['Key']}")

        papers = pd.read_csv(paper_ids_file, sep="|")
        papers["Key"].to_list()
        if row["Key"] in papers["Key"].to_list():
            continue

        while True:  # do not try `while True:` at home or without supervision
            response = get_s2_data_by_title(title=row["Title"])
            if response.status_code in [200, 404]:
                break
            time.sleep(5)

        with open(paper_ids_file, "a+", encoding="utf-8") as f:
            if response.status_code == 404 or response.json() == {}:
                f.write(f'{row["Key"]}|||\n')
            else:
                paper_id = response.json().get("data", [])[0].get("paperId", "")
                title = (
                    response.json()
                    .get("data", [])[0]
                    .get("title", "")
                    .replace("\n", "")
                    .replace("|", "")
                )
                match_score = response.json().get("data", [])[0].get("matchScore", "")
                f.write(f'{row["Key"]}|{paper_id}|{title}|{match_score}\n')
        time.sleep(1)
    return paper_ids_file


def get_papers_from_dois(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Download papers based on DOIs. It will query S2 to get the open
    access url for the paper and return a pd.DataFrame with the urls.

    Args:
        df (pd.DataFrame): Exported list from a Zotero group.

    Returns:
        pd.DataFrame: pd.DataFrame with open access url for the papers.
    """
    # Getting DOI codes from the paper list
    dois = df[~pd.isna(df["DOI"])]["DOI"].to_list()

    if verbose:
        logger.info(f"Querying SemanticScholar for paper IDs for {len(dois):,} DOIs...")

    # Querying the S2 API using the DOIs
    data_download = []
    for i in tqdm(range(ceil(len(dois) / 100))):
        start_index = (i) * 100
        end_index = (i + 1) * 100 - 1
        data = get_s2_data(ids=dois[start_index:end_index])

        for j, r in enumerate(data):
            if r:
                data_download.append(
                    (
                        dois[start_index + j],
                        r.get("paperId"),
                        r["externalIds"]["DOI"],
                        r["title"],
                        r["referenceCount"],
                        r["citationCount"],
                        r["isOpenAccess"],
                        r["openAccessPdf"]["url"],
                        r["openAccessPdf"]["status"],
                        r["openAccessPdf"]["license"],
                    )
                )
        time.sleep(1)

    # Dataframe with open access URLs
    df_papers = pd.DataFrame(
        data_download,
        columns=[
            "DOI_Zotero",
            "paperId",
            "DOI_S2",
            "title",
            "referenceCount",
            "citationCount",
            "isOpenAccess",
            "url",
            "status",
            "license",
        ],
    )

    return df_papers


def main(file_path: Path, output_dir: Path, download_type: str = "doi") -> None:
    """This script allows to download papers based on three methods:

    - `doi`: searching ID papers in SemanticScholar using the DOI and then
        downloading the paper using the open access url.
    - `direct`: using the URL provided by Zotero that ends with '.pdf'
    - `title`: searching ID papers in Semantic Scholar using the title of the
        paper and then downloading the paper using the open access url.

    It uses an exported CSV version of any Zotero list.

    Args:
        file_path (Path): Exported CSV from a Zotero list.
        output_dir (Path): Directory to store the downloaded papers.
        download_type (str, optional): Type of download to perform. Options are
            'doi', 'direct' and 'title'. Defaults to 'doi'.
    """

    # Check if the file exists
    if not Path(file_path).is_file():
        logger.info(f"{file_path} doesn't exists")
        return

    # Create output dir in case it doesn't exists
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"{output_dir} created to store the PDFs")

    # Read the zotero library from a CSV
    df_bank = pd.read_csv(
        file_path,
    )

    # Select a few fields from Zotero
    df_bank = df_bank[
        [
            "Key",
            "Item Type",
            "Publication Year",
            "Title",
            "Publication Title",
            "ISBN",
            "ISSN",
            "DOI",
            "Url",
            "Extra",
        ]
    ]

    logger.info(f"{df_bank.shape[0]:,} papers in the Zotero group")

    if download_type == "doi":
        # DOI papers
        df_papers = get_papers_from_dois(df=df_bank)
        df_papers_to_download = df_papers.merge(
            df_bank[["Key", "DOI"]],
            how="left",
            left_on="DOI_Zotero",
            right_on="DOI",
        )

        # Actual download of the papers
        pbar = tqdm(
            df_papers_to_download.iterrows(),
            total=df_papers_to_download.shape[0],
            unit="doi",
        )
        for i, row in pbar:
            pbar.set_description(f'{row["Key"]}')
            if row["isOpenAccess"]:
                download_file(
                    url=row["url"],
                    file_name=row["Key"] + ".pdf",
                    output_dir=output_dir,
                )
    elif download_type == "direct":
        # Direct download
        pbar = tqdm(
            df_bank[pd.isna(df_bank["DOI"])].iterrows(),
            total=df_bank[pd.isna(df_bank["DOI"])].shape[0],
        )
        for i, row in pbar:
            pbar.set_description(f'{row["Key"]}')
            if str(row["Url"]).endswith(".pdf"):
                download_file(
                    url=row["Url"],
                    file_name=row["Key"] + ".pdf",
                    output_dir=output_dir,
                )

    elif download_type == "title":
        # Download papers by title
        zotero_paper_ids = INTERIM_DATA_DIR / "zotero"
        zotero_paper_ids.mkdir(exist_ok=True, parents=True)
        output_file = get_paper_ids_by_title(
            df=df_bank, paper_ids_file=zotero_paper_ids / "papers_id.txt"
        )
        papers = pd.read_csv(output_file, sep="|")
        paper_ids = [x for x in papers["paperId"].to_list() if pd.notna(x)]
        papers_download = []
        for i in tqdm(range(ceil(len(paper_ids) / 100))):
            start_index = (i) * 100
            end_index = (i + 1) * 100 - 1
            data = get_s2_data(ids=paper_ids[start_index:end_index])

            for j, row in enumerate(data):
                if row:
                    papers_download.append(
                        (
                            paper_ids[start_index + j],
                            row.get("paperId"),
                            row.get("externalIds", "").get("DOI", ""),
                            row.get("externalIds", "").get("ArXiv", ""),
                            row["title"],
                            row["referenceCount"],
                            row["citationCount"],
                            row["isOpenAccess"],
                            row["openAccessPdf"]["url"],
                            row["openAccessPdf"]["status"],
                            row["openAccessPdf"]["license"],
                        )
                    )
            time.sleep(1)

        df_papers_from_s2 = pd.DataFrame(
            papers_download,
            columns=[
                "DOI_Zotero",
                "paperId",
                "DOI_S2",
                "ArXiv_S2",
                "title",
                "referenceCount",
                "citationCount",
                "isOpenAccess",
                "url",
                "status",
                "license",
            ],
        )
        df_papers_to_download = papers.merge(df_papers_from_s2, how="left", on="paperId")

        # Actual download
        pbar = tqdm(df_papers_to_download.iterrows(), total=df_papers_to_download.shape[0])
        for i, row in pbar:
            pbar.set_description(f'{row["Key"]}')
            if len(str(row["url"])) > 3:
                download_file(
                    url=row["url"],
                    file_name=row["Key"] + ".pdf",
                    output_dir=output_dir,
                )


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=DESCRIPTION, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--file-path",
        type=Path,
        default=DATA_DIR
        / "external"
        / "zotero"
        / "Faktencheck_Artenvielfalt_Literaturdatenbank.csv",
        help="Path to the exported CSV from a Zotero group.",
    )
    parser.add_argument(
        "--download-type",
        type=str,
        choices=["doi", "direct", "title"],
        default="doi",
        help="Type of download to perform. doi: using the DOI to find the open access url; "
        "direct: using the direct url provided by Zotero; title: using the title to find the open access url.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATA_DIR / "interim" / "zotero_download",
        help="Directory to store the downloaded papers.",
    )
    kwargs = vars(parser.parse_args())
    main(**kwargs)
