from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BaseEcosystemStudyFeatures(BaseModel):
    """Basis-Klasse für ökosystembezogene Studienmerkmale."""

    pass


class HabitatEnum(str, Enum):
    AGRAR_UND_OFFENLAND = "Agrar- und Offenland"
    BINNENGEWAESSER_UND_AUEN = "Binnengewässer und Auen"
    BODEN = "Boden"
    KUESTEN_UND_KUESTENGEWAESSER = "Küsten und Küstengewässer"
    URBANE_RAEUME = "Urbane Räume"
    WALD = "Wald"


class NaturalRegionEnum(str, Enum):
    ALPEN = "Alpen"
    ALPENVORLAND = "Alpenvorland"
    MITTELGEBIRGSSCHWELLE = "Mittelgebirgsschwelle"
    NORD_UND_OSTSEE = "Nord- und Ostsee"
    NORDDEUTSCHES_TIEFLAND = "Norddeutsches Tiefland"
    SCHICHTSTUFENLAND_OBERRHEINGRABEN = "Schichtstufenland beidseits des Oberrheingrabens"


# this is not yet used (compounds are not yet implemented)
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


# this is not yet used (compound)
class EcosystemTypeCategoryEnum(str, Enum):
    I_MEERE_UND_KUESTEN = "I Biotoptypengruppen der Meere und Küsten"
    II_BINNENGEWAESSER = "II Biotoptypengruppen der Binnengewässer"
    III_BINNENLAND = "III Terrestrische und semiterrestrische Biotoptypengruppen des Binnenlandes"
    IV_TECHNISCHE = "IV Technische Biotoptypengruppen"
    V_ALPEN = "V Biotoptypengruppen mit Schwerpunkt in den Alpen"
    VI_WEITERE = "VI Weitere"


# this is not yet used (compound)
class EcosystemTypeTermEnum(str, Enum):
    ANTHROPOGENE_ROHBODEN = "Anthropogene Rohbodenstandorte und Ruderalfluren"
    BAUWERKE = "Bauwerke"
    BENTHAL_NORDSEE = "Benthal der Nordsee"
    BENTHAL_OSTSEE = "Benthal der Ostsee"
    FELDGEHOELZE = "Feldgehölze, Gebüsche, Hecken und Gehölzkulturen"
    FELS_STEILKUESTEN = "Fels- und Steilküsten"
    FELSEN_BLOCK_SCHUTTHALDEN = "Felsen, Block- und Schutthalden, Geröllfelder, offene Bereiche mit sandigem oder bindigem Substrat"
    FLIESSENDE_GEWAESSER = "Fließende Gewässer"
    GEBIRGSRASEN = "Gebirgsrasen (subalpine bis alpine Stufe)"
    GRUNDWASSER_HOHLENGEWAESSER = "Grundwasser und Höhlengewässer"
    GRUEN_FREIFLAECHEN = "Grün- und Freiflächen"
    HOCH_ZWISCHEN_UEBERGANGSMOORE = "Hoch-, Zwischen- und Übergangsmoore"
    HOHLEN = "Höhlen (einschließlich Stollen, Brunnenschächte etc.)"
    KLEINE_UNBEFESTIGTE_FREIFLAECHEN = "Kleine, unbefestigte Freiflächen des besiedelten Bereiches"
    KUESTENDUENEN = "Küstendünen"
    LAUB_MISCH_WAELDER = "Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent)"
    NADEL_MISCH_WAELDER = "Nadel(Misch)Wälder und -Forste"
    PELAGIAL_NORDSEE = "Pelagial der Nordsee"
    PELAGIAL_OSTSEE = "Pelagial der Ostsee"
    QUELLEN_KRENAL = "Quellen (inklusive Quellabfluss (Krenal))"
    ROEHRICHTE = "Röhrichte (ohne Brackwasserröhrichte)"
    SALZGRUENLAND_NORDSEEKUESTE = "Salzgrünland der Nordseeküste (Supralitoral)"
    SALZGRUENLAND_BRACKWASSER = (
        "Salzgrünland, Brackwasserröhrichte und -Hochstaudenfluren des Geolitorals der Ostseeküste"
    )
    STEHENDE_GEWAESSER = "Stehende Gewässer"
    SANDE_STRAND = "Sände, Sand-, Geröll- und Blockstrände"
    TROCKENRASEN = "Trockenrasen sowie Grünland trockener bis frischer Standorte"
    VERKEHRSANLAGEN_PLAETZE = "Verkehrsanlagen und Plätze"
    WALD_UFERSAEUME = "Wald- und Ufersäume, Staudenfluren"
    WALDFREIE_NIEDERMOORE = (
        "Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte"
    )
    WALDMAENTEL_VORWAELDER = "Waldmäntel und Vorwälder, spezielle Waldnutzungsformen"
    ZWERGSTRAUCHHEIDEN = "Zwergstrauchheiden"
    AECKER_ACKERBRACHEN = "Äcker und Ackerbrachen"


class ClimateEnum(str, Enum):
    ATLANTISCHES_KLIMA = "Atlantisches Klima"
    GEBIRGSKLIMA = "Gebirgsklima"
    KONTINENTAL = "kontinental"
    MARITIM = "maritim"
    NIEDERSCHLAGSBENACHTEILIGT = "niederschlagsbenachteiligt"
    NIEDERSCHLAGSNORMAL = "niederschlagsnormal"
    NIEDERSCHLAGSBEGUENSTIGT = "niederschlagsbegünstigt"
    SUBKONTINENTAL = "subkontinental"
    SUBMARITIM = "submaritim"


class LanduseEnum(str, Enum):
    BAU = "Bau"
    BERGBAU_UND_STEINBRUCH = "Bergbau und Steinbruch"
    BRACHLIEGENDE_FLAECHEN = "Brachliegende Flächen"
    ENERGIEPRODUKTION = "Energieproduktion"
    ERHOLUNG_FREIZEIT_SPORT = "Erholung, Freizeit, Sport"
    FISCHEREI_UND_AQUAKULTUR = "Fischerei und Aquakultur"
    FORSTWIRTSCHAFT = "Forstwirtschaft"
    HANDELS_FINANZ_BERUFS_UND_INFORMATIONSDIENSTLEISTUNGEN = (
        "Handels-, Finanz-, Berufs- und Informationsdienstleistungen"
    )
    INDUSTRIE_UND_FERTIGUNG = "Industrie und Fertigung"
    LANDWIRTSCHAFT = "Landwirtschaft"
    NATURNAHE_UND_NATUERLICHE_FLAECHEN_DIE_NICHT_GENUTZT_WERDEN = (
        "Naturnahe und natürliche Flächen, die nicht genutzt werden"
    )
    VERKEHR_KOMMUNIKATIONSNETZWERKE_LAGERUNG_SCHUTZWALLE = (
        "Verkehr, Kommunikationsnetzwerke, Lagerung, Schutzwälle"
    )
    WASSER_UND_ABFALLBEHANDLUNG = "Wasser- und Abfallbehandlung"
    WOHNGEBIETE = "Wohngebiete"
    ANDERE_LEISTUNG_DES_PRIMAERSEKTORS = "andere Leistung des Primärsektors"
    OEFFENTLICHE_EINRICHTUNGEN = "Öffentliche Einrichtungen"


class SpatialExtentEnum(str, Enum):
    BUNDESWEIT = "bundesweit"
    GLOBAL = "global"
    KONTINENT = "kontinent"
    LANDSCHAFT = "landschaft"
    PLOT = "plot"
    PUNKT = "punkt"
    REGION = "region"


class SpatialResolutionEnum(str, Enum):
    BUNDESWEIT = "bundesweit"
    GLOBAL = "global"
    KONTINENT = "kontinent"
    LANDSCHAFT = "landschaft"
    PLOT = "plot"
    PUNKT = "punkt"
    REGION = "region"


class TemporalExtentUnit(str, Enum):
    JAHRE = "jahre"
    JAHRZEHNTE = "jahrzehnte"
    MINUTEN = "minuten"
    MONATE = "monate"
    STUNDEN = "stunden"
    TAGE = "tage"
    WOCHEN = "wochen"


class TemporalResolutionEnum(str, Enum):
    JAHRE = "jahre"
    JAHRZEHNTE = "jahrzehnte"
    MINUTEN = "minuten"
    MONATE = "monate"
    STUNDEN = "stunden"
    TAGE = "tage"
    WOCHEN = "wochen"


class MethodEnum(str, Enum):
    CITIZEN_SCIENCE = "Citizen Science"
    EXPERIMENT = "Experiment"
    FELDBEOBACHTUNG = "Feldbeobachtung"
    MODELLIERUNG = "Modellierung"
    REMOTE_SENSING = "Remote Sensing"
    REVIEW = "Review"
    SYNTHESE = "Synthese"
    UMFRAGE = "Umfrage"


class StudyTypeEnum(str, Enum):
    GUTACHTEN = "Gutachten"
    META_STUDIE = "Meta-Studie"
    NICHT_PEER_REVIEWED = "Nicht Peer-Reviewed"
    ORIGINALSTUDIE = "Originalstudie"
    PEER_REVIEWED = "Peer-Reviewed"
    POSITION_PAPER = "Position Paper"
    TEXT_REVIEW = "Text Review"
    VOTE_COUNT = "Vote Count"


class BiodiversityLevelEnum(str, Enum):
    ARTENVIELFALT = "Artenvielfalt"
    FUNKTIONELLE_DIVERSITAET = "Funktionelle Diversität"
    GENETISCHE_DIVERSITAET = "Genetische Diversität"
    HABITATDIVERSITAET = "Habitatdiversität"
    PHYLOGENETISCHE_DIVERSITAET = "Phylogenetische Diversität"
    STRUKTURELLE_DIVERSITAET = "Strukturelle Diversität"
    ZUSAMMENSETZUNG_DER_ARTENGEMEINSCHAFT = "Zusammensetzung der Artengemeinschaft"


class TransformationPotentialEnum(str, Enum):
    LEBENSRAUMSPEZIFISCHER_WANDLUNGSPROZESS = "Lebensraumspezifischer Wandlungsprozess"
    LEBENSRAUMUNABHAENGIGER_WANDLUNGSPROZESS = "Lebensraumunabhängiger Wandlungsprozess"
    LEBENSRAUMUEBERGREIFENDER_WANDLUNGSPROZESS = "Lebensraumübergreifender Wandlungsprozess"


class EcosystemStudyFeaturesWithoutCompounds(BaseEcosystemStudyFeatures):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    habitat: list[HabitatEnum] = Field(
        default_factory=list,
        alias="Lebensräume",
        description="Um welchen der folgenden Lebensräume oder um welche Kombinationen der folgenden Lebensräume geht es in dem Text?",
    )
    natural_region: list[NaturalRegionEnum] = Field(
        default_factory=list,
        alias="Naturgroßräume",
        description="Um welchen der folgenden Naturgroßräume geht es in dem Text?",
    )
    climate: list[ClimateEnum] = Field(
        default_factory=list,
        alias="Klima",
        description="Welche Umschreibung trifft auf das Klima des Untersuchungsgebiets zu?",
    )
    landuse: list[LanduseEnum] = Field(
        default_factory=list,
        alias="Landnutzung",
        description="Welche Landnutzung wird im oder nahe des Untersuchungsgebietes betrieben? In welche der folgenden Kategorien fällt die Nutzung?",
    )
    spatial_extent: SpatialExtentEnum | None = Field(
        default=None,
        alias="Räumliche Ausdehnung",
        description="Wie ist insgesamt die räumliche Ausdehnung der Studie?",
    )
    spatial_resolution: SpatialResolutionEnum | None = Field(
        default=None,
        alias="Räumliche Auflösung",
        description="Mit welcher räumlichen Auflösung wurden die einzelnen Messungen in der Studie durchgeführt?",
    )
    spatial_measurements: int | None = Field(
        default=None,
        alias="Anzahl räumlicher Messungen",
        description="An wie vielen Stellen wurde gemessen?",
    )
    temporal_extent: int | None = Field(
        default=None,
        alias="Zeitraum",
        description="In welchem Zeitraum fanden die Messungen statt?",
    )
    temporal_extent_unit: TemporalExtentUnit | None = Field(
        default=None,
        alias="Zeiteinheit",
        description="In welcher der folgenden Zeiteinheiten ist der Zeitraum angegeben?",
    )
    temporal_resolution: TemporalResolutionEnum | None = Field(
        default=None,
        alias="Zeitliche Auflösung",
        description="Mit welcher zeitlichen Auflösung wurden die einzelnen Messungen in der Studie durchgeführt?",
    )
    temporal_measurements: int | None = Field(
        default=None,
        alias="Anzahl zeitlicher Messungen",
        description="Zu wie vielen unterschiedlichen Zeitpunkten wurde gemessen?",
    )
    start_year: int | None = Field(
        default=None,
        alias="Startjahr",
        description="In welchem Jahr fand die erste Messung statt?",
    )
    end_year: int | None = Field(
        default=None,
        alias="Endjahr",
        description="In welchem Jahr fand die letzte Messung statt?",
    )
    method: list[MethodEnum] = Field(
        default_factory=list,
        alias="Methoden der Datenaufnahme",
        description="Mit welcher/welchen Methode(n) wurden die Daten erhoben?",
    )
    study_type: list[StudyTypeEnum] = Field(
        default_factory=list,
        alias="Studienart",
        description="Um welche Form der wissenschaftlichen Studie handelt es sich?",
    )
    project: str | None = Field(
        default=None,
        alias="Projekt/Programm",
        description="Gehört die Studie zu einem größeren Programm oder Projekt? Wenn ja, zu welchem?",
    )
    biodiversity_level: list[BiodiversityLevelEnum] = Field(
        default_factory=list,
        alias="Biodiversitätsebene",
        description="Auf welche der folgenden Ebenen wird Biodiversität in der Studie gemessen?",
    )
    biodiversity_variable: list[str] = Field(
        default_factory=list,
        alias="Biodiversitätsvariable",
        description="In welchen Variablen wird die Biodiversität gemessen?",
    )
    transformation_potential: list[TransformationPotentialEnum] = Field(
        default_factory=list,
        alias="Transformationspotenzial",
        description="In welche der folgenden Kategorien lässt sich die im Text behandelte Transformation einordnen? ",
    )

    model_config = ConfigDict(
        # validate_by_name=True,
        # use_enum_values=True,
        extra="forbid",
    )


class EcosystemStudyFeaturesSimple(BaseEcosystemStudyFeatures):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    habitat: list[HabitatEnum] = Field(
        default_factory=list,
        alias="Lebensräume",
        description="Um welchen der folgenden Lebensräume oder in welcher Kombination der folgenden Lebensräume geht es in dem Text?",
    )
    natural_region: list[NaturalRegionEnum] = Field(
        default_factory=list,
        alias="Naturgroßräume",
        description="Um welchen der folgenden Naturgroßräume geht es in dem Text?",
    )
    climate: list[ClimateEnum] = Field(
        default_factory=list,
        alias="Klima",
        description="Welche Umschreibung trifft auf das Klima des Untersuchungsgebiets zu?",
    )
    landuse: list[LanduseEnum] = Field(
        default_factory=list,
        alias="Landnutzung",
        description="Welche Landnutzung wird im oder nahe des Untersuchungsgebietes betrieben? In welche der folgenden Kategorien fällt die Nutzung?",
    )

    model_config = ConfigDict(
        # validate_by_name=True,
        # use_enum_values=True,
        extra="forbid",
    )


class EcosystemType(BaseModel):
    """Ökosystemtyp mit Kategorie und Term."""

    category: EcosystemTypeCategoryEnum = Field(
        ..., alias="Kategorie", description="Kategorie des Biotoptyps"
    )
    term: EcosystemTypeTermEnum = Field(..., alias="Term", description="Spezifischer Biotoptyp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )


class Location(BaseModel):
    """Standort mit Bundesland und Name."""

    federal_state: LocationFederalStateEnum = Field(
        ..., alias="Bundesland", description="Bundesland des Standorts"
    )
    name: str = Field(..., alias="Name", description="Name des Standorts")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )


class EcosystemStudyFeaturesCompoundsSimple(BaseEcosystemStudyFeatures):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    ecosystem_type: list[EcosystemType] = Field(
        default_factory=list,
        alias="Ökosystemtypen",
        description="Liste der relevanten Ökosystemtypen",
    )
    location: list[Location] = Field(
        default_factory=list, alias="Standorte", description="Liste der relevanten Standorte"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )
