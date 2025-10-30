from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    HOCH_ZWISCHEN_UeBERGANGSMOORE = "Hoch-, Zwischen- und Übergangsmoore"
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


class EcosystemStudyFeaturesWithoutCompounds(BaseModel):
    """Angaben zu den ökosystembezogenen Studienmerkmalen."""

    habitat: list[HabitatEnum] = Field(
        default_factory=list,
        alias="Lebensräume",
        description="In welchen Lebensräumen wurde die Studie durchgeführt?",
    )
    natural_region: list[NaturalRegionEnum] = Field(
        default_factory=list,
        alias="Naturgroßräume",
        description="In welchen Naturgroßräumen wurde die Studie durchgeführt?",
    )
    ecosystem_type_term: list[EcosystemTypeTermEnum] = Field(
        default_factory=list,
        alias="Ökosystemtyp",
        description="Welche Ökosystemtypen sind mit der Studie verknüpft?",
    )
    climate: list[ClimateEnum] = Field(
        default_factory=list,
        alias="Klima",
        description="Welche Klimata sind mit der Studie verknüpft?",
    )
    landuse: list[LanduseEnum] = Field(
        default_factory=list,
        alias="Landnutzung",
        description="Welche Arten der Landnutzung wurden in der Studie betrachtet?",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
    )
