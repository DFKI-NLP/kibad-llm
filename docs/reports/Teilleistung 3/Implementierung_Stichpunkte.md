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