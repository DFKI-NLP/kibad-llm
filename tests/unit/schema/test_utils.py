import inspect

from kibad_llm.schema.utils import build_schema_description

# created via: SCHEMA = kibad_llm.schema.types.EcosystemStudyFeatures.model_json_schema()
SCHEMA = {
    "$defs": {
        "EcosystemTypeTermEnum": {
            "enum": [
                "Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte",
                "Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent)",
                "Binnengewässer: Stehende Gewässer",
                "Meere und Küsten: Benthal der Nordsee",
                "UNBEKANNT",
            ],
            "title": "EcosystemTypeTermEnum",
            "type": "string",
        },
        "HabitatEnum": {
            "enum": [
                "Wald",
                "Agrar- und Offenland",
                "Binnengewässer und Auen",
                "Küste und Küstengewässer",
                "Urbane Räume",
                "Boden",
                "UNBEKANNT",
            ],
            "title": "HabitatEnum",
            "type": "string",
        },
        "LocationFederalStateEnum": {
            "enum": [
                "Baden-Württemberg",
                "Bayern",
                "Berlin",
                "Brandenburg",
                "Bremen",
                "Hamburg",
                "Hessen",
                "Mecklenburg-Vorpommern",
                "Niedersachsen",
                "Nordrhein-Westfalen",
                "Rheinland-Pfalz",
                "Saarland",
                "Sachsen",
                "Sachsen-Anhalt",
                "Schleswig-Holstein",
                "Thüringen",
                "UNBEKANNT",
            ],
            "title": "LocationFederalStateEnum",
            "type": "string",
        },
        "NaturalRegionEnum": {
            "enum": [
                "Alpen",
                "Alpenvorland",
                "Mittelgebirgsschwelle",
                "Norddeutsches Tiefland",
                "Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens",
                "UNBEKANNT",
            ],
            "title": "NaturalRegionEnum",
            "type": "string",
        },
    },
    "additionalProperties": False,
    "description": "Angaben zu den ökosystembezogenen Studienmerkmalen.",
    "properties": {
        "Bundesland": {
            "$ref": "#/$defs/LocationFederalStateEnum",
            "description": "In welchem Bundesland liegt das betrachtete Ökosystem der Studie?",
        },
        "Lebensraum": {
            "$ref": "#/$defs/HabitatEnum",
            "description": "In welchem Lebensraum wurde die Studie durchgeführt?",
        },
        "Naturgroßraum": {
            "$ref": "#/$defs/NaturalRegionEnum",
            "description": "In welchem Naturgroßraum wurde die Studie durchgeführt?",
        },
        "Ökosystemtyp": {
            "$ref": "#/$defs/EcosystemTypeTermEnum",
            "description": "Welchen Ökosystemtyp hat die Studie betrachtet?",
        },
    },
    "required": ["Lebensraum", "Naturgroßraum", "Ökosystemtyp", "Bundesland"],
    "title": "EcosystemStudyFeatures",
    "type": "object",
}


def test_build_schema_description():
    description = build_schema_description(SCHEMA)
    expected = inspect.cleandoc(
        """
        Beschreibung: Angaben zu den ökosystembezogenen Studienmerkmalen.
        Feldhinweise und erlaubte Werte:
        - Bundesland: In welchem Bundesland liegt das betrachtete Ökosystem der Studie? Zulässige Werte: Baden-Württemberg; Bayern; Berlin; Brandenburg; Bremen; Hamburg; Hessen; Mecklenburg-Vorpommern; Niedersachsen; Nordrhein-Westfalen; Rheinland-Pfalz; Saarland; Sachsen; Sachsen-Anhalt; Schleswig-Holstein; Thüringen; UNBEKANNT
        - Lebensraum: In welchem Lebensraum wurde die Studie durchgeführt? Zulässige Werte: Wald; Agrar- und Offenland; Binnengewässer und Auen; Küste und Küstengewässer; Urbane Räume; Boden; UNBEKANNT
        - Naturgroßraum: In welchem Naturgroßraum wurde die Studie durchgeführt? Zulässige Werte: Alpen; Alpenvorland; Mittelgebirgsschwelle; Norddeutsches Tiefland; Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens; UNBEKANNT
        - Ökosystemtyp: Welchen Ökosystemtyp hat die Studie betrachtet? Zulässige Werte: Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte; Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent); Binnengewässer: Stehende Gewässer; Meere und Küsten: Benthal der Nordsee; UNBEKANNT
    """
    )
    assert description == expected
