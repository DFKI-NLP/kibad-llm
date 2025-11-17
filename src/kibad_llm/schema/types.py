from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BaseEcosystemStudyFeatures(BaseModel):
    """Basis-Klasse für ökosystembezogene Studienmerkmale."""

    # do not allow extra fields per default
    model_config = ConfigDict(extra="forbid")


class CompoundFeature(BaseModel):
    """Basis-Klasse für komplexe Merkmale mit Unterfeldern."""

    # do not allow extra fields per default
    model_config = ConfigDict(extra="forbid")


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


class EcosystemTypeCategoryEnum(str, Enum):
    I_MEERE_UND_KUESTEN = "I Biotoptypengruppen der Meere und Küsten"
    II_BINNENGEWAESSER = "II Biotoptypengruppen der Binnengewässer"
    III_BINNENLAND = "III Terrestrische und semiterrestrische Biotoptypengruppen des Binnenlandes"
    IV_TECHNISCHE = "IV Technische Biotoptypengruppen"
    V_ALPEN = "V Biotoptypengruppen mit Schwerpunkt in den Alpen"
    VI_WEITERE = "VI Weitere"


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


class EcosystemType(CompoundFeature):
    """Ökosystemtyp mit Kategorie, Name und Beschreibung."""

    category: EcosystemTypeCategoryEnum = Field(
        ..., alias="Kategorie", description="Kategorie des Ökosystemtyps"
    )
    term: EcosystemTypeTermEnum = Field(..., alias="Term", description="Name des Ökosystemtyps")
    # TODO: or is "description" mandatory?
    description: str | None = Field(
        default=None,
        alias="Beschreibung",
        description="Beschreibung des Ökosystemtyps",
    )


class Location(CompoundFeature):
    """Standort mit Land, Bundesland und Ort."""

    country: str | None = Field(
        default=None, alias="Land", description="Land des Studienstandorts"
    )
    federal_state: LocationFederalStateEnum | None = Field(
        default=None,
        alias="Bundesland",
        description="Bundesland des Studienstandorts",
    )
    name: str = Field(
        ...,
        alias="Ort",
        description="Ort (z.B. Stadt, Gemeinde, Region) des Studienstandorts",
    )


class SpeciesGroupEnum(str, Enum):
    AMPHIBIANS_AND_REPTILES = "Amphibien und Reptilien"
    OTHERS = "Andere"
    OTHER_PLANTS = "Andere Pflanzen"
    OTHER_INVERTEBRATES = "Andere Wirbellose"
    ARCHAEA = "Archaeen"
    BACTERIA = "Bakterien"
    FISHES = "Fische"
    LICHENS = "Flechten"
    VASCULAR_PLANTS = "Gefäßpflanzen"
    INSECTS = "Insekten"
    MOSSES = "Moose"
    FUNGI = "Pilze"
    PROTISTS = "Protisten"
    PROTOZOA = "Protozoen"
    MAMMALS = "Säugetiere"
    BIRDS = "Vögel"


class Taxa(CompoundFeature):
    """Art mit wissenschaftlichem und deutschem Namen sowie Gruppierung."""

    # TODO: or is "scientific_name" mandatory?
    scientific_name: str | None = Field(
        default=None,
        alias="Wissenschaftlicher Artenname",
        description="Wissenschaftlicher Name der Art",
    )
    # TODO: or is "german_name" mandatory?
    german_name: str | None = Field(
        default=None,
        alias="Deutscher Artenname",
        description="Deutscher Name der Art",
    )
    # TODO: Should that be added? It is in the data, but not in the Fragenkatalog google table.
    #  If this gets added, remove the entry from metric.ignore_subfields in the evaluate.yaml config!
    # collective_term: bool = Field(
    #    ...,
    #    # not sure about the alias here, made up by auto-complete
    #    alias="Sammelbegriff",
    #    # not sure about the description here, made up by auto-complete
    #    description="Handelt es sich bei dem angegebenen Artnamen um einen Sammelbegriff für mehrere Arten?",
    # )
    species_group: SpeciesGroupEnum = Field(
        ...,
        alias="Artengruppe",
        description="Artengruppe der Art",
    )


class SoilDepthEnum(str, Enum):
    OBERBODEN = "Oberboden"
    STREUSCHICHT = "Streuschicht"
    UNBEKANNT = "Unbekannt"
    UNTERBODEN = "Unterboden"


class SoilNameEnum(str, Enum):
    BERGBAUFLAECHEN = "Bergbauflächen"
    BRAUNE_LOESSBOEDEN = "Braune Lössböden, einschließlich Sandlöss und lössähnliche Sedimente"
    BOEDEN_GESCHIEBELEHM = "Böden aus Geschiebelehm und Geschiebemergel mit sandiger Deckschicht"
    BOEDEN_KALK_MERGEL_DOLIMITGESTEINEN = "Böden aus Kalk-, Mergel- und Dolomitgesteinen"
    BOEDEN_TON_SCHLUFFSCHIEFERN = "Böden aus Ton- und Schluffschiefern"
    BOEDEN_KALKFREIEN_SEDIMENTGESTEINEN = "Böden aus kalkfreien Sedimentgesteinen und Quarziten"
    BOEDEN_SAUREN_MAGMATISCHEN_GESTEINEN = (
        "Böden aus sauren und intermediären magamatischen und metamorphen Gesteinen"
    )
    BOEDEN_FLUSSAUEN = "Böden der Flussauen"
    BOEDEN_NIEDERUNGEN_URSTROMTAELER = "Böden der Niederungen und Urstromtäler"
    GEWAESSERFLAECHEN = "Gewässerflächen"
    HOCH_NIEDERMOORBOEDEN = "Hoch- und Niedermoorböden"
    MARSCHBOEDEN = "Marschböden"
    SCHWARZE_LOESSBOEDEN = "Schwarze Lössböden"
    SIEDLUNGSFLAECHEN = "Siedlungsflächen"
    STAUNASSE_LOESSBOEDEN = "Staunasse Lössböden"
    TROCKENE_SANDBOEDEN = "Trockene Sandböden"
    WATTBOEDEN = "Wattböden"


class Soil(CompoundFeature):
    """Boden mit Kategorie und Tiefe."""

    name: SoilNameEnum = Field(..., alias="Name", description="Name des Bodentyps")
    depth: SoilDepthEnum = Field(..., alias="Tiefe", description="Tiefe des Bodens")


class SuccessEnum(str, Enum):
    JA = "ja"
    NEIN = "nein"
    TEILWEISE = "teilweise"
    UNBEKANNT = "unbekannt"


class ConservationArea(CompoundFeature):
    """Schutzgebiet mit Name, Beschreibung und Erfolg."""

    name: str = Field(
        ...,
        alias="Name",
        description="Name des Schutzgebiets",
    )
    # TODO: or is "description" mandatory?
    description: str | None = Field(
        default=None,
        alias="Beschreibung",
        description="Charakterisierung des Schutzgebiets",
    )
    success: SuccessEnum = Field(
        ...,
        alias="Erfolg",
        description="Hatte das Schutzgebiet einen messbaren Effekt auf die Biodiversität?",
    )


class ManagementMeasure(CompoundFeature):
    """Bewirtschaftungsmaßnahme mit Beschreibung und Erfolg."""

    # TODO: or is "description" optional?
    description: str = Field(
        ...,
        alias="Beschreibung",
        description="Beschreibung der Bewirtschaftungsmaßnahme",
    )
    success: SuccessEnum = Field(
        ...,
        alias="Erfolg",
        description="Hatte die Bewirtschaftung als Maßnahme für die Biodiversität einen messbaren Effekt? ",
    )


class ImpulseMeasure(CompoundFeature):
    """Einmalige Maßnahme mit Beschreibung und Erfolg."""

    # TODO: or is "description" optional?
    description: str = Field(
        ...,
        alias="Beschreibung",
        description="Beschreibung der einmaligen Maßnahme",
    )
    success: SuccessEnum = Field(
        ...,
        alias="Erfolg",
        description="Hatte die einmalige Maßnahme für die Biodiversität einen messbaren Effekt? ",
    )


class DirectDriverEnum(str, Enum):
    ANDERE_DIREKTE_TREIBER = "Andere direkte Treiber"
    DIREKTE_ROSSOURCENTNAHME = "Direkte Ressourcenentnahme"
    INVASIVE_GEBIETSFREMDE_ARTEN = "Invasive gebietsfremde Arten"
    KLIMAWANDEL = "Klimawandel"
    VERSCHMUTZUNG = "Verschmutzung"
    VERANDERTE_LAND_MEERESNUTZUNG = "Veränderte Land-/Meeresnutzung"
    VERANDERUNG_DER_STRUKTUR_DER_LANDSCHAFT = "Veränderung der Struktur der Landschaft"


class IndirectDriverEnum(str, Enum):
    GESELLSCHAFTLICHE_TREIBER = "Gesellschaftliche Treiber"
    POLITISCHE_RECHTLICHE_TREIBER_RECHTLICH_REGULATIV = (
        "Politische und rechtliche Treiber - rechtlich-regulativ"
    )
    POLITISCHE_RECHTLICHE_TREIBER_SOZIAL_INFORMATIONELL = (
        "Politische und rechtliche Treiber - sozial-informationell"
    )
    POLITISCHE_RECHTLICHE_TREIBER_OEKONOMISCH_ANREIZBASIERT = (
        "Politische und rechtliche Treiber - ökonomisch-anreizbasiert"
    )
    WIRTSCHAFTLICHE_TECHNOLOGISCHE_TREIBER = "Wirtschaftliche und technologische Treiber"


class DirectDriver(CompoundFeature):
    """Direkter Treiber mit Kategorie und Details."""

    category: DirectDriverEnum = Field(
        ...,
        alias="Kategorie",
        description="Zu welcher der folgenden Kategorien lässt sich der direkte Treiber zuordnen?",
    )
    # TODO: or is "details" mandatory?
    details: str | None = Field(
        default=None,
        alias="Details",
        description="Details zum direkten Treiber",
    )


class IndirectDriver(CompoundFeature):
    """Indirekter Treiber mit Kategorie und Details."""

    category: IndirectDriverEnum = Field(
        ...,
        alias="Kategorie",
        description="Zu welcher der folgenden Kategorien lässt sich der indirekte Treiber zuordnen?",
    )
    # TODO: or is "details" mandatory?
    details: str | None = Field(
        default=None,
        alias="Details",
        description="Details zum indirekten Treiber",
    )


class EcosystemServiceCategoryEnum(str, Enum):
    KULTURELLE_LEISTUNGEN = "Kulturelle Leistungen"
    REGULIERUNGS_UND_ERHALTUNGSLEISTUNGEN = "Regulierungs- und Erhaltungsleistungen"
    VERSORGUNGSLEISTUNGEN = "Versorgungsleistungen"


class EcosystemServiceTermEnum(str, Enum):
    ES_TERM_1_1_1_1 = "1.1.1.1 Kultivierte Landpflanzen (einschließlich Pilze und Algen), die zu Ernährungszwecken angebaut werden"
    ES_TERM_1_1_1_2 = "1.1.1.2 Fasern und andere Materialien aus kultivierten Landpflanzen, Pilzen, Algen und Bakterien zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_1_3 = "1.1.1.3 Kultivierte Landpflanzen (einschließlich Pilze, Algen), die zur Energiegewinnung angebaut werden"
    ES_TERM_1_1_2_1 = (
        "1.1.2.1 Pflanzen aus In-situ-Aquakultur, die zu Ernährungszwecken angebaut werden"
    )
    ES_TERM_1_1_2_2 = "1.1.2.2 Fasern und andere Materialien aus Pflanzen aus In-situ-Aquakultur zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_2_3 = (
        "1.1.2.3 Pflanzen aus In-situ-Aquakultur, die als Energiequelle angebaut werden"
    )
    ES_TERM_1_1_3_1 = "1.1.3.1 Zu Ernährungszwecken gehaltene Tiere"
    ES_TERM_1_1_3_2 = "1.1.3.2 Fasern und andere Materialien von gehaltenen Tieren zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_3_3 = "1.1.3.3 Tiere, die zur Energiegewinnung gehalten werden (auch mechanisch)"
    ES_TERM_1_1_4_1 = (
        "1.1.4.1 Tiere, die in In-situ-Aquakultur zu Ernährungszwecken aufgezogen werden"
    )
    ES_TERM_1_1_4_2 = "1.1.4.2 Fasern und andere Materialien von Tieren, die in In-situ-Aquakultur gezüchtet werden, zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_4_3 = "1.1.4.3 In-situ-Aquakultur aufgezogene Tiere als Energiequelle"
    ES_TERM_1_1_5_1 = "1.1.5.1 Wildpflanzen (Land- und Wasserpflanzen, einschließlich Pilze und Algen), die zur Ernährung genutzt werden"
    ES_TERM_1_1_5_2 = "1.1.5.2 Fasern und andere Materialien von Wildpflanzen zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_5_3 = "1.1.5.3 Wildpflanzen (Land- und Wasserpflanzen, einschließlich Pilze und Algen), die als Energiequelle genutzt werden"
    ES_TERM_1_1_6_1 = (
        "1.1.6.1 Wildtiere (Land- und Wassertiere), die zu Ernährungszwecken verwendet werden"
    )
    ES_TERM_1_1_6_2 = "1.1.6.2 Fasern und andere Materialien von Wildtieren zur direkten Verwendung oder Verarbeitung (ausgenommen genetisches Material)"
    ES_TERM_1_1_6_3 = (
        "1.1.6.3 Wildtiere (Land- und Wassertiere), die als Energiequelle genutzt werden"
    )
    ES_TERM_1_2_1_1 = "1.2.1.1 Saatgut, Sporen und anderes Pflanzenmaterial, das zur Erhaltung oder zum Aufbau einer Population gesammelt wird"
    ES_TERM_1_2_1_2 = "1.2.1.2 Höhere und niedere Pflanzen (ganze Organismen), die zur Züchtung neuer Stämme oder Sorten verwendet werden"
    ES_TERM_1_2_1_3 = "1.2.1.3 Einzelne Gene, die aus höheren und niederen Pflanzen für den Entwurf und die Konstruktion neuer biologischer Einheiten gewonnen werden"
    ES_TERM_1_2_2_1 = "1.2.2.1 Tiermaterial, das für die Erhaltung oder den Aufbau einer Population gesammelt wurde"
    ES_TERM_1_2_2_2 = "1.2.2.2 Wildtiere (ganze Organismen), die zur Züchtung neuer Stämme oder Sorten verwendet werden"
    ES_TERM_1_2_2_3 = "1.2.2.3 Einzelne Gene, die aus Organismen extrahiert werden, um neue biologische Einheiten zu entwerfen und zu konstruieren"
    # Note: Here is a typo in the original data ("Versorungsleistungen" missing a "g")
    ES_TERM_1_3_X_X = "1.3.X.X Andere (Versorungsleistungen aus biotischen Quellen)"
    ES_TERM_2_1_1_1 = "2.1.1.1 Biosanierung durch Mikroorganismen, Algen, Pflanzen und Tiere"
    ES_TERM_2_1_1_2 = "2.1.1.2 Filtration/Sequestrierung/Speicherung/Akkumulation durch Mikroorganismen, Algen, Pflanzen und Tiere"
    ES_TERM_2_1_2_1 = "2.1.2.1 Reduktion von Gerüchen"
    ES_TERM_2_1_2_2 = "2.1.2.2 Reduktion von Lärm"
    ES_TERM_2_1_2_3 = "2.1.2.3 Sichtschutz (Visual Screening)"
    ES_TERM_2_2_1_1 = "2.2.1.1 Kontrolle der Erosionsraten"
    ES_TERM_2_2_1_2 = "2.2.1.2 Pufferung und Abschwächung von Massenbewegungen"
    ES_TERM_2_2_1_3 = "2.2.1.3 Wasserkreislauf und Wasserflussregulierung (einschließlich Hochwasserschutz und Küstenschutz)"
    ES_TERM_2_2_1_4 = "2.2.1.4 Windschutz"
    ES_TERM_2_2_1_5 = "2.2.1.5 Feuerschutz"
    ES_TERM_2_2_2_1 = "2.2.2.1 Bestäubung (oder 'Gameten'-Ausbreitung in einem marinen Kontext)"
    ES_TERM_2_2_2_2 = "2.2.2.2 Ausbreitung von Saatgut"
    ES_TERM_2_2_2_3 = "2.2.2.3 Aufrechterhaltung von Aufwuchspopulationen und Lebensräumen (einschließlich Schutz des Genpools)"
    ES_TERM_2_2_3_1 = "2.2.3.1 Schädlingsbekämpfung (einschließlich invasiver Arten)"
    ES_TERM_2_2_3_2 = "2.2.3.2 Krankheitsbekämpfung"
    ES_TERM_2_2_4_1 = "2.2.4.1 Verwitterungsprozesse und ihre Auswirkungen auf die Bodenqualität"
    ES_TERM_2_2_4_2 = (
        "2.2.4.2 Zersetzungs- und Fixierungsprozesse und ihre Auswirkungen auf die Bodenqualität"
    )
    ES_TERM_2_2_5_1 = (
        "2.2.5.1 Regulierung des chemischen Zustands von Süßgewässern durch lebende Prozesse"
    )
    ES_TERM_2_2_5_2 = (
        "2.2.5.2 Regulierung des chemischen Zustands von Salzwasser durch lebende Prozesse"
    )
    ES_TERM_2_2_6_1 = (
        "2.2.6.1 Regulierung der chemischen Zusammensetzung der Atmosphäre und der Ozeane"
    )
    ES_TERM_2_2_6_2 = "2.2.6.2 Regulierung von Temperatur und Feuchtigkeit, einschließlich Belüftung und Transpiration"
    ES_TERM_2_3_X_X = "2.3.X.X Andere"
    ES_TERM_3_1_1_1 = "3.1.1.1 Merkmale lebender Systeme, die durch aktive oder immersive Interaktionen Aktivitäten ermöglichen, die der Gesundheit, der Erholung oder dem Vergnügen dienen"
    ES_TERM_3_1_1_2 = "3.1.1.2 Merkmale lebender Systeme, die Aktivitäten zur Förderung von Gesundheit, Erholung oder Vergnügen durch passive oder beobachtende Interaktionen ermöglichen"
    ES_TERM_3_1_2_1 = "3.1.2.1 Merkmale lebender Systeme, die eine wissenschaftliche Untersuchung oder die Schaffung von traditionellem ökologischem Wissen ermöglichen"
    ES_TERM_3_1_2_2 = "3.1.2.2 Merkmale lebender Systeme, die Bildung und Ausbildung ermöglichen"
    ES_TERM_3_1_2_3 = "3.1.2.3 Merkmale lebender Systeme, die in Bezug auf die Kultur und Kulturerbe eine Rolle spielen"
    ES_TERM_3_1_2_4 = "3.1.2.4 Merkmale lebender Systeme, die ästhetische Erfahrungen ermöglichen"
    ES_TERM_3_2_1_1 = (
        "3.2.1.1 Elemente von lebenden Systemen, die eine symbolische Bedeutung haben"
    )
    ES_TERM_3_2_1_2 = (
        "3.2.1.2 Elemente von lebenden Systemen, die eine heilige oder religiöse Bedeutung haben"
    )
    ES_TERM_3_2_1_3 = (
        "3.2.1.3 Elemente lebender Systeme, die zur Unterhaltung oder Darstellung verwendet werden"
    )
    ES_TERM_3_2_2_1 = (
        "3.2.2.1 Merkmale oder Eigenschaften von lebenden Systemen, die einen Existenzwert haben"
    )
    ES_TERM_3_2_2_2 = "3.2.2.2 Merkmale oder Eigenschaften von lebenden Systemen, die einen Options- oder Vermächtniswert haben"
    ES_TERM_3_3_X_X = "3.3.X.X Andere"
    ES_TERM_4_2_1_1 = "4.2.1.1 Oberflächenwasser als Trinkwasser"
    ES_TERM_4_2_1_2 = (
        "4.2.1.2 Oberflächenwasser, das als Material verwendet wird (nicht zu Trinkzwecken)"
    )
    ES_TERM_4_2_1_3 = "4.2.1.3 Oberflächenwasser aus Süßwasser, das als Energiequelle genutzt wird"
    ES_TERM_4_2_1_4 = "4.2.1.4 Küsten- und Meereswasser, das als Energiequelle genutzt wird"
    ES_TERM_4_2_2_1 = "4.2.2.1 Grundwasser (und Untergrundwasser) als Trinkwasser"
    ES_TERM_4_2_2_2 = "4.2.2.2 Grundwasser (und Oberflächenwasser), das als Material verwendet wird (nicht zu Trinkzwecken)"
    ES_TERM_4_2_2_3 = (
        "4.2.2.3 Grundwasser (und Untergrundwasser), das als Energiequelle genutzt wird"
    )
    ES_TERM_4_2_X_X = "4.2.X.X Andere (Ökosystemleistungen des Wassers)"


class EcosystemService(CompoundFeature):
    """Ökosystemdienstleistung mit Kategorie, Term und Details."""

    # TODO: or is "category" optional?
    category: EcosystemServiceCategoryEnum = Field(
        ...,
        alias="Kategorie",
        description="In welche der folgenden Kategorien lässt sich die im Text behandelte Ökosystemleistung einordnen?",
    )
    # TODO: or is "term" optional?
    term: EcosystemServiceTermEnum = Field(
        ...,
        alias="Term",
        description="Welche konkrete Ökosystemleistung wurde untersucht?",
    )
    # TODO: or is "details" mandatory?
    details: str | None = Field(
        default=None,
        alias="Details",
        description="Details zum direkten Treiber",
    )


class EcosystemStudyFeaturesCompoundsSimple(BaseEcosystemStudyFeatures):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    ecosystem_type: list[EcosystemType] = Field(
        default_factory=list,
        alias="Ökosystemtypen",
        description="Welche Ökosystemtypen werden in der Studie untersucht?",
    )
    location: list[Location] = Field(
        default_factory=list,
        alias="Standorte",
        description="Welche Standorte werden in der Studie untersucht?",
    )


class EcosystemStudyFeaturesCompoundsOnly(BaseEcosystemStudyFeatures):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    ecosystem_type: list[EcosystemType] = Field(
        default_factory=list,
        alias="Ökosystemtypen",
        description="Welche Ökosystemtypen werden in der Studie untersucht?",
    )
    location: list[Location] = Field(
        default_factory=list,
        alias="Standorte",
        description="Welche Standorte werden in der Studie untersucht?",
    )
    taxa: list[Taxa] = Field(
        default_factory=list,
        alias="Arten",
        description="Welche Arten werden in der Studie untersucht?",
    )
    soil: list[Soil] = Field(
        default_factory=list,
        alias="Böden",
        description="Welche Bodentypen werden in der Studie untersucht?",
    )
    conservation_area: list[ConservationArea] = Field(
        default_factory=list,
        alias="Schutzgebiete",
        description="Welche Schutzgebiete werden in der Studie untersucht?",
    )
    management_measure: list[ManagementMeasure] = Field(
        default_factory=list,
        alias="Bewirtschaftungsmaßnahmen",
        description="Wurden Formen der Bewirtschaftung als Maßnahmen für die Biodiversität untersucht?",
    )
    impulse_measure: list[ImpulseMeasure] = Field(
        default_factory=list,
        alias="Einmalige Maßnahmen",
        description="Wurden einmalige Maßnahmen für die Biodiversität untersucht?",
    )
    direct_driver: list[DirectDriver] = Field(
        default_factory=list,
        alias="Direkte Treiber",
        description="Welche Vorgänge mit direktem Einfluss auf Biodiversität wurden untersucht?",
    )
    indirect_driver: list[IndirectDriver] = Field(
        default_factory=list,
        alias="Indirekte Treiber",
        description="Welche Vorgänge mit indirektem Einfluss auf Biodiversität wurden untersucht?",
    )
    ecosystem_service: list[EcosystemService] = Field(
        default_factory=list,
        alias="Ökosystemleistungen",
        description="Welche Ökosystemleistungen wurden in der Studie untersucht?",
    )
