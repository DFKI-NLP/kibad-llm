import inspect

from kibad_llm.schema.types import EcosystemStudyFeatures
from kibad_llm.schema.utils import build_schema_description


def test_build_schema_description():
    description = build_schema_description(EcosystemStudyFeatures.model_json_schema())
    expected = inspect.cleandoc(
        """
        Beschreibung: Angaben zu den ökosystembezogenen Studienmerkmalen.
        Feldhinweise und erlaubte Werte:
        - Lebensräume: In welchen Lebensräumen wurde die Studie durchgeführt? Zulässige Werte: Wald; Agrar- und Offenland; Binnengewässer und Auen; Küste und Küstengewässer; Urbane Räume; Boden
        - Naturgroßräume: In welchen Naturgroßräumen wurde die Studie durchgeführt? Zulässige Werte: Alpen; Alpenvorland; Mittelgebirgsschwelle; Norddeutsches Tiefland; Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens
        - Ökosystemtyp: Welchen Ökosystemtyp hat die Studie betrachtet? Zulässige Werte: Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte; Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent); Binnengewässer: Stehende Gewässer; Meere und Küsten: Benthal der Nordsee; UNBEKANNT
        - Bundesland: In welchem Bundesland liegt das betrachtete Ökosystem der Studie? Zulässige Werte: Baden-Württemberg; Bayern; Berlin; Brandenburg; Bremen; Hamburg; Hessen; Mecklenburg-Vorpommern; Niedersachsen; Nordrhein-Westfalen; Rheinland-Pfalz; Saarland; Sachsen; Sachsen-Anhalt; Schleswig-Holstein; Thüringen; UNBEKANNT
        """
    )
    assert description == expected
