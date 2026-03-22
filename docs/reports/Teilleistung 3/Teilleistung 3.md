# Dokumentation Teilleistung 3 “LLM-basierte Content-Extraktion”

Kontinuierliche KI-basierte Biodiversitäts-Assessments für Deutschland (KIBA-D)

202501 KIBA-D
Version: 1.0
Status: final

**DFKI GmbH** Tel: +49 631 20575 0
Trippstadter Straße 122 Email: info@dfki.de
67663 Kaiserslautern Web: www.dfki.de

**iDiv e.V.** Tel: +49 341 9733105
Puschstraße 4 Email: info@idiv.de
04103 Leipzig Web: www.idiv.de

-----

## Inhaltsverzeichnis

1.  Einleitung
    1.1. Überblick AP 1
    1.2. Ziele Teilleistung 3
    1.3. Struktur des Dokuments
2.  LLM-basierte Contentextraktion
    2.1. Implementation
    2.2. Eingesetzte Software
    2.3. IT Infrastruktur / Ressourcenbedarf
3.  Aufbereitung von Testdatensätzen
4.  Bereitgestellte Daten für TL 4

-----

# 1. Einleitung

## 1.1. Überblick AP 1

Das Projekt KIBA-D "Kontinuierliche KI-basierte Biodiversitäts-Assessments für Deutschland" hat sich die Aufgabe gesetzt, die Grundlagen für ein KI-basiertes System zu entwickeln, das auf Basis des Korpus des Faktenchecks Artenvielfalt KI-Modelle trainiert, die relevante Daten zu Biodiversitätstrends, zu kausalen Zusammenhängen, zu Bewertungen der Wirksamkeit von Instrumenten und Maßnahmen aus Textinformation extrahieren und - in einem zusätzlichen Schritt - auch analysieren können[cite: 32]. Ziel des ersten Arbeitspakets AP1 ist dabei die Etablierung eines Workflows zur KI-gestützten Extraktion biodiversitätsrelevanter Informationen aus Textquellen[cite: 32]. Der Workflow soll aus drei Elementen bestehen: (1) Die Erstellung eines digitalen Referenz-Korpus aus möglichst allen Dokumenten des Faktencheck Artenvielfalt, (2) die Auswahl und das Training von LLM-basierten Modellen mithilfe dieses Korpus und (3) das Rekreieren der “Annotationen” des Faktenchecks zu Testzwecken mit anschließender Validierung und Sensitivitätsanalyse[cite: 32].

Dieser Zwischenbericht stellt einen vorläufigen Projektbericht für die Teilleistung 3 in AP1 dar und dient zur Dokumentation des Projektstands und zur Abnahme der Teilleistung[cite: 32].

## 1.2. Ziele Teilleistung 3

Ziel von Teilleistung 3 ist die Implementierung des Proof-of-Concept Workflows aus Teilleistung 2[cite: 32]. Sie dient dazu, die Umsetzbarkeit des konzipierten Workflows zu validieren[cite: 32]. Die Implementierung fokussiert auf die Extraktion der wichtigsten Annotationen der Originalpublikationen, wie z.B. Artengruppe, Lebensraum, Biodiversitätsebene, Trends, etc., um aggregierende Analysen u.a. für die Weighted Vote Counts zu ermöglichen[cite: 32]. Die Ergebnisse der Content-Extraktion werden in einem geeigneten Format für die Validierung und die Sensitivitätsanalysen zur Verfügung gestellt[cite: 32]. Konkret umgesetzt wurden, in Absprache mit der FEdA und den Expert\*innen des iDiv, die Workflows für Anwendungsfälle 1 & 2 zur Rekreierung der Annotationen der Literaturdatenbank des Faktencheck Artenvielfalts und zur Extraktion der Trenddaten für die Weighted Vote Counts / Sensitivitätsanalysen (Anwendungsfälle 5 & 8)[cite: 32].

## 1.3. Struktur des Dokuments

Das folgende Kapitel 2 beschreibt die Implementierung der Workflows[cite: 32]. Anschließend geben wir noch einen kurzen Überblick über die Aufbereitung der Testdatensätze sowie die für die in TL4 anschließenden Analysen bereitgestellten Modell-Outputs[cite: 32].

# 2. LLM-basierte Contentextraktion

## 2.1. Implementation

KI-Workflows für ausgewählte Content-Extraktionsaufgaben: Implementierungen der KI-Extraktionsworkflows für ausgewählte Inhalte inkl. technischer Tests und Dokumentation

  * Extraktions-Pipeline (Workflow):
      * Voraussetzungen:
          * Definition des erwarteten Datenformats als PyDantic Daten-Model
          * Manuell definierter Prompt-Text mit Aufgabenstellung, Persona, etc.
          * Eingabe-PDFs
              * Verschiedene Dokumentarten (später: ggf. docx-2-text etc)
              * Optional: OCR
              * Parallelisierbar (Batchverarbeitung)
      * PDF-zu-Markdown (Text) Konvertierung via PyMuPDF4LLM
      * Automatische JSON Schema Erstellung basierend auf dem PyDantic Model
      * Automatische Anpassung des Schemas für Evidenz-Anker-Generierung (exakte Zitate, welche die extrahierten Informationen belegen sollen)
      * Automatische Erstellung einer textuellen Beschreibung des geforderten Datenformats an Hand des JSON Schemas
      * Schemata für unterschiedliche Informationsbedarfe (siehe slide [https://docs.google.com/presentation/d/12t1E1N0rf0CDu8JSRb-6pScbJYjLfkY8/edit?slide=id.g3c89e74f00f\_0\_141\#slide=id.g3c89e74f00f\_0\_141](https://docs.google.com/presentation/d/12t1E1N0rf0CDu8JSRb-6pScbJYjLfkY8/edit?slide=id.g3c89e74f00f_0_141#slide=id.g3c89e74f00f_0_141) )
          * Full
          * Kern
          * OrganismTrend
      * LLM-basierte Text-Generierung
          * Prompt:
              * manuell definierter Prompt-Text / Konfigurierbare Prompttemplates
              *   + Datenformat-Beschreibung
              *   + Dokument-Text (im Markdown Format)
              * 3 verschiedene “Basisprompts” (auf Basis der Annotationsrichtlinien bzw. Textvorschlägen von iDiv)
                  * Mit Evidenz
                  * Mit Persona
                  * Ohne Feld- bzw. Typ-Beschreibungen
          * via Llama-Index für kommerzielle Modelle und vLLM für selbst-gehostete Modelle
          * Variable LLMs
              * mit Hilfe von JSON Schema basiertem Guided Decoding um LLM-Antworten im gewünschten Datenformat zu erhalten ((Strukturiertes Output & Guided Decoding))
              * wenn vom LLM unterstützt, zusätzlich mit Reasoning-Traces
      * Evidenz-Snippet Erstellung basierend auf generierten Evidenz-Ankern: Falls ein Anker im Eingabe-Text gefunden werden kann, erweitere ihn um einen Kontext von k Wörtern
      * (Optional) Ergebnis-Aggregation über mehrere LLM-Antworten
          * für Ensemble (via majority-voting) um stabilere Ergebnisse zu erhalten
          * bei Zerlegung des Extraktions-Problems in mehrere Teilschritte (Komplexitätsreduktion - kleinere Prompts machen die Extraktionsaufgabe für das LLM leichter); hierzu muss das PyDantic Daten-Modell vorab (manuell) in mehrere Modelle aufgeteilt werden
              * als unabhängige LLM-Anfragen oder als konditionaler Workflow möglich (d.h. die zweite LLM-Anfrage bekommt das Ergebnis der ersten als Kontext etc.)
          * bei Dokument-Chunking: wenn Eingabe-Dokumente nicht komplett in den Eingabe-Kontext der LLMs passen oder um die Performanz zu verbessern (Komplexitätsreduktion, siehe oben)
      * Finales JSON
          * zusätzliche Informationen:
              * unverarbeitete LLM-Antworten
              * Reasoning-Traces, wenn das LLM Reasoning in “\<think\>”-Tags unterstützt
              * Evidenz-Snippets mit Position im Originaltext, insofern Evidenzsnippets durch das LLM extrahiert wurden und ein Matching auf den Originaltext erfolgreich war
              * Fehler, Messages
      * Ausblick: Konditionale / “orchestrierte” Promptflows (oder ggf. sogar “agentisch”)
  * Generell:
      * Hydra für Experiment-Orchestrierung
      * pre-commit + pytest
      * GitHub CI
  * evaluate.py - Implementierung der Evaluation
      * f1/p/r pro Klasse und Averages
      * flache vs komplexe eval
      * fehler, confusion matrices

## 2.2. Eingesetzte Software

Tabelle mit OSS + Lizenz? siehe schon TL 2 Abschnitt

## 2.3. IT Infrastruktur / Ressourcenbedarf

self-hosted: eine GPU pro Run (welche Modelle?), Zeit?

OpenAI API: Kosten (in €) pro Run?

vielleicht hier nur eine knappe Beschreibung, was bisher so verwendet wurde bzw. wie lange es dauert

  * GPUs: H100 / A100 GPUs
  * grobe Dauer, für 100 Test-PDFs ca X Minuten für Inferenz

# 3. Aufbereitung von Testdatensätzen

Für die zwei Extraktionsaufgaben - Literaturdatenbank bzw. Weighted Vote Count Trenderkennung - wurden die bereitgestellten Daten (siehe TL1) genutzt, um Trainings- und Testdatensätze zu erstellen.

Die Annotationen der Literaturdatenbank wurden mit einem Pythonskript[1] aus dem SQL-Dump der Literaturdatenbank in eine Datei im JSON-Line-Format - also eine als JSON formatierte Zeile pro Dokument - überführt. Das JSON-Schema für die Datei wurde in Absprache mit den iDiv-Expert\*innen entworfen und orientiert sich an der Tabellenstruktur der Datenbank. Es enthält alle relevanten Annotationen und Metadaten des jeweiligen PDFs. Komplexe Typen mit Subfeldern (z.B. Ökosystemtyp) werden dabei als Dictionary von Key-Value-Paaren gespeichert, alle anderen Informationen als Einzelwerte bzw. Listen. Für eine konsistente Repräsentation wurden Felder im Vergleich zur Datenbank teilweise umbenannt und Schreibweisen normalisiert. Dies erleichtert die Verwendung im Prompt bzw. im Pydantic-Datenschema des Modells.

Für das Einlesen der Trenddatensätze, die in Form von Exceltabellen vorliegen, wurde durch das DFKI ein CSV-Reader[2] implementiert, der direkt die Daten in eine analoge JSON-Schemastruktur überführt (ohne den Zwischenschritt der Konvertierung in eine JSONL-Datei). Die folgende Abbildung zeigt einen Ausschnitt der konvertierten Testdaten für die Literaturdatenbankeinträge im JSONL-Format. Die Testdaten für die Organismentrends bzw. ÖSL-Trends sehen ähnlich aus, allerdings mit anderen Feldern pro Trend (entsprechend den in den Exceltabellen definierten Attributen / Spalten).

Abbildung X Testdatenformat für Literaturdatenbank 

Literaturdatenbank: Alle Einträge der Literaturdatenbank, für die ein PDF vorhanden ist, wurden zur Erstellung eines Train / Dev / Test-Splits für die Optimierung bzw. Evaluation der Workflows genutzt. Annotierte Dokumente wurden zufällig den 3 Splits zugeordnet. Nicht annotierte Dokumente bilden einen separaten Split. Tabelle X zeigt die Verteilung auf die Splits.

Tabelle X Verteilung der Dokumente auf die Splits 

| Train | Validation | Test | Unlabeled | Total |
| :-: | :-: | :-: | :-: | :-: |
| 900 | 900 | 500 | 1.609 | 3.917 |

Für die initiale Entwicklung und erste Experimente wurde zusätzlich ein kleineres Testset von 100 Dokumenten erstellt. Dokumente wurden dabei zufällig ausgewählt, es wurde jedoch darauf geachtet, dass die Verteilung über Dokumentarten (wiss. Artikel, Buch, Bericht; Doktorarbeit, Präsentation) in etwa repräsentativ für den Gesamtkorpus war. Die Auswahl für das Testset ist hier[3] dokumentiert.

Trenderkennung / Weighted Vote Counts: Für die Trenderkennung beschränkten wir uns zunächst auf die Erstellung eines Testsets für die organismenbezogenen Trends. Auf Vorschlag von iDiv wurden dafür die Literatur des Kapitels “Wald” des Faktencheck Artenvielfalt sowie alle weiteren Publikationen aus den Weighted Vote Count Analysen zum Lebensraum Wald verwendet, weil in diesem Lebensraum sowohl positive als auch negative Trends beobachtet wurden. Insgesamt besteht das Testset aus 409 Publikationen, für die PDFs verfügbar sind. Von diesen 409 sind 172 mit Trendinformationen annotiert (insgesamt 312 Trendaussagen), die restlichen enthalten keine Trends. Die Verteilung der Trends ist positiv: 110, negativ zu positiv: 30, kein Trend: 73, negativ: 85, positiv zu negativ: 14.

Weitere Testdatensätze, z.B. für die ÖSL-Trends bzw. für weitere LLM-Aufgaben, werden im Verlauf des Projekts nach Bedarf erstellt.

# 4. Bereitgestellte Daten für TL 4

Für die Analysen in TL4 haben wir eine Reihe von Experimenten mit verschiedenen Modellen, Prompts, Hyperparametern, und anderen Änderungen durchgeführt (für Details siehe TL4). Pro Durchlauf, also einer konkreten Konfiguration eines Experiments, werden sowohl Modellausgaben als auch Loggingdaten (während Inferenz und während Evaluation) gespeichert. Die Modellausgaben werden in dem in Abschnitt 2.1 beschriebenen, “finalen” JSON-Line-Format abgelegt. Die Inhalte der “structured” bzw. “structured\_with\_metadata” Elemente entsprechen dabei im Wesentlichen dem Format der aufbereiteten Testdaten, bis auf die zusätzlichen Informationen wie Evidenzsnippets. Die Loggingdaten werden mit dem Standard “logging”-Paket von Python erzeugt. Die Daten werden in folgender Struktur abgelegt: 

Abbildung X Struktur der bereitgestellten Experimentdaten 

Der Top-Level-Ordner enthält separate Unterordner für die logs/ und predictions/. Predictions werden über ein benanntes Experiment gruppiert und jeder Run enthält einen Zeitstempel. Die Logdateien speichern im Unterordner “.hydra” die Metadaten zu den einzelnen Runs, insbesondere die exakte Hydra-Konfiguration (config.yaml), die für diesen Run spezifischen Parameter (overrides.yaml) sowie weitere, während des Runs produzierte Metadaten (job\_return\_value.json). Darüber ist jederzeit nachvollziehbar, welche Prediction-Datei mit welchen Hyperparametern, Random Seed, Modell, Commit oder Branch, etc. erzeugt wurde. Über den Commit-Hash kann das Experiment ggf. reproduziert werden. Die Zeitstempel für predictions/ und dem zugehörigen logs/predict/ Ordner sind identisch, für leichtere Zuordnung. Die logs/evaluate Zeitstempel sind, weil die Evaluation separat gestartet wird, verschieden von den predict/ - Zeitstempeln.

Im logs/-Ordner werden zusätzlich eine “readme.md” sowie die mit einem Jupyter Notebook[4] erzeugten Grafiken zu den automatischen Metriken und Fehlern abgelegt. Die Readme enthält alle notwendigen Informationen zur Reproduktion des Experiments, inklusive einer Beschreibung des Experiments, relevanter Log-Ausgaben, Konfigurationsparameter für das Jupyter Notebook, der Dokumentation der Inferenz- und Evaluationsskriptaufrufe sowie Links zu relevanten Github Issues und weiterer Dokumentation.

Insgesamt wurden für die Analysen in TL4 die Ergebnisse von 18 Experimenten aufbereitet. Die meisten Experimente nutzen alle in Teilleistung 2, Abschnitt 2.4 aufgeführten Modelle, bis auf Ministral 3[5]. Von den Experimenten entfallen 10 auf das Faktencheck Kernschema, und 8 auf das Organismentrendschema. Je Experiment und Modell wurden meist 3 Durchläufe mit verschiedenen Random Seeds ausgeführt. Ausnahme war GPT 5, wo wir oft nur einen Durchlauf verwendeten, um die Kosten niedrig zu halten. Insgesamt entstanden so mehr als 120 Modelldurchläufe für das Kernschema, und etwas mehr als 90 Durchläufe für die Organismentrends.

-----

[1] kibad-llm/src/kibad\_llm/data\_integration/db\_converter.py (Hinweis: Der Pfad bezieht sich auf das kibad-llm Coderepository, das separat zur Verfügung gestellt wird) 
[2] kibad-llm/src/kibad\_llm/datasets/csv.py 
[3] Copy of Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx 
[4] kibad-llm/notebooks/plot\_multirun\_evaluation.ipynb 
[5] Das Modell Ministral 3 wurde nach den ersten Tests nicht mehr verwendet, da es zu viele Fehler produzierte. 