"""Pydantic models for the evidence-snippet pipeline and its LLM judge.

The [`EvidenceSnippetExtractor`][kibad_llm.extractors.evidence_snippets.EvidenceSnippetExtractor]
reads a document chunk by chunk. For each chunk, the model returns a
[`ChunkEvidence`][.ChunkEvidence] object: updated running notes about the whole document and the
findings in the current chunk, each marked by short verbatim anchors. The
[`SnippetJudgeMetric`][kibad_llm.metrics.snippet_judge.SnippetJudgeMetric] uses
[`SnippetJudgeOutput`][.SnippetJudgeOutput] to compare the resulting snippets with gold entries.

Field descriptions are in German, like the prompts of this project. The model is asked to write the
notes in German and the findings in the language of the document.

Classes:
    SectionTypeEnum: Coarse type of the document section a finding stands in.
        (Enum docstrings are German since they are shown to the model as value hints.)
    StudyNotes: Running notes about the whole document, carried from chunk to chunk.
    EvidenceFinding: One finding in a chunk, marked by verbatim anchors.
    ChunkEvidence: Model output for one chunk: updated notes and the findings of the chunk.
    JudgeVerdictEnum: Whether a candidate snippet supports a gold entry.
    ResultAgreementEnum: Whether the result in a candidate agrees with the gold entry.
    SnippetJudgement: Judgement of one candidate against one gold entry.
    SnippetJudgeOutput: Judge output for one gold entry and a batch of candidates.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SectionTypeEnum(str, Enum):
    """Art des Abschnitts, in dem eine Textstelle steht (Tabelle bzw. Bildunterschrift, falls sie dort steht)."""

    TITLE_OR_ABSTRACT = "title_or_abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    OTHER = "other"


class StudyNotes(BaseModel):
    """Laufende Notizen zum gesamten Dokument. Sie werden nach jedem Textausschnitt aktualisiert und an den
    nächsten Textausschnitt weitergegeben."""

    model_config = ConfigDict(extra="forbid")

    document_language: str = Field(
        ...,
        description="Sprache des Dokuments, z.B. 'Englisch' oder 'Deutsch'.",
    )
    study_topic: str = Field(
        ...,
        description="Worum geht es in der Studie? Fragestellung und Untersuchungsgegenstand in 1 bis 3 Sätzen.",
    )
    study_design: str = Field(
        ...,
        description=(
            "Studiendesign: Beobachtung oder Experiment, verglichene Varianten bzw. untersuchte Gradienten, "
            "Behandlungen, Stichprobenumfang."
        ),
    )
    study_area: str = Field(
        ...,
        description="Untersuchungsgebiet und Lebensraum: Ort, Region, Land, Lebensraum- bzw. Bestandestyp.",
    )
    time_period: str = Field(
        ...,
        description="Untersuchungszeitraum bzw. Zeitpunkte der Aufnahmen, falls genannt.",
    )
    organisms: str = Field(
        ...,
        description="Untersuchte Organismen bzw. Artengruppen, mit wissenschaftlichen Namen, falls genannt.",
    )
    variables: str = Field(
        ...,
        description="Gemessene Zielgrößen und erklärende Variablen bzw. Faktoren.",
    )
    current_section: str = Field(
        ...,
        description=(
            "Abschnitt, in dem der aktuelle Textausschnitt endet, als Überschrift oder Abschnittsart (z.B. "
            "'Results > 3.2 Drought response'). Dient der Einordnung des nächsten Textausschnitts."
        ),
    )
    open_points: str = Field(
        ...,
        description=(
            "Hinweise für die folgenden Textausschnitte, z.B. angekündigte, noch nicht berichtete Ergebnisse, "
            "Abkürzungen und ihre Bedeutung, Bezeichnungen von Versuchsvarianten oder Flächen."
        ),
    )


class EvidenceFinding(BaseModel):
    """Ein relevantes Ergebnis im aktuellen Textausschnitt, markiert durch wörtliche Zitate."""

    model_config = ConfigDict(extra="forbid")

    section: str = Field(
        ...,
        description=(
            "Überschrift bzw. Abschnitt, in dem die Textstelle steht (z.B. 'Results > 3.2 Decomposition'). "
            "Enthält der Ausschnitt keine Überschrift, übernimm den Abschnitt aus den bisherigen Notizen."
        ),
    )
    section_type: SectionTypeEnum = Field(
        ...,
        description="Art des Abschnitts, in dem die Textstelle steht.",
    )
    finding: str = Field(
        ...,
        description=(
            "Kurze Zusammenfassung des Ergebnisses in der Sprache des Dokuments: was womit verglichen bzw. "
            "welcher Zusammenhang untersucht wurde und was herauskam (Richtung, Signifikanz)."
        ),
    )
    context: str = Field(
        ...,
        description=(
            "Informationen aus dem übrigen Dokument (z.B. aus den Notizen), die zum Verständnis der Textstelle "
            "nötig sind, aber nicht in den Zitaten stehen, z.B. wofür Abkürzungen oder Varianten stehen. In der "
            "Sprache des Dokuments. Leer lassen, wenn nicht nötig."
        ),
    )
    figure_or_table: str = Field(
        ...,
        description=(
            "Verweis auf die Abbildung oder Tabelle, in der das Ergebnis dargestellt ist (z.B. 'Fig. 3', "
            "'Tab. 2'), sonst leer."
        ),
    )
    anchors: list[str] = Field(
        ...,
        min_length=1,
        max_length=3,
        description=(
            "1 bis 3 wörtliche Zitate aus dem aktuellen Textausschnitt, Zeichen für Zeichen kopiert, in der "
            "Originalsprache. Jedes Zitat ist ein zusammenhängender Satz oder Teilsatz, der das Ergebnis oder "
            "das Untersuchungsdesign belegt."
        ),
    )


class ChunkEvidence(BaseModel):
    """Ergebnis für einen Textausschnitt: aktualisierte Notizen und die relevanten Ergebnisse des Ausschnitts."""

    model_config = ConfigDict(extra="forbid")

    notes: StudyNotes = Field(
        ...,
        description=(
            "Aktualisierte Notizen zum gesamten Dokument: alle bisherigen Informationen, ergänzt um neue "
            "Informationen aus dem aktuellen Textausschnitt. Auf Deutsch; Fachbegriffe und Artnamen wie im Original."
        ),
    )
    findings: list[EvidenceFinding] = Field(
        ...,
        description="Relevante Ergebnisse im aktuellen Textausschnitt; leere Liste, wenn es keine gibt.",
    )


class JudgeVerdictEnum(str, Enum):
    """match: belegt dieselbe Information; partial: belegt sie teilweise; no_match: belegt sie nicht."""

    MATCH = "match"
    PARTIAL = "partial"
    NO_MATCH = "no_match"


class ResultAgreementEnum(str, Enum):
    """agrees: Ergebnis stimmt überein; conflicts: Ergebnis widerspricht; unclear: kein Vergleich möglich."""

    AGREES = "agrees"
    CONFLICTS = "conflicts"
    UNCLEAR = "unclear"


class SnippetJudgement(BaseModel):
    """Bewertung eines Kandidaten im Vergleich zum Gold-Eintrag."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., description="ID des Kandidaten, z.B. 'F3'.")
    rationale: str = Field(
        ...,
        description="Kurze Begründung (1 bis 3 Sätze), warum der Kandidat den Gold-Eintrag belegt oder nicht.",
    )
    verdict: JudgeVerdictEnum = Field(
        ...,
        description="Belegt der Kandidat dieselbe Information wie der Gold-Eintrag?",
    )
    result_agreement: ResultAgreementEnum = Field(
        ...,
        description=(
            "Stimmt das Ergebnis (Richtung bzw. Vorhandensein eines Effekts oder Trends) im Kandidaten mit dem "
            "Gold-Eintrag überein? 'unclear', wenn der Kandidat kein Ergebnis nennt oder nicht passt."
        ),
    )


class SnippetJudgeOutput(BaseModel):
    """Bewertungen aller Kandidaten für einen Gold-Eintrag."""

    model_config = ConfigDict(extra="forbid")

    judgements: list[SnippetJudgement] = Field(
        ...,
        description="Genau eine Bewertung pro Kandidat.",
    )
