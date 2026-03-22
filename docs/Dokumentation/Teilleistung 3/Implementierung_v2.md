## 2.1. Implementation

Die technische Umsetzung des in Teilleistung 2 konzipierten Proof-of-Concept Workflows für ausgewählte Content-Extraktionsaufgaben erfolgt über das Python-basierte Framework `kibad-llm`. Die Codebasis ist stark modularisiert und nutzt Hydra zur Konfigurations- und Experiment-Orchestrierung. Dies erlaubt eine flexible Steuerung verschiedener LLM-Backends, Extraktions-Schemata und Evaluierungsdurchläufe (via `configs/predict.yaml` und `configs/evaluate.yaml`), ohne den Kerncode anpassen zu müssen. Die generelle Code-Qualität wird durch den Einsatz von pre-commit Hooks, `pytest` für automatisierte Tests (inklusive Integrations-, Schema- und Aggregationstests) sowie GitHub CI sichergestellt.

Der Kern der Implementierung ist die Extraktions-Pipeline, welche über den zentralen Einstiegspunkt `predict.py` angesteuert wird und vollständig parallelisierbar (Batchverarbeitung) ist.

Abbildung "Eingabe-Processing-Ausgabe"
![Eingabe-Processing-Ausgabe.png](images/Eingabe-Processing-Ausgabe.png)

### 2.1.1. Vorverarbeitung und PDF-Konvertierung

Als Voraussetzung für die LLM-Verarbeitung müssen die Eingabe-PDFs in ein maschinenlesbares Format überführt werden, das semantische Strukturen beibehält. Das Modul `kibad_llm.preprocessing` nutzt hierfür `PyMuPDF4LLM` zur Konvertierung der PDFs in Markdown-Text. Dies erhält wichtige Layout-Informationen wie Tabellen und Überschriften für das Sprachmodell. Der Workflow ist darauf ausgelegt, perspektivisch um OCR (für Bild-basierte Scans) oder Konverter für andere Dokumentarten (z.B. docx-to-text) erweitert zu werden.

Abbildung "Pipeline - Teil 1 - Schemata und Vorverarbeitung"
![Pipeline - Teil 1 - Schemata und Vorverarbeitung.png](images/Pipeline%20-%20Teil%201%20-%20Schemata%20und%20Vorverarbeitung.png)

### 2.1.2. Schema-Definition und dynamisches Prompting

Um die in Teilleistung 2 definierten, unterschiedlich komplexen Informationsbedarfe abzubilden, wird das erwartete Datenformat strikt als Pydantic-Datenmodell (in `src/kibad_llm/schema/types.py`) definiert. Aktuell sind Schemata wie *Full*, *Kern* und *OrganismTrend* implementiert.

Das Modul `src/kibad_llm/schema/utils.py` übernimmt dabei die entscheidende Vermittlerrolle zwischen Datenmodell und Modell-Prompt:

- **Automatische Schema-Generierung:** Aus den Pydantic-Modellen wird automatisch das benötigte JSON-Schema sowie eine textuelle Beschreibung des geforderten Datenformats generiert.
- **Evidenz-Anpassung:** Das Schema wird automatisch erweitert, um sogenannte Evidenz-Anker (exakte Zitate zur Belegung extrahierter Informationen) vom LLM einzufordern.

Das finale Prompting setzt sich dynamisch aus dem manuell definierten Prompt-Text (Aufgabenstellung, Persona), der generierten Datenformat-Beschreibung und dem konvertierten Dokumententext zusammen. Es wurden drei konfigurierbare "Basisprompts" (auf Basis der Annotationsrichtlinien von iDiv) implementiert: *Mit Evidenz*, *Mit Persona* und *Ohne Feld- bzw. Typ-Beschreibungen*.

Abbildung "Prompt"
![Prompt.png](images/Prompt.png)

### 2.1.3. LLM-Engine und Inferenz

Die LLM-basierte Textgenerierung ist über abstrakte Basisklassen (`src/kibad_llm/llms/base.py`) gekapselt, was die in TL 2 geforderte Austauschbarkeit der Modelle garantiert. Für kommerzielle Modelle (wie OpenAI GPTs) erfolgt die Anbindung via Llama-Index, während für selbst-gehostete Open-Source-Modelle (wie Qwen) vLLM als performante Inferenz-Engine genutzt wird.

Um die strikte Einhaltung der Pydantic-Schemata zu garantieren, wird **JSON Schema basiertes Guided Decoding** (Strukturiertes Output) eingesetzt. Zusätzlich nutzt das System, sofern vom LLM unterstützt, **Reasoning-Traces** (Ausgabe von Gedankengängen in `<think>`-Tags), um die Qualität der Extraktionen bei komplexen kausalen Zusammenhängen zu steigern.

Zur weiteren Stabilisierung und Leistungssteigerung unterstützt das System (`kibad_llm.extractors.base.py`) optional verschiedene Ergebnis-Aggregationen:

- **Ensemble-Methoden:** Majority-Voting über mehrere LLM-Antworten für robustere Ausgaben.
- **Problemzerlegung:** Aufteilung komplexer Schemata in unabhängige oder konditionale Einzelschritte zur Komplexitätsreduktion (kleinere Prompts machen die Aufgabe für das LLM leichter).
- **Dokument-Chunking:** Falls Dokumente den maximalen Kontextbereich überschreiten.

Perspektivisch bildet dies die Grundlage für komplexe konditionale, orchestrierte oder agentische Promptflows.

Abbildung "Pipeline - Teil 2 - LLM Engine"
![Pipeline - Teil 2 - LLM Engine.png](images/Pipeline%20-%20Teil%202%20-%20LLM%20Engine.png)

### 2.1.4. Post-Processing und finales Datenformat

Nach der Textgenerierung verarbeitet das System die vom LLM extrahierten Evidenz-Anker weiter. Falls ein Anker im Eingabe-Text erfolgreich gefunden wird, generiert das System ein **Evidenz-Snippet**, indem es den Anker um einen Kontext von *k* Wörtern erweitert. Dies setzt die Anforderung des Daten-Governance-Konzepts (TL 2) um, die Herkunft extrahierter Fakten nachvollziehbar zu belegen.

Das Ergebnis der Extraktions-Pipeline wird als finales JSON(L) gespeichert. Neben den strukturierten Extraktionsdaten enthält das finale Objekt zusätzliche Metadaten für die spätere Fehleranalyse:

- Unverarbeitete LLM-Antworten
- Reasoning-Traces
- Evidenz-Snippets inklusive ihrer exakten Position im Originaltext
- Aufgetretene Fehler und System-Messages

Abbildung "Extraktions-Ergebnis"
![Extraktions-Ergebnis.png](images/Extraktions-Ergebnis.png)

### 2.1.5. Evaluation (evaluate.py)

Die Pipeline wird durch das Modul `predict.py`s Gegenstück, `evaluate.py`, komplettiert. Dieses Modul steuert den Batch-Evaluationsprozess und ermöglicht den Abgleich der Vorhersagen mit den Referenzdatensätzen (`src/kibad_llm/dataset/*`).

Dabei werden die in TL 2 skizzierten Evaluationskonzepte angewendet: Das System erlaubt die Unterscheidung zwischen "flacher" und "komplexer" Evaluation bei geschachtelten Hierarchien. Die Metriken-Logik (`src/kibad_llm/metrics/*`) berechnet detailliert F1-Score, Precision und Recall (sowohl pro Klasse als auch als Averages) und gibt zusätzlich Confusion Matrices sowie Listen spezifischer Fehlerfälle aus. Über Hydra Callbacks (`save_job_return_value.py`) werden die Evaluationsergebnisse konsistent über mehrere multirun-Experimente hinweg aggregiert und gespeichert.

Abbildung "Pipeline - Teil 3 - Evaluation"
![Pipeline - Teil 3 - Evaluation.png](images/Pipeline%20-%20Teil%203%20-%20Evaluation.png)
