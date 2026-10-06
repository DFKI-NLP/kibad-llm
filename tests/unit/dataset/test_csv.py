import json

from kibad_llm.dataset.csv import read_grouped_csv_records
from tests import FIXTURE_DATA_ROOT
from tests.conftest import WRITE_FIXTURE_DATA

FIXTURE_DATA_PATH = FIXTURE_DATA_ROOT / "dataset" / "csv"

# this needs to contain at least the following keys: 324V8DKM, 324V8DKM, 324V8DKM
ORGANISM_TREND_DATA_EXTRACT = (
    FIXTURE_DATA_PATH / "Weighted Vote Count Wald Literatur - Sheet1_extract.csv"
)


def test_read_grouped_csv_records_organism_trends_wald_all() -> None:
    result = read_grouped_csv_records(
        str(ORGANISM_TREND_DATA_EXTRACT),
        output_key="organism_trends",
    )
    assert isinstance(result, dict)
    assert len(result) == 6

    key = "324V8DKM"
    data = result[key]

    path_expected = FIXTURE_DATA_PATH / f"{key}.json"

    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    with open(path_expected, encoding="utf-8") as f:
        expected = json.load(f)

    assert data == expected


def test_read_grouped_csv_records_custom_output_key() -> None:
    result = read_grouped_csv_records(
        str(ORGANISM_TREND_DATA_EXTRACT),
        columns=["Hauptgruppe_RoteListen"],
        output_key="ecosystem_service_trends",
    )
    key = "324V8DKM"
    assert list(result[key].keys()) == ["ecosystem_service_trends"]


def test_read_grouped_csv_records_split_columns() -> None:
    result = read_grouped_csv_records(
        str(FIXTURE_DATA_PATH / "ösl_papers_raw_extract.csv"),
        output_key="ecosystem_service_trends",
        columns=["Lebensraum_Gruppiert"],
        split_columns={"Lebensraum_Gruppiert": ", "},
    )
    # "62Y3AKIQ" has a single source row with "Lebensraum_Gruppiert" == "Agrar- und Offenland, Wald",
    # which should be split into two separate entries.
    assert result["62Y3AKIQ"] == {
        "ecosystem_service_trends": [
            {"Lebensraum_Gruppiert": "Agrar- und Offenland"},
            {"Lebensraum_Gruppiert": "Wald"},
        ]
    }
    # a record with a single, non-split value should be unaffected
    assert result["27HEKAH2"] == {
        "ecosystem_service_trends": [{"Lebensraum_Gruppiert": "Agrar- und Offenland"}]
    }


def test_read_grouped_csv_records_organism_trends_wald_selected_columns() -> None:
    result = read_grouped_csv_records(
        str(ORGANISM_TREND_DATA_EXTRACT),
        output_key="organism_trends",
        columns=[
            "Hauptgruppe_RoteListen",
            "Untergruppe_RoteListen",
            "Lebensraum",
            "Antwortvariable",
            "Trend",
        ],
    )
    assert isinstance(result, dict)
    assert len(result) == 6

    key = "324V8DKM"
    data = result[key]
    assert data == {
        "organism_trends": [
            {
                "Antwortvariable": "Artenzahl",
                "Hauptgruppe_RoteListen": "Wirbellose",
                "Lebensraum": "Wald",
                "Trend": "no",
                "Untergruppe_RoteListen": "Arthropoden",
            },
            {
                "Antwortvariable": "Artenzahl",
                "Hauptgruppe_RoteListen": "Wirbellose",
                "Lebensraum": "Wald",
                "Trend": "no",
                "Untergruppe_RoteListen": "Arthropoden",
            },
        ]
    }
