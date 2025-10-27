import inspect

from kibad_llm.schema.types import EcosystemStudyFeatures
from kibad_llm.schema.utils import build_schema_description


def test_build_schema_description():
    description = build_schema_description(EcosystemStudyFeatures.model_json_schema())
    expected = inspect.cleandoc(
        """
        Beschreibung: Angaben zu den ökosystembezogenen Studienmerkmalen.
        Feldhinweise und erlaubte Werte (getrennt durch Semikolons):
        - Lebensräume: In welchen Lebensräumen wurde die Studie durchgeführt? Kardinalität: 0..* | Zulässige Werte: Agrar- und Offenland; Binnengewässer und Auen; Boden; Küsten und Küstengewässer; Urbane Räume; Wald
        - Naturgroßräume: In welchen Naturgroßräumen wurde die Studie durchgeführt? Kardinalität: 0..* | Zulässige Werte: Alpen; Alpenvorland; Mittelgebirgsschwelle; Nord- und Ostsee; Norddeutsches Tiefland; Schichtstufenland beidseits des Oberrheingrabens
        - Bundesland: In welchen Bundesländern liegt das betrachtete Ökosystem der Studie? Kardinalität: 0..* | Zulässige Werte: Baden-Württemberg; Bayern; Berlin; Brandenburg; Bremen; Hamburg; Hessen; Mecklenburg-Vorpommern; Niedersachsen; Nordrhein-Westfalen; Rheinland-Pfalz; Saarland; Sachsen; Sachsen-Anhalt; Schleswig-Holstein; Thüringen
        """
    )
    assert description == expected
