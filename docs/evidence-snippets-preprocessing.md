# Evidence-snippet preprocessing requirements

This page lists what the PDF-to-Markdown conversion (currently [`pymupdf4llm`](/configs/pdf_reader/pymupdf4llm.yaml))
needs to provide for the evidence-snippet pipeline. It is written for whoever works on the preprocessing. See
[Evidence snippets and LLM judge](USAGE.md#evidence-snippets-and-llm-judge) for the pipeline itself.

## Why the text format matters

The pipeline relies on the converted text in three places:

- **Locating anchors.** The model quotes short anchors from a chunk, and code searches for them in the full text.
  Matching tolerates whitespace, Markdown emphasis, quote characters, line-end hyphenation and ellipses, but not
  garbled characters, words merged across columns or running headers in the middle of a sentence.
- **Widening anchors to snippets.** Snippets are built from whole paragraphs (split at blank lines) and, for long
  paragraphs, whole sentences. Wrong paragraph boundaries give snippets that start or end in the middle of an
  unrelated passage.
- **Tracking sections.** The running notes record which section a chunk is in, and each finding gets a section label.
  Without recognizable headings, the model has to guess the section from the content.

## Requirements

Priorities: **must** is needed for reliable snippets, **should** improves quality, **later** is needed once figures
and tables are processed in the extraction.

| Priority | Requirement                                                                                                                                                                               | Reason                                                                                                                                                       |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| must     | Text is extracted as real characters. Scanned PDFs and PDFs with broken font encodings go through OCR.                                                                                     | Garbled text (e.g. `data/Q9YAA7WE.md`, which consists of replacement characters) cannot be quoted or located. Many older organism-trend papers are scans. |
| must     | Multi-column layouts are converted in reading order.                                                                                                                                      | Interleaved columns break sentences, anchors and paragraphs.                                                                                                 |
| must     | One blank line between paragraphs and none inside a paragraph. Line breaks inside a paragraph are fine.                                                                                   | Paragraphs are the unit for widening anchors to snippets.                                                                                                    |
| must     | Running headers, footers, page numbers and line numbers are removed, or at least put on their own paragraph.                                                                             | They interrupt sentences, so anchors spanning a page break are not found.                                                                                   |
| must     | The same conversion is used for prediction and for any later inspection of the snippets.                                                                                                  | Snippet offsets refer to the converted text.                                                                                                                 |
| should   | Section headings are Markdown headings (`#`, `##`, ...) with their numbering kept, e.g. `## 3.2 Drought response`.                                                                       | Section labels and the running notes rely on headings. In the two converted samples in `data/`, headings are missing or garbled.                           |
| should   | Line-end hyphenation is removed where it is not a real hyphen, and ligatures (e.g. `ﬁ`) are normalized.                                                                                  | Matching tolerates both, but summaries and the judge read the text.                                                                                         |
| should   | Page breaks are marked, e.g. `<!-- page 5 -->`.                                                                                                                                           | Snippets can then be traced to a page for manual checks and for cropping figures later.                                                                     |
| should   | The references section has its own heading, and footnotes are separated from the body text.                                                                                               | The model can skip cited literature, which is not a finding of the study.                                                                                   |
| should   | Title, authors, year and abstract come first, e.g. as front matter (Zotero metadata can fill gaps).                                                                                      | The running notes start from the study context.                                                                                                              |
| should   | The text stays in its original language.                                                                                                                                                 | Anchors must be verbatim; translation happens after extraction.                                                                                              |
| later    | Figure captions are separate paragraphs that start with the figure id (`Fig. 3`, `Abb. 3`), followed by a placeholder with id and page, e.g. `![Fig. 3](page-5-figure-1.png)`.              | Organism trends are mostly shown in figures: `Beschreibung_Potential` names a figure in 201 and a table in 100 of 304 gold rows.                            |
| later    | Tables are Markdown tables with their caption directly above, keeping rows, columns and numbers.                                                                                          | Trends and effects in tables can then be quoted like text.                                                                                                   |
| later    | Figure images are stored next to the Markdown (or can be cropped from the page with the placeholder information).                                                                        | A multimodal model can then read trends from figures.                                                                                                        |

## Checking a conversion

Run the evidence-snippet experiments on a dev set and look at how the anchors matched
(`structured.evidence_findings[].anchors[].match` in the predictions):

- `exact`: the quote was found verbatim (up to whitespace).
- `normalized` or `ellipsis`: found after removing punctuation, Markdown, hyphenation or omissions. A high share
  points to formatting noise in the text.
- `partial`: only part of the quote was found. Check whether the text is garbled or the model paraphrased.
- `null`: not found. These findings are not shown to the judge (`metric.include_unlocated=false`).

The judge's count `findings_unlocated` gives the same information per run.
