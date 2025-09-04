"""
This script connects to a database, extracts the most important data and its metadata, then
converts the results to JSONL format and writes to a file.
"""

import json
import os
from typing import Any

import argparse
import psycopg2
from dotenv import load_dotenv


FILEPATH: str = "results.jsonl"
QUERY: str = """
WITH document_base AS (
    SELECT 
        b.zot_key,
        b.zot_creator,
        b.zot_date,
        b.zot_item_type,
        b.zot_title,
        b.zot_pub_title,
        b.date_modified,
        b.zot_pages,
        b.zot_version,
        b.zot_html_link,
        b.zot_api_link,
        b.zot_bibtex,
        c.status,
        c.created_at,
        c.updated_at,
        c.zot_created_by,
        c.spacial_resolution,
        c.spacial_extent,
        c.spacial_measurements,
        c.temporal_extent,
        c.temporal_extent_unit,
        c.temporal_resolution,
        c.temporal_measurements,
        c.start_year,
        c.end_year,
        c.bibtex_string,
        c.citation_html,
        c.citation_validated,
        c.bibtex_author,
        c.bibtex_title,
        c.bibtex_year,
        c.bibtex_type,
        vp.name AS project_name,
        vtp.name AS transformation_potential_name
    FROM bib_zotitem b
    LEFT JOIN core_zotaddon c ON b.zot_key = c.zotitem_ptr_id
    LEFT JOIN vocabulary_project vp ON c.project_id = vp.id
    LEFT JOIN vocabulary_transformationpotential vtp ON c.transformation_potential_id = vtp.id
),
document_categories AS (
    SELECT 
        db.*,
        -- Biodiversity levels
        STRING_AGG(DISTINCT vbl.name, '; ') AS biodiversity_levels,
        -- Biodiversity variables
        STRING_AGG(DISTINCT vbv.name, '; ') AS biodiversity_variables,
        -- Climates
        STRING_AGG(DISTINCT vc.name, '; ') AS climates,
        -- Habitats
        STRING_AGG(DISTINCT vh.name, '; ') AS habitats,
        -- Land uses
        STRING_AGG(DISTINCT vlu.name, '; ') AS land_uses,
        -- Locations
        STRING_AGG(DISTINCT vl.name, '; ') AS locations,
        -- Methods
        STRING_AGG(DISTINCT vm.name, '; ') AS methods,
        -- Natural regions
        STRING_AGG(DISTINCT vnr.name, '; ') AS natural_regions,
        -- Study types
        STRING_AGG(DISTINCT vst.name, '; ') AS study_types,
        -- Taxa
        STRING_AGG(DISTINCT vt.german_name, '; ') AS taxa_german,
        STRING_AGG(DISTINCT vt.scientific_name, '; ') AS taxa_scientific
    FROM document_base db
    LEFT JOIN core_zotaddon_biodiversity_levels czbl ON db.zot_key = czbl.zotaddon_id
    LEFT JOIN vocabulary_biodiversitylevel vbl ON czbl.biodiversitylevel_id = vbl.id
    LEFT JOIN core_zotaddon_biodiversity_variables czbv ON db.zot_key = czbv.zotaddon_id
    LEFT JOIN vocabulary_biodiversityvariable vbv ON czbv.biodiversityvariable_id = vbv.id
    LEFT JOIN core_zotaddon_climates czc ON db.zot_key = czc.zotaddon_id
    LEFT JOIN vocabulary_climate vc ON czc.climate_id = vc.id
    LEFT JOIN core_zotaddon_habitats czh ON db.zot_key = czh.zotaddon_id
    LEFT JOIN vocabulary_habitat vh ON czh.habitat_id = vh.id
    LEFT JOIN core_zotaddon_land_uses czlu ON db.zot_key = czlu.zotaddon_id
    LEFT JOIN vocabulary_landuse vlu ON czlu.landuse_id = vlu.id
    LEFT JOIN core_zotaddon_locations czl ON db.zot_key = czl.zotaddon_id
    LEFT JOIN vocabulary_location vl ON czl.location_id = vl.id
    LEFT JOIN core_zotaddon_methods czm ON db.zot_key = czm.zotaddon_id
    LEFT JOIN vocabulary_method vm ON czm.method_id = vm.id
    LEFT JOIN core_zotaddon_natural_regions cznr ON db.zot_key = cznr.zotaddon_id
    LEFT JOIN vocabulary_naturalregion vnr ON cznr.naturalregion_id = vnr.id
    LEFT JOIN core_zotaddon_study_types czst ON db.zot_key = czst.zotaddon_id
    LEFT JOIN vocabulary_studytype vst ON czst.studytype_id = vst.id
    LEFT JOIN core_zotaddon_taxa czt ON db.zot_key = czt.zotaddon_id
    LEFT JOIN vocabulary_taxon vt ON czt.taxon_id = vt.id
    GROUP BY 
        db.zot_key, db.zot_creator, db.zot_date, db.zot_item_type, db.zot_title,
        db.zot_pub_title, db.date_modified, db.zot_pages, db.zot_version,
        db.zot_html_link, db.zot_api_link, db.zot_bibtex, db.status, db.created_at,
        db.updated_at, db.zot_created_by, db.spacial_resolution, db.spacial_extent,
        db.spacial_measurements, db.temporal_extent, db.temporal_extent_unit,
        db.temporal_resolution, db.temporal_measurements, db.start_year, db.end_year,
        db.bibtex_string, db.citation_html, db.citation_validated, db.bibtex_author,
        db.bibtex_title, db.bibtex_year, db.bibtex_type, db.project_name,
        db.transformation_potential_name
)
SELECT * FROM document_categories
ORDER BY zot_key;
"""


def to_jsonl(results: list[tuple], column_names: list[str], filepath: str) -> None:
    """
    Converts query results to JSONL format, then writes to a file.

    Args:
        results (list[tuple]): query results to be converted to JSONL format
        column_names (list[str]): column names to be used as keys
        filepath (str): path to the JSONL file to write
    """
    with open(filepath, "w", encoding="utf-8") as f:
        for result in results:
            row_dict: dict[str, Any] = dict(zip(column_names, result))
            for key, value in row_dict.items():
                if hasattr(value, 'isoformat'):
                    row_dict[key] = value.isoformat()
                elif value is None:
                    row_dict[key] = None
            
            f.write(json.dumps(row_dict, ensure_ascii=False) + "\n")


def main(args: argparse.Namespace) -> None:
    """
    Main function to execute the query and convert the results to JSONL format.

    Args:
        args (argparse.Namespace): command line arguments
    """
    with psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "kibad"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(args.query)
            results: list[tuple] = cursor.fetchall()
            column_names: list[str] = [desc[0] for desc in cursor.description]
            print(f"Found {len(results)} rows with {len(column_names)} columns")
            print(f"Column names: {column_names}")
            to_jsonl(results, column_names, args.filepath)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--filepath", type=str, default=FILEPATH)
    parser.add_argument("--query", type=str, default=QUERY)
    args: argparse.Namespace = parser.parse_args()
    load_dotenv()
    main(args)
