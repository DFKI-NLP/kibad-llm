# Dokumentation Teilleistung 2 “Entwicklung des Proof-of-Concept Workflows”

Kontinuierliche KI-basierte Biodiversitäts-Assessments für Deutschland (KIBA-D)

202501 KIBA-D
Version: 1.0
Status: final

DFKI GmbH Tel: +49 631 20575 0
Trippstadter Straße 122 Email: info@dfki.de
67663 Kaiserslautern Web: www.dfki.de

iDiv e.V. Tel: +49 341 9733105
Puschstraße 4 Email: info@idiv.de
04103 Leipzig Web: www.idiv.de

## Inhaltsverzeichnis

  * 1. Einleitung 3
      * 1.1. Überblick AP 1 3
      * 1.2. Ziele Teilleistung 2 3
      * 1.3. Struktur des Dokuments 3
  * 2. Entwicklung des Proof-of-Concept Workflows 3
      * 2.1. Hintergrund und Motivation 3
      * 2.2. Überblick und Architektur 4
      * 2.3. Anwendungsfälle 7
      * 2.4. Modellauswahl und -bewertung 7
      * 2.5. Frameworks und Bibliotheken 8
      * 2.6. Integration Daten-Governance-Konzept 9
      * 2.7. Evaluationskonzept für die automatische Evaluation 10

# 1. Einleitung

## 1.1. Überblick AP 1

Das Projekt KIBA-D "Kontinuierliche KI-basierte Biodiversitäts-Assessments für Deutschland" hat sich die Aufgabe gesetzt, die Grundlagen für ein KI-basiertes System zu entwickeln, das auf Basis des Korpus des Faktenchecks Artenvielfalt KI-Modelle trainiert, die relevante Daten zu Biodiversitätstrends, zu kausalen Zusammenhängen, zu Bewertungen der Wirksamkeit von Instrumenten und Maßnahmen aus Textinformation extrahieren und - in einem zusätzlichen Schritt - auch analysieren können. Ziel des ersten Arbeitspakets AP1 ist dabei die Etablierung eines Workflows zur KI-gestützten Extraktion biodiversitätsrelevanter Informationen aus Textquellen. Der Workflow soll aus drei Elementen bestehen: (1) Die Erstellung eines digitalen Referenz-Korpus aus möglichst allen Dokumenten des Faktencheck Artenvielfalt, (2) die Auswahl und das Training von LLM-basierten Modellen mithilfe dieses Korpus und (3) das Rekreieren der “Annotationen” des Faktenchecks zu Testzwecken mit anschließender Validierung und Sensitivitätsanalyse.

Dieser Zwischenbericht stellt einen vorläufigen Projektbericht für die zweite Teilleistung in AP1 dar und dient zur Dokumentation des Projektstands und zur Abnahme der Teilleistung.

## 1.2. Ziele Teilleistung 2

Ziel von Teilleistung 2 ist die inhaltliche und technische Konzeption des Proof-of-Concept Workflows zur Umsetzung der Informationsextraktion auf den Publikationen des Faktencheck Artenvielfalt. Dafür werden, basierend auf den Anwendungsfällen und der Datengrundlage (siehe TL 1), eine Architektur für das System und konkrete Funktionalitäten sowie Eingabe- und Ausgabeparameter für die LLMs definiert. Das Konzept stellt die Grundlage für die Implementierung des Systems in TL 3 dar.

## 1.3. Struktur des Dokuments

Das folgende Kapitel 2 beschreibt zunächst die Herangehensweise und das finale Konzept des Workflows. Im Anschluss werden weitere Aspekte, wie die Konzeption der Evaluation des Systems und die Integration des Daten-Governance-Konzepts beschrieben.

# 2. Entwicklung des Proof-of-Concept Workflows

## 2.1. Hintergrund und Motivation

Die zentrale Aufgabe der Anwendungsfälle zur Rekreierung des Faktencheck Artenvielfalt fällt aus sprachtechnologischer Sicht in das Gebiet der Informationsextraktion. Sowohl die Erkennung von einzelnen Konzepten - wie z.B. Arten, Lebensräume, und Orte - als auch die Erkennung von Beziehungen zwischen erkannten Konzepten sind klassische Teilaufgaben der Informationsextraktion, in diesem Fall Eigennamenerkennung (Named Entity Recognition, NER) und Relationsextraktion (RE). Die Erkennung komplexerer Aussagen, z.B. Trendaussagen oder kausalen Zusammenhängen zwischen Treibern und Biodiversitätsänderungen, würde in etwa Tasks wie der Claim Extraction oder dem Argumentation Mining entsprechen. In allen angedachten Szenarien geht es darum, aus unstrukturierten Textdaten solche und andere Informationsarten zu extrahieren, um sie in strukturierter Form für eine maschinelle Weiterverarbeitung zur Verfügung zu stellen.

Die Anforderungsanalyse und die Auswertung der verfügbaren Datenbasis ergaben inhaltlichen Herausforderungen, die bei der Systementwicklung zu berücksichtigen sind:

  * Die zu extrahierenden Inhalte haben stark differenzierte “Schwierigkeitsgrade”
  * Klassische Eigennamenerkennung auf Wortebene (z.B. Ort, Taxon), teilweise mit vorgegebenen Antwortmöglichkeiten (z.B. Lebensraum)
  * Komplexere Datentypen auf Basis von längeren Wortgruppen und inklusive Klassifikationsschritt in vorgegebene Antwortmöglichkeiten (z.B. Ökosystemtyp - Beschreibung, Term und Kategorie)
  * Aussagenerkennung auf Satzebene / satzübergreifend (z.B. Trends, kausale Zusammenhänge)
  * Annotationen sind in der Literaturdatenbank nur auf Dokumentebene verfügbar, nicht auf Wortebene
  * Die Extraktion erfolgt je Dokument, und als Ergebnis produziert das System eine Reihe von Metadaten/Annotationen, wie sie für die Literaturdatenbank, die Weighted Vote Counts, etc., benötigt werden.

Zusätzlich waren die weiteren technischen Anforderungen (siehe TL1, Abschnitt 2.3) zu berücksichtigen.

Klassische Ansätze auf Basis einer sequenziellen Pipeline einzelner NLP-Schritte - zuerst Eigennamenerkennung, dann eine Normalisierung (Entity Linking), gefolgt von Relations- und Claimerkennung - fallen aufgrund der nicht vorhandenen Annotationsdaten auf Wortebene, die für das überwachte Training von KI-Modellen für jeden dieser Schritte benötigt werden, als Lösung zunächst aus. Ebenso ergab sich aus den Anwendungsfällen nicht die Notwendigkeit, eine Art Retrieval-Augmented-Generation-System (RAG) zu konzipieren: Einerseits sollen immer komplette Dokumente vollständig verarbeitet werden, andererseits sind die Informationsbedarfe konkret vorgegeben, und werden nicht interaktiv durch einen Nutzer dynamisch generiert. In einem RAG-System müsste zudem die Suchkomponente mit entsprechenden gelabelten Trainingsdaten justiert werden.

Wir haben uns daher für einen an eine klassische NLP-Pipeline angelehnten Ansatz entschieden, in dem wir allerdings die Fähigkeiten aktueller großer Sprachmodelle nutzen wollen, um ein Training von spezifischen Modellen für einzelne Schritte der Pipeline zu vermeiden. Der Ansatz ermöglicht einen späteren Austausch der generischen Basismodelle gegen überwacht trainierte oder anderweitig auf die Aufgaben angepasste Modelle. Zudem erlaubt die dokumentenzentrierte Verarbeitung die Parallelisierung der Verarbeitung, was die Skalierung auf große Dokumentenkorpora ermöglicht.

## 2.2. Überblick und Architektur

Abbildung 1 illustriert den geplanten Workflow der Informationsextraktion. Jedes Dokument wird zunächst aus seinem Ausgangsformat - typischerweise PDF - in eine Textform konvertiert und dann durch ein LLM verarbeitet. Bei Dokumenten, die nur als Bilddaten verfügbar sind (z.B. PDFs bestehend aus gescannten Buchseiten) kann eine OCR-Software oder ein Vision-Language-Modell eingesetzt werden. Wichtig am Workflow ist, dass die vom System extrahierten Informationen zunächst nicht direkt in die Literaturdatenbank des Faktencheck Artenvielfalt einfließen, sondern zuvor durch Expert\*innen verifiziert werden können (und müssen). Erst wenn die experimentelle Evaluation für bestimmte Informationen eine zufriedenstellende Qualität der LLM-basierten Extraktion zeigt, kann man überlegen, zu einem vollständig automatisierten Workflow überzugehen.

Abbildung 1 Workflow für die Informationsextraktion aus PDF-Dokumenten

Abbildung 2 zeigt die geplante Systemarchitektur der Informationsextraktionspipeline, inklusive der Evaluation.

Abbildung 2 Konzeptuelle Systemarchitektur für die Informationsextraktionspipeline

Die gewählte Architektur bietet verschiedene Vorteile:

  * Instruktionen und Beispiele für das LLM via Prompts
  * Unterstützung für flexible Datenschemas und Prompt Templates
  * Austauschbare LLMs
  * Integrierte Evaluation
  * Parallelisierbarkeit
  * Mehrschrittige Prompt-Workflows

Die Logik des Workflows ist relativ Standard im Vergleich zu klassischen NLP-Pipelines. Die Vorverarbeitungskomponente ist dafür zuständig, verschiedene Inputformate in ein normalisiertes Format, auf Textbasis, zu konvertieren. Zudem werden weitere Normalisierungs- und Säuberungsschritte ausgeführt, oft heuristisch gesteuert (z.B. Beheben von Encodingproblemen, Entfernen nicht-relevanter Textabschnitte wie z.B. Literaturverzeichnisse bei Publikationen). Eine Verarbeitung von Bilddaten via OCR würde ebenfalls hier durchgeführt werden.

Über ein konfigurierbares Datenschema werden die Extraktionsaufgaben flexibel definiert. Im Schema werden die gewünschten Informationen und ihre Struktur sowie eventuelle Vorgaben (z.B. Antwortmöglichkeiten) festgelegt. Die Vorgabe eines Datenschema stellt sicher, dass das LLM nur Outputs produziert, die dem Schema entsprechen. Abbildung 3 zeigt beispielhaft einen Ausschnitt des “Kernschemas”, Abbildung 4 den daraus generierten Beschreibungstext, der Teil des Prompts ist (siehe TL3).

Abbildung 3 Ausschnitt eines exemplarischen Datenschemas

Abbildung 4 Ausschnitt der Beschreibung des obigen Schemas als Teil des Prompts

Aus dem Schema und dem ebenfalls konfigurierbaren Prompttemplate wird das finale Prompt generiert. Im Prompttemplate übersetzen wir die unterschiedlichen Anforderungen der Anwendungsfälle in konkrete Instruktionen und Erläuterungen, und lassen damit die aus NLP-Sicht notwendigen Schritte durch das LLM ausführen - sowohl für einfache Konzepterkennung, als auch für die komplexeren Extraktionsaufgaben. Bei Bedarf können neben den Instruktionen im Prompt auch noch Beispiele mitgegeben werden (Wechsel von zero-shot in-context-learning (ICL) zu few-shot ICL). Das finale Prompt wird zusammen mit dem Dokument und weiteren Parametern an die LLM-Schnittstelle geschickt.

Die LLM-Schnittstelle kapselt das eigentliche LLM bzw. generative KI-Modell, so dass dieses austauschbar ist. Dabei unterstützt diese Komponente sowohl lokale Modelle als auch die API-Schnittstellen proprietärer Modelle wie OpenAI, Claude, etc. Optional ist eine Weiterverarbeitung durch Folge-Prompts möglich, die durch das Output des aktuellen Schritts gesteuert werden kann. So können z.B. bedingte Workflows, Selbstvalidierungsschritte, etc., umgesetzt werden. Perspektivisch kann die Entscheidung über Folgeschritte dann auch dem LLM selbst überlassen werden, so dass das ganze System in Richtung einer agentischen Pipeline weiterentwickelt werden kann.

Das Ergebnis des LLM-Aufrufs, also das gefüllte Datenschema sowie Metadaten, werden durch eine Reihe von Postprocessing-Schritten angereichert (z.B. Ergänzung von Textstellenbelegen, Normalisierung von extrahierten Konzepten, Anreicherung mit Provenienzinformationen, etc.). Danach werden sie abgelegt bzw. an die Evaluationskomponente weitergeleitet.

Die Evaluationskomponente dient dazu, die vom LLM generierten Ergebnisse mit den Referenzannotationen der Testdaten zu vergleichen. Es können hier verschiedene automatisch berechenbare Metriken integriert werden, die auf Feldebene arbeiten (z.B. Accuracy, Precision, Recall, F1). Zusätzlich können andere Auswertungen durchgeführt werden, z.B. die Erstellung von Konfusionsmatrizen oder die Analyse von Fehlerfällen.

## 2.3. Anwendungsfälle

Die oben beschriebene Architektur ermöglicht die Bearbeitung der Anwendungsfälle UC 1 “Informationsextraktion aus Texten” inklusive der Unteranwendungsfälle, UC 2 “Rekreieren des Faktencheck Korpus”, UC 5 “Weighted Vote Counts”, und die Vorbereitung der Datengrundlage für die Anwendungsfälle UC 6 “Sonstige Informationen dokumentübergreifend verdichten / Kernaussagen formulieren”, UC 7 “Neue Informationen im Vergleich zum FA 1.0 hervorheben” und UC 8 “Sensitivitätsanalysen”. Es ist lediglich nötig, das verwendete Schema und Prompttemplate auszutauschen, sowie ggf. andere Konfigurationsparameter des Systems (eingesetztes LLM, Hyperparameter des Modells, etc.)

## 2.4. Modellauswahl und -bewertung

Als Teil der Architekturplanung haben wir eine Recherche und initiale Bewertung von relevanten KI-Modellen durchgeführt. Aufgrund einer ersten Analyse der PDF-Dateien der Literaturdatenbank haben wir hier zunächst nur reine LLMs berücksichtigt, da die Analyse ergab, dass nur ein vernachlässigbarer Teil der PDFs aus Bilddaten besteht und deshalb OCR bzw. ein Vision-Language-Modell zur Verarbeitung benötigen würde. Ein wichtiges Kriterium für die initiale Modellauswahl war die Verfügbarkeit als Open Source oder Open Weight Modell, einerseits, um die Modelle lokal laufen lassen zu können, andererseits aber auch aus dem Grund, dass Open Source Modelle eine einfachere Anpassung an die Biodiversitätsdomäne, z.B. durch Training mit dem Korpus des Faktencheck, erlauben, und damit die Abhängigkeit von kommerziellen Anbietern bzw. proprietären Modellen verringert wird. Zudem konzentrierten wir uns initial auf Modelle mit weniger Parametern, um schneller über Experimente iterieren zu können, da die Inferenzgeschwindigkeit bei größeren Modellen niedriger ist (gegeben die verfügbare Hardware). Alle ausgewählten Modelle, bzw. deren Modellfamilien, haben aber auch Varianten mit deutlich mehr Parametern, sodass später problemlos auf größere Modellvarianten gewechselt werden kann.

Tabelle 1 zeigt die LLMs, die aufgrund von Erfahrungswerten aus Vorprojekten und auf Basis der gerade genannten Kriterien für die initialen Experimente ausgewählt wurden. Alle Modelle unterstützen die Zielsprachen Deutsch und Englisch und sind in der Lage, Kontexte der Länge von 128,000 Tokens zu verarbeiten. Alle Modelle bis auf Ministral 3 sind sogenannte Reasoning-Modelle, d.h. sie wurden so trainiert, dass sie auf Wunsch zunächst einen Analyse- und Handlungsanweisungstext generieren, bevor sie das finale Ergebnis erzeugen. Typischerweise führt dieser Zwischenschritt zu besseren Ergebnissen, allerdings werden dadurch auch mehr Tokens generiert, was die Inferenzzeit / Kosten vergrößert. Zusätzlich haben wir ein proprietäres OpenAI-Modell inkludiert, GPT 5.2, das als Referenz für eine mögliche “upper bound” der Performanz gedacht ist.

Tabelle 1 Modellauswahl für initiale Experimente im Proof-of-Concept Workflow (TL3)

## 2.5. Frameworks und Bibliotheken

Parallel zur Entwicklung der Architektur des Proof-of-Concept Workflows wurden LLM-Frameworks und Bibliotheken gesammelt und evaluiert, die die Basis für die Umsetzung der Workflows bilden könnten. Aufgrund unserer Recherchen haben wir uns für folgende Frameworks entschieden:

  * LlamaIndex [1]: LlamaIndex ist eine Bibliothek für die Umsetzung dokumentorientierter Workflows mit LLMs, und unterstützt agentische / RAG Setups, aber auch OCR. Als Alternative hatten wir LangChain [2] in Betracht gezogen, das letztere erschien uns jedoch aktuell als unnötig komplex für unsere Anwendungsfälle. LangChain integriert jedoch Speicher-, Agenten- und Werkzeugnutzungskonzepte, und könnte sich daher besser für das Projekt eignen, wenn die abgebildeten Workflows von KIBA-D umfangreicher werden.
  * vLLM [3]: Eine schnelle und einfach zu bedienende Bibliothek für LLM-Inferenz und -Bereitstellung. Im Gegensatz zur anderen populären Alternative Ollama [4] ist für den High-Performance-Serverbetrieb optimiert, statt für die lokale Entwicklung
  * Hydra [5]: Hydra ist ein Framework zur einfachen Konfiguration von komplexen Anwendungen. Es ermöglicht komponierbare Konfigurationen und unterstützt damit vor allem die effiziente Durchführung vieler ähnlicher Experimente.
  * Pydantic [6]: Pydantic ist eine Datenvalidierungsbibliothek für Python, die es uns erlaubt, Datenschemas zu definieren und das Output der KI-Modelle zu validieren.

Weitere Frameworks, die im Verlauf des Projekts eine Rolle spielen könnten, sind DSPy [7] zur automatischen Optimierung von Prompts, und Evaluationsframeworks wie DeepEval [8] oder Promptfoo [9], die eine Reihe von weiteren Metriken zur Bewertung des Outputs generativer LLMs bereitstellen. Aktuell implementieren wir die Evaluationslogik und Metriken selbst, siehe Abschnitt 2.7.

## 2.6. Integration Daten-Governance-Konzept

Ein relevanter Aspekt der Konzeption der Systemarchitektur des Proof-of-Concept Workflows ist die Integration der Ergebnisse des rechtlichen Prüfung, welche unter anderem in Form eines Daten-Governance-Konzepts in Teilleistung 8 erarbeitet wird. Zum Zeitpunkt dieses Berichts wurde ein erster Entwurf des Daten-Governance-Konzepts auf dem Meilensteintreffen zu AP 1 vorgestellt (siehe Dokument “20260219 KIBA-D – Data-Governance-Konzept Entwurf.docx”).

Für die Architektur der hier vorgestellte Analysepipeline sind vor allem die Abschnitte zur Datenverarbeitung relevant, und darin insbesondere die Dokumentationspflichten. Die von uns geplante Architektur beinhaltet eine exakte, nachvollziehbare Dokumentation der Provenienz aller gewonnenen Informationen sowie aller zugehörigen Metadaten (eingesetztes LLM, Modellparameter, Prompt, Systemversion, etc.) über die komponierten Hydra-Konfigurationsartefakte. Diese Dokumentation kann später auch dazu genutzt werden, um Daten-Steckbriefe für die gesammelten Analyseergebnisse der LLMs zu erstellen, und damit den Transparenz- und Dokumentationspflichten für die neu entstandenen Datensätze in Bezug auf Motivation, Zusammensetzung, Erhebungsprozesse, und empfohlenen Nutzungen gerecht zu werden (siehe “20260219 KIBA-D – Data-Governance-Konzept Entwurf.docx”, Abschnitt 4). Zusätzlich haben wir für die Umsetzung vorgesehen, jede ‘Extraktion’ konkreter Informationen aus einem Dokument mit einem Textstellenbezug (d.h. Referenz auf die Fundstelle wie bei einer Quellenangabe) und/oder einem Textsnippet, also einer exzerptierten Textstelle um den Fundort herum, zu versehen. Dies ermöglicht einerseits die raschere Prüfung der LLM-Ergebnisse durch Expert\*innen, andererseits aber auch eine Provenienz der Datenherkunft auf Datenelementebene, was z.B. bei späteren Aggregationen vieler Extraktionen über Dokumente / Abstraktionsebenen hinweg wichtig sein könnte.

## 2.7. Evaluationskonzept für die automatische Evaluation

Als Teil der Entwicklung der LLM-Pipeline haben wir eine automatische Evaluation der LLM-Ausgaben vorgesehen. Dabei werden die Modellausgaben und Referenzdaten mittels quantitativen Metriken wie z.B. Accuracy oder F1 verglichen. Der Vergleich erfolgt zunächst auf der Ebene einzelner Informationselemente der Literaturdatenbank bzw. der Weighted Vote Counts, aus denen dann aggregierte Werte für das gesamte Dokument bzw. einen Testdatensatz berechnet werden können. Aufgrund der Struktur der Referenzannotationen können wir alle Elemente nur dokumentbezogen evaluieren, d.h. konkrete Positionen im Text wie bei klassischer sequenzbasierter Evaluation werden nicht berücksichtigt, und Mehrfachnennungen ebenfalls nicht. Methodisch wird die automatische Evaluation als Teil der skizzierten LLM-Pipeline integriert (siehe Abbildung 2). Für jedes durchgeführte Experiment werden je Element die zugehörigen Metriken sowie deren Aggregationen (z.B. Macro-/Micro-Mittelwerte) berechnet. Die konkrete Implementierung inklusive eingesetzter Metriken wird im Bericht zu Teilleistung 3 beschrieben.

Bei der Entwicklung des Konzepts für die automatische Evaluation der Modellvorhersagen mit den Referenzannotationen der Testdaten ergaben sich nach der Erarbeitung des Fragenkatalogs verschiedene Aspekte, die zu berücksichtigen waren:

  * Komplexe Elemente versus einfache Elemente
  * Elemente mit festgelegten Kategorien versus offene oder erweiterbare Kategorien
  * Elemente mit Freitextantworten
  * Offene Fragen
  * Auswahl der Metriken

Einige der in der Literaturdatenbank annotierten Werte bilden zusammengehörige Informationsgruppen, andere stehen als Einzelfelder für sich. So ist zum Beispiel der “Ökosystemtyp” durch drei Felder - “Kategorie”, “Begriff”, und “Beschreibung” definiert, während z.B. “Lebensraum” unabhängig von anderen Elementen ist [10]. Für einfache Elemente genügt ein direkter Vergleich des vorhergesagten Werts mit der Referenzannotation. Bei komplexen Elementen kann eine strikte Evaluationssicht angewendet werden, wonach das komplexe Element nur korrekt ist, wenn alle Teilelemente im Vergleich zur jeweiligen Referenzannotation den richtigen Wert haben. Alternativ kann man partielle Matches erlauben, z.B. beim Ökosystemtyp den Wert für “Beschreibung” als optional betrachten. Eine dritte Möglichkeit ist es, komplexe Elemente in ihre Subelemente aufzulösen und alle Informationstypen als einfache Elemente zu betrachten (“flache Evaluation”). Dabei geht allerdings die Zusammengehörigkeit verloren, was insbesondere dann wichtig wird, wenn für ein Dokumente mehrere Vorhersagen für einen komplexen Typ (z.B. mehrere Ökosystemtypen) erzeugt werden bzw. in den Referenzen annotiert sind. In diesem Fall kann die flache Evaluation Zuordnungsfehler des LLMs verschleiern (z.B. falsche Kombination von Kategorie und Term). Dies ist insbesondere bei der Evaluation der Trendaussagen relevant, da hier im Fall von mehreren Trends in einem Dokument nur die korrekte Kombination der Einzelelemente - also z.B. Lebensraum, Artengruppe, Biodiversitätsvariable mit einem Trend - als richtig gewertet werden kann.

Die Evaluation von Elementen mit festgelegten bzw. offen erweiterbaren Kategorien ist relativ unproblematisch, da hier auch nur ein Vergleich auf der Ebene einzelner Annotationen erfolgt. Es können quantitative Metriken wie Precision, Recall, F1 und Accuracy eingesetzt werden. Für Elemente mit festgelegten Kategorien können allerdings über das Schema stärkere Vorgaben gemacht werden, d.h. Begriffe und deren Schreibweise sind fest definiert. Bei offenen Kategorien kann es hingegen vorkommen, dass das LLM Synonyme oder einfach nur andere Schreibweisen des Referenzbegriffs generiert, die dann zu einem Mismatch führen.

Schwieriger ist die Evaluation von Elementen mit Freitextantworten. Das betrifft hauptsächlich die Informationstypen, die “Beschreibungen” als Teilfeld enthalten, also z.B. Ökosystemtyp, Treiber, Schutzgebiete, etc. Hier ist ein wortgenauer Vergleich nicht geeignet, da bereits minimale Unterschiede (linker bzw. rechter Rand, fehlende oder zusätzliche Wörter, Umformulierungen) zu einem “Fehlerfall” bei Metriken wie Accuracy oder F1 führen. Klassischerweise sollten daher Ähnlichkeitsmaße (z.B. ROUGE, BLEU, BertScore) oder schnittmengenbasierte Metriken eingesetzt werden (z.B. Jaccard-Koeffizient, Longest Common Substring).

Offene Fragen, die letzte Kategorie von Fragetypen des Fragenkatalogs, sind von den Biodiversitätsexpertinnen zusätzlich formulierte Fragestellungen, die nicht in der Literaturdatenbank annotiert sind. Eine typische Fragestellung wäre z.B. “Wie beeinflussen die direkten Treiber den Trend?”. Das erwartete Output des LLMs wäre hier also eine Freitextantwort, die typischerweise mit einem festgelegten Bewertungsraster evaluiert werden sollte. Das Bewertungsraster definiert Kriterien/Fragestellungen, wie z.B. ‘Passgenauigkeit der Antwort’, ‘Enthält die Antwort halluzinierte Elemente’, usw., die anhand einer festen Skala (z. B. Ordinalskala, Likert-Skala) bewertet werden. Hierfür können neben der Bewertung durch Expertinnen auch LLM-as-a-judge-Ansätze eingesetzt werden, um eine Skalierung auf größere Datenmengen zu ermöglichen. Ein Vergleich der automatischen Bewertungen mit Expertenbewertungen sollte jedoch auf jeden Fall durchgeführt werden, um die Qualität der automatischen Bewertungen einschätzen zu können.

-----

[1] [https://www.llamaindex.ai/](https://www.google.com/url?sa=E&source=gmail&q=https://www.llamaindex.ai/)
[2] [https://www.langchain.com/](https://www.google.com/url?sa=E&source=gmail&q=https://www.langchain.com/)
[3] [https://github.com/vllm-project/vllm](https://www.google.com/url?sa=E&source=gmail&q=https://github.com/vllm-project/vllm)
[4] [https://ollama.com/](https://www.google.com/url?sa=E&source=gmail&q=https://ollama.com/)
[5] [https://hydra.cc/](https://www.google.com/url?sa=E&source=gmail&q=https://hydra.cc/)
[6] [https://docs.pydantic.dev/latest/](https://www.google.com/url?sa=E&source=gmail&q=https://docs.pydantic.dev/latest/)
[7] [https://dspy.ai/](https://www.google.com/url?sa=E&source=gmail&q=https://dspy.ai/)
[8] [https://deepeval.com/](https://www.google.com/url?sa=E&source=gmail&q=https://deepeval.com/)
[9] [https://www.promptfoo.dev/](https://www.google.com/url?sa=E&source=gmail&q=https://www.promptfoo.dev/)
[10] Die Festlegungen als einfacher oder komplexer Informationstyp sind im Dokument “Fragenkatalog” in der Spalte “Gruppe/Komplexer Datentyp” dokumentiert.