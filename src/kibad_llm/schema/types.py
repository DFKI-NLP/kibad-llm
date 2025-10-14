from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class HabitatEnum(str, Enum):
    WALD = "Wald"
    AGRAR_UND_OFFENLAND = "Agrar- und Offenland"
    BINNENGEWAESSER_UND_AUEN = "Binnengewässer und Auen"
    KUESTE_UND_KUUESTENGEWAESSER = "Küste und Küstengewässer"
    URBANE_RAEUME = "Urbane Räume"
    BODEN = "Boden"
    UNBEKANNT = "UNBEKANNT"


class NaturalRegionEnum(str, Enum):
    ALPEN = "Alpen"
    ALPENVORLAND = "Alpenvorland"
    MITTELGEBIRGSSCHWELLE = "Mittelgebirgsschwelle"
    NORDDEUTSCHES_TIEFLAND = "Norddeutsches Tiefland"
    NORD_UND_OSTSEE_ODER_SCHICHTSSTUFENLAND = (
        "Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens"
    )
    UNBEKANNT = "UNBEKANNT"


class EcosystemTypeTermEnum(str, Enum):
    BINNENLAND_NIEDERMOORE_UND_SUEMPFE_GRUENLAND = (
        "Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte"
    )
    BINNENLAND_LAUBMISCH_WAELDER_UND_FORSTE = (
        "Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent)"
    )
    BINNENGEWAESSER_STEHENDE = "Binnengewässer: Stehende Gewässer"
    MEERE_UND_KUESTEN_BENTHAL_DER_NORDSEE = "Meere und Küsten: Benthal der Nordsee"
    UNBEKANNT = "UNBEKANNT"


class LocationFederalStateEnum(str, Enum):
    BADEN_WUERTTEMBERG = "Baden-Württemberg"
    BAYERN = "Bayern"
    BERLIN = "Berlin"
    BRANDENBURG = "Brandenburg"
    BREMEN = "Bremen"
    HAMBURG = "Hamburg"
    HESSEN = "Hessen"
    MECKLENBURG_VORPOMMERN = "Mecklenburg-Vorpommern"
    NIEDERSACHSEN = "Niedersachsen"
    NORDRHEIN_WESTFALEN = "Nordrhein-Westfalen"
    RHEINLAND_PFALZ = "Rheinland-Pfalz"
    SAARLAND = "Saarland"
    SACHSEN = "Sachsen"
    SACHSEN_ANHALT = "Sachsen-Anhalt"
    SCHLESWIG_HOLSTEIN = "Schleswig-Holstein"
    THUERINGEN = "Thüringen"
    UNBEKANNT = "UNBEKANNT"


class EcosystemStudyFeatures(BaseModel):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    habitat: HabitatEnum = Field(
        ...,
        alias="Lebensraum",
        description="In welchem Lebensraum wurde die Studie durchgeführt?",
    )
    natural_region: NaturalRegionEnum = Field(
        ...,
        alias="Naturgroßraum",
        description="In welchem Naturgroßraum wurde die Studie durchgeführt?",
    )
    ecosystem_type_term: EcosystemTypeTermEnum = Field(
        ...,
        alias="Ökosystemtyp",
        description="Welchen Ökosystemtyp hat die Studie betrachtet?",
    )
    location_federal_state: LocationFederalStateEnum = Field(
        ...,
        alias="Bundesland",
        description="In welchem Bundesland liegt das betrachtete Ökosystem der Studie?",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )
