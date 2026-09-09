import json

from kibad_llm.config import PROJ_ROOT
from kibad_llm.dataset.csv import read_grouped_csv_records
from tests.conftest import WRITE_FIXTURE_DATA


def test_read_grouped_csv_records_organism_trends_wald_all() -> None:
    result = read_grouped_csv_records(
        "data/external/organism_trends/Weighted Vote Count Wald Literatur - Sheet1.csv",
        output_key="organism_trends",
    )
    assert isinstance(result, dict)
    assert len(result) == 172

    key = "324V8DKM"
    data = result[key]

    path_expected = PROJ_ROOT / "tests" / "fixtures" / "organism_trends" / f"{key}.json"

    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    with open(path_expected, encoding="utf-8") as f:
        expected = json.load(f)

    assert data == expected


def test_read_grouped_csv_records_custom_output_key() -> None:
    result = read_grouped_csv_records(
        "data/external/organism_trends/Weighted Vote Count Wald Literatur - Sheet1.csv",
        columns=["Hauptgruppe_RoteListen"],
        output_key="ecosystem_service_trends",
    )
    key = "324V8DKM"
    assert list(result[key].keys()) == ["ecosystem_service_trends"]


def test_read_grouped_csv_records_organism_trends_wald_selected_columns() -> None:
    result = read_grouped_csv_records(
        "data/external/organism_trends/Weighted Vote Count Wald Literatur - Sheet1.csv",
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
    assert len(result) == 172

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
