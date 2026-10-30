# KIBA-D FEdA 2026 presentation: finalization handover

Prepared on 30 October 2026. This document consolidates the slide-comment review, subsequent decisions, verified statistics, and source checks. It is intended to let a colleague finish the presentation without needing the original conversation.

## Scope and current state

- **Presentation:** [KIBA-D_FEdA2026_Keynote.pptx](KIBA-D_FEdA2026_Keynote.pptx).
- **Primary background and results source:** [Manuscript draft KIBA D.docx](<Manuscript draft KIBA D.docx>). Prefer its reported results, supplemented by the verified original evaluation files described below.
- **Other sources:** this `kibad-llm` repository and neighboring `../kibad-crawler`, relative to the repository root. Both are readable locally. This folder is two levels below the repository root.
- **Event:** [FEdA Status Conference 2026](https://www.feda.bio/de/statuskonferenz2026/), Senckenberg, Frankfurt. The [programme](https://www.feda.bio/wp-content/uploads/2026/10/FEdA_Conference_Program-3.pdf) lists the opening keynote on **3 November 2026, 13:45–14:15, in English**, with Julia Ellerbrok and Arne Binder. The slot is 30 minutes; the programme does not specify a separate Q&A allocation.
- The supplied deck contains **30 slides, 22 comments, and 14 comment threads on nine slides**, including hidden slide 25. Replies within a thread are not separate tasks.
- **The slides have not been edited.** Work completed so far consists of inspection, statistics, provenance research, and preparation of this handover and an unposted PR-comment draft.
- Slide numbers throughout this document refer to the **original supplied deck**. Apply the mapping before deleting slides or adding build states.

The agreed scope is to finish the existing talk: address the remaining comments, improve the specified layouts and explanations, and correct the identified inconsistencies. No new inference experiments, crawler features, or legal review are required.

## Main decisions

1. Keep crawling relevant but brief; extraction and its evaluation are the main focus.
2. Show extraction output as columns of coloured boxes, then reveal provenance on the excerpt.
3. Frame costs as **resources**, with concrete estimates that allow comparison between open-weight execution and a proprietary API.
4. Preserve the two task panels on slide 11 and modify the lower strip. Use a **combined, deduplicated, character-weighted** source-type chart.
5. Retain the scale teaser: **“≈1,500 document inputs across development and testing.”**
6. Colour-code open-weight versus proprietary models consistently on slides 12 and 16.
7. Use **Qwen 3 only** and **version B** on slide 17: detect habitat + species group + variable, then categorise direction on matched triples. Remove GPT-5 and the average across model families.
8. Present F1 as **points on a 0–100 scale**, not a percentage of correct answers.
9. Omit the legal/governance slide 25. Its comment is considered resolved; no request to Luisa is needed.
10. Omit the software licence detail. The repository licence is not considered final enough to report in the talk.
11. Correct the old milestone-meeting footer on slide 9.
12. Add a **backup slide on Qwen's direction categorisation**, covering all five categories explicitly: Negative, Neutral, Positive, Positive → negative, and Negative → positive. Use the full confusion matrix and per-direction diagnostics in Appendix C.

## Implementation notes

- Create a backup of the slide deck before editing. Name the backup file `KIBA-D_FEdA2026_Keynote.backup-0.pptx`. If this file already exists, increment the number. Keep the backup in the same folder as the original deck.
- Integrate a short report for the implemented changes into this handover document. Be concise, do not replicate the instructions, just reference them. Most important: note any deviations from the agreed plan, with justification. 

## Slide-by-slide instructions

### Slide 7 — Finding new literature automatically

**Original comment:** the slide is crowded; reconsider the three grey supporting boxes using the crawler repository.

**Agreed direction:** simplify this slide and keep its speaking time short. It should establish where new literature comes from and lead into extraction.

Suggested treatment:

- Retain a compact discovery flow: new publications → keyword screening → full texts for extraction.
- Condense the three grey supporting boxes into a short message about continuing the assessment workflow with expert review, or remove redundant boxes.
- Clearly distinguish implemented functions from planned work. The repository supports Semantic Scholar metadata retrieval, incremental updates, keyword filtering, and PDF download utilities. A learned semantic relevance classifier was not found in the inspected code. EDIT: But it is currently WIP.

**Unverified claims in the existing slide:** the fortnightly operating schedule and forest-subset overlap figures of 95%/97% were not substantiated by the inspected repository material. Crawling is peripheral, so omit these details if the team cannot readily identify their source. Do not turn this into a new research or implementation task. EDIT: But these numbers are correct (internal crawler evaluation on a subset of original Faktencheck bibliography lists) and should be presented. 

Useful sources: `../kibad-crawler/README.md`, `src/kibad_crawler/main.py`, `basic_filter.py`, `relevance.py`, and `crawler.py`, all within the neighboring repository. The README's implementation-status diagram should be checked against the actual code rather than treated as definitive by itself.

### Slide 8 — Buried information / extraction example

**Original comments:** align the extracted output with the example above; introduce three reveals while preserving the alignment of text and annotations.

**Agreed output design:** a two-dimensional extraction board below the excerpt. Each column represents an annotation type; each extraction is an individual box. Boxes use the same colour as their annotation type in the excerpt. Columns can contain different numbers of boxes. Add an ellipsis indicating further extraction types.

Example structure, with illustrative wording to be fitted to the existing annotations:

| Taxon | Time | Location | Trend | ⋯ |
| --- | --- | --- | --- | --- |
| `[Ring Ouzel]` | `[1986–1987]` | `[Black Forest]` | `[decline]` | |
| `[T. torquatus alpestris]` | `[2017]` | `[Germany]` | | |

The current output tuple “Open land / Birds / Abundance / negative” does not faithfully describe the excerpt: it discusses Ring Ouzel distribution and declining habitat occupancy. Replace that tuple with evidence-supported extraction boxes. Do not invent abundance information to fill a predefined tuple.

**Required reveal order:**

1. Excerpt without annotations.
2. Extraction board appears.
3. Annotations appear over the excerpt, demonstrating evidence/provenance.

**Critical constraint:** preserve the existing proportions and relative geometry of the excerpt and annotations. Changing them independently breaks alignment. The objects are editable; a raster recreation is unnecessary. Use reliable native builds where possible and check the sequence in the actual presentation application. The final point is that extracted values come with traceable evidence, even when the downstream task only needs document-level values.

### Slide 9 — Pipeline

Replace the remaining **“KIBA-D - Meilensteintreffen 2 · AP 3 · Oktober 2026”** footer with the conference footer used elsewhere. No broader redesign was requested.

### Slide 10 — Resources and costs

**Original comment:** reorganize as time/money × per document/full corpus.

**Agreed framing:** resources, with monetary comparison between open-weight model execution and GPT-5. Treat the existing slide's runtime and API-cost figures as accepted estimates; do not reopen their verification as a blocker.

Use concrete rental equivalents for open-weight execution:

| Resource | Per document | Full corpus: 3,917 PDFs |
| --- | ---: | ---: |
| Open models: compute time | 40–150 seconds | ≈84 GPU hours |
| Open models: estimated rental expenditure | **≈€0.06** | **≈€235** |
| GPT-5: estimated API expenditure | **≈€0.08** | **≈€313** |

Calculation and assumptions:

- **Rental reference:** OVHcloud `h100-380`, one H100 80 GB, **€2.80/hour excluding VAT**, checked on 30 October 2026. [Official price list](https://www.ovhcloud.com/en-ie/public-cloud/prices/).
- 84 × €2.80 = **€235.20**; €235.20 / 3,917 = **€0.06005/document**.
- The 84-hour figure is a representative configuration, not the extrapolation of the entire 40–150 second range. It is consistent with the manuscript's GPT OSS CoreSchema timing of 76.84 seconds/document: approximately 84 hours for 3,917 PDFs.
- The runtime range spans models/tasks. The manuscript's Table 4 contains the detailed extraction timings.
- The GPT-5 values follow the existing slide's project estimate. Its cited source is project report TL3; the manuscript's monetary-cost cells remain TBD. The user explicitly accepted the slide's values for this presentation.
- These are approximate extraction-resource estimates, not a newly measured, identical-workload cost benchmark. Open-model monetary values are rental equivalents, not recorded expenditure on the project's own cluster.
- No comparable GPT-5 runtime was supplied. Do not invent one.

Suggested takeaway: **“Similar expenditure, different resource requirements.”** Use the same open/proprietary colour convention as the result slides.

Keep assumptions in a small footer or notes: *Estimates for one extraction run; representative configuration; rental equivalent at €2.80/H100-hour excl. VAT; costs depend on model, document length and provider prices.* Avoid letting the explanation dominate the slide.

Remove the existing LGPLv3 claim. No licence name should appear in the revised slide.

### Slide 11 — Tasks and datasets

**Original comments:** add source-type proportions; clarify the language denominator; show that all four trend components belong together; “probably remove this.”

**Agreed layout:** retain the two grey Task 1 / Task 2 panels. Redesign the lower strip rather than restructuring the whole slide.

- Within Task 2, visually group the four fields: habitat, species group, variable, direction. A single enclosing box is sufficient.
- In the lower strip, place compact corpus facts on one side and the combined source-type chart on the other.
- Facts: **German & English; 21–37% of documents in German; up to 2,218 pages.** The language percentages are document shares, not character shares.
- Remove the “Reference / annotations by Faktencheck experts” footer block, which is the apparent target of the removal comment. This should not remove needed explanations elsewhere about the reference data.

**Scale wording:** use **“≈1,500 document inputs across development and testing.”** The four sets contain 100 + 500 + 468 + 430 = **1,498 inputs**. This is a sum across tasks/splits, not a count of distinct publications. Matching local PDF identifiers yields 1,318 distinct identifiers across all four sets, but that detail need not appear on the slide. Keep the task panels' test sizes at **500** and **430**.

#### Combined source-type chart: verified figures

Use **converted-text character shares**, combining only the two test sets and counting shared documents once. Do not average the separate datasets' percentages.

- Test inputs: 500 + 430 = **930**.
- Shared PDFs: **61**, confirmed byte-identical by SHA-256.
- Unique PDFs: **869**.
- Missing source-type metadata: **4**, excluded from the breakdown.
- Retained: **865 documents, 24,853 pages, 87,913,353 Markdown characters**.

| Source type | Documents | Pages | Markdown characters | Character share |
| --- | ---: | ---: | ---: | ---: |
| Journal articles | 759 | 12,566 | 50,183,056 | **57.08%** |
| Reports | 46 | 6,760 | 20,490,541 | **23.31%** |
| Books and chapters | 39 | 4,490 | 14,536,356 | **16.53%** |
| Other | 21 | 1,037 | 2,703,400 | **3.08%** |
| **Total** | **865** | **24,853** | **87,913,353** | **100.00%** |

Grouping:

- Journal articles: `journalArticle`.
- Reports: `report`.
- Books and chapters: `book` + `bookSection`.
- Other: `conferencePaper`, `dataset`, `document`, `statute`, `thesis`, `webpage`.

These metadata categories are not a verified peer-reviewed/grey-literature classification. Label the chart as **source types by extracted text length**.

**Chart recommendation, considered against a pie:**

| Option | Consideration |
| --- | --- |
| Pie | Intuitive part-of-whole view; four categories are manageable. Needs a roughly square area and room for labels, especially the 3% slice. |
| Horizontal stacked bar | Fits the existing bottom strip and preserves the task panels. Direct labels can show the shares; put “Other” outside its small segment. |

**Default recommendation:** one horizontal stacked bar in the order journal articles → reports → books/chapters → other. A pie is acceptable if the final layout provides enough space; no strong user preference was expressed.

Suggested source note: *Both test sets combined; duplicate documents counted once; source-type metadata available for 865 of 869 unique documents. Shares based on converted-text characters.*

**Reproduction wrinkle:** 11 shared PDFs have different Markdown conversions. Passing both original Markdown folders directly to the statistics command raises a conflicting-content error. Keep the CoreSchema conversion for shared documents in a temporary combined input, matching the PDF folder priority. The PDFs were verified identical; the sum of absolute character-count differences is only 42 characters. Do not weaken the statistics script's conflict checking or edit source datasets.

The complete, tested reproduction instructions and unposted comment for [PR #636](https://github.com/DFKI-NLP/kibad-llm/pull/636) are embedded in Appendix A. The user asked to **prepare** the comment; it has **not** been posted. EDIT: The comment was posted on 2026-10-30, after the handover was prepared. It is now part of the PR discussion [here](https://github.com/DFKI-NLP/kibad-llm/pull/636#issuecomment-6526264782).

### Slide 12 — Information extraction results

Colour-code open-weight versus proprietary models in the chart, then reuse those colours in the “open ≈ commercial” callout. Use a readable, consistent distinction, with labels or patterns if necessary; no exact palette was selected.

The current chart is already a **native, editable PowerPoint chart with embedded values**, despite the comment discussion suggesting it could not be edited. No recreation is required.

Keep the message that the best open models achieve approximately **50 F1 points**, comparable to GPT-5. Manuscript figures: best open-model CoreSchema F1 **50.4**, GPT-5 **45.5**. Replace “of answers match the experts exactly” with accurate F1 wording; see the shared wording guidance below.

### Slide 14 — Recall and precision

Emphasize why recall is especially important **for this expert screening workflow**:

> Experts can reject extra candidates. Recovering missed evidence requires searching or reading again.

This may be a short slide message or a speaking note. Keep precision relevant; the argument is a workflow priority, not a universal claim that precision does not matter. 

- Existing values are the open-model test means: **74.1% recall** and **34.2% precision**, rounded on the slide to 74% and 34%.
- Explain these relative to the reference annotations. Unmatched predictions include both errors and information omitted from the reference.
- The correction **410 → 914 annotations** concerns the **100-document development set**, not a correction of the test set.

EDIT: As a side note, Julia explained to me that, for the final biodiversity report (not the result of the current LLM pipeline), false positives (low precision) would be more costly than false negatives (low recall) since the report would be used to inform policy decisions and hallucinations are more serious than missing a few pieces of information. But this is more of a side note and not so relevant to the current presentation (which is about the LLM pipeline and its performance).

### Slide 16 — Complete trend extraction results

**Original comments:** resolve the apparent GPT-5/Qwen contradiction and remove the open-model mean.

- Retain individual model results and colour-code open-weight versus proprietary models as on slide 12.
- Remove the “mean of open models” bar and the takeaway claiming GPT-5 is ahead of that average.
- The existing chart is a raster image. Rebuild it as an editable chart using the verified figures below.

| Model | Complete trend extraction, F1 points |
| --- | ---: |
| Gemma 3 27B | 14.1 |
| GPT OSS 20B | 19.2 |
| Mistral Small 3 24B | 13.4 |
| **Qwen 3 30B** | **25.5** |
| GPT-5 | 21.8 |

Suggested takeaway: **“Complete trend extraction remains difficult; the best open model matches or exceeds GPT-5.”**

Suggested comparison callout: **“Best F1: 25.5 points — versus about 50 for document annotations.”** Do not say 25% of trend statements are correct.

An additional manuscript finding fits here without taking content from slide 17:

> GPT-5 has the highest recall; Qwen has the highest precision and F1.

For complete trend extraction, GPT-5 recall is **48.6%** (37.8% for Qwen); Qwen precision is **19.3%**, compared with GPT-5's **14.0%**. A short sentence is sufficient; avoid another chart. Reserve the task breakdown for slide 17. EDIT: Context is the "recall is more important then precision" statement from slide 14. Also, with 45.5% recall, the open model Gemma 3 provides a comparible resutl as GPT-5 in that means. And low precision values may be not reliable (also see slide 14 for jump in precision after manually correcting the dev set). However, we should not overload this slide.

### Slide 17 — Detection versus categorisation

**Final decision:** use **version B**, showing **Qwen 3 only**, not GPT-5 or an average across open-weight model families. The variable is part of the detected trend target; categorisation assigns its direction. Qwen 3 was the best open model for complete trend extraction. Means and SDs summarize repeated seeds of this one model.

**Verified checkpoint:** `Qwen/Qwen3-30B-A3B-Thinking-2507`.

| Evaluation | Qwen F1 points, mean ± sample SD |
| --- | ---: |
| Detection: habitat + species group + variable | **37.3 ± 1.1** |
| Direction categorisation, conditional on a matched triple | **66.9 ± 1.5** |
| Complete four-field extraction | **25.5 ± 1.2** |

These scores were recomputed from the three existing prediction runs with seeds **42, 1337, 7331** from the corrected agricultural/open-land test experiment, **PR #586**. No new LLM inference was run. The complete-extraction result reproduces the original score exactly. Appendix B contains the derivation, raw counts, input paths, checksums, and tested reproduction code.

**These replace the earlier version A diagnostics of 49.6 for habitat–group detection and 47.7 for joint variable/direction categorisation. Do not reuse those numbers with version B labels.** The manuscript's original breakdown uses version A; the new version B diagnostics are a re-evaluation of the same outputs.

#### What the evaluations actually mean

| Evaluation | Matching unit | Treatment of missed/extra targets |
| --- | --- | --- |
| Detection | Document-level **habitat + species group + biodiversity variable** triple, projected from extracted trend tuples; direction ignored. | Both penalized. |
| Conditional categorisation | **Trend direction** labels for triples present in both prediction and reference. | Triples found on only one side are excluded. |
| Complete extraction | Exact **habitat + species group + variable + direction** tuple. | Both penalized. |

The distinction is between identifying **what changes** and assigning **how it changes**. The variable belongs to the target because abundance, species number, and effective species number can have different trends for the same habitat and organism group. This is a choice of evaluation identity, not a claim that biodiversity variables cannot be mentioned outside trend statements.

Example reference: `agricultural land · birds · abundance · negative`.

- Predicting the same habitat, species group, and variable with a **positive** direction succeeds at detection but fails at categorisation and complete extraction.
- Predicting **species richness** instead of abundance is a missed reference target plus an extra predicted target. That unmatched triple is excluded from the conditional direction score.
- Reference and prediction directions are compared as **sets per document and triple**, not as one mandatory direction label. Multiple directions may describe different observations, subgroups, places, or periods not distinguished by the evaluated schema.
- There are **270 reference triples**, compared with 225 habitat–group pairs. Of those pairs, **43 involve multiple variables**. **22 reference triples have multiple direction labels**. Even the three-field target is therefore not a unique identifier for every evidence passage or underlying observation.

Useful existing files, relative to the repository root:

- `configs/experiment/evaluate/organism_trends_f1_micro.yaml`: full-tuple F1; version B detection uses the same metric while additionally ignoring `Trend`.
- `configs/experiment/evaluate/organism_trends_confusion_matrix_conditional_trend_only.yaml`: already groups by habitat, group, and variable and scores direction; the new calculation uses that grouping with the F1 metric.
- `src/kibad_llm/metrics/f1.py` and `src/kibad_llm/metrics/collection.py`: the existing micro-F1 and conditional grouping implementations.

#### Suggested slide arrangement and interpretation

Show **“Identify the trend target: 37.3”** and **“Assign its direction: 66.9”** as two diagnostic panels, with a visually separate **“Complete extraction: 25.5”** panel below or alongside them. Explicitly label the direction score **“on correctly matched targets.”**

Suggested takeaway:

> Finding the correct trend target is challenging; direction assignment works better once that target is found.

The direction score is conditional on successful target matching, so it does not describe direction performance on missed or extra targets, or establish the performance of an independently run classifier supplied with gold targets. This is a **diagnostic breakdown, not an arithmetic decomposition**: do not add or multiply the F1 values or use a waterfall/stacked chart implying that relationship. Use a common 0–100 F1 axis where appropriate. Remove the old variable-only 71.5-point callout, which belongs to version A.

### Slide 25 — Legal/governance, hidden

**Resolved by omission.** Remove this slide from the finished presentation. Do not seek Luisa's review or undertake legal research for this talk. Preserve the rest of the backup organization unless another change is necessary for consistency. EDIT: This can just stay there for now as hidden slide or backup slide.

### New backup slide — Which trend directions does Qwen identify?

**Add this slide in the backup section**, after the existing Backup divider. It supports questions about slide 17 and does not extend the main talk sequence. No new slide has been created yet; these are the implementation instructions.

**Scope:** Qwen 3 only, version B direction categorisation on correctly matched habitat–species-group–variable triples, using the three existing seeds. Include **all five direction categories** separately in both the matrix and the summary:

1. **Negative**
2. **Neutral** (the schema's `no` label)
3. **Positive**
4. **Positive → negative**
5. **Negative → positive**

Do not merge the two transition categories, fold them into “Other,” or omit them because their support is small. Each transition describes a change in trend direction over time and is one distinct label; do not split it into two simple direction labels.

**Agreed takeaway (visible on the backup slide):**

> Qwen recovers increases and declines more reliably than stability or trend reversals.

**Supporting line, using rounded recall figures:**

> On matched targets, recall is 97% for declines and 82% for increases, versus 52% for neutral trends and 29–39% for reversals.

Keep the qualification **“Few reference examples for reversals.”** visible. The takeaway describes recall within matched targets; it does not imply that all predicted increases or declines are correct. Keep the precision values in the accompanying table.

**Suggested layout:**

- **Title:** “Which trend directions does Qwen identify?”
- **Subtitle:** “Direction categorisation on correctly matched targets · Qwen 3 · three seeds.”
- **Left, about 60% of the body:** heatmap of the full **6×6 alignment-averaged confusion matrix** from Appendix C. Reference labels are rows; predicted labels are columns. Keep all five direction categories, plus the **Unassigned prediction** row and **Missing direction** column. Use wrapped transition labels and readable cell annotations. Counts are means across the three seeds, not pooled counts of independent observations.
- **Right, about 35%:** the compact five-category precision/recall table below, with reference support. These are exact per-direction presence/absence diagnostics, independent of the off-diagonal alignment convention.
- **Takeaway callout:** the agreed sentence above, near the bottom; use the supporting line if space permits.
- **Footer:** “Matched targets only. Matrix off-diagonals are alignment-averaged error allocations; transition categories have low support.”

| Direction | Precision | Recall | Reference labels per seed |
| --- | ---: | ---: | ---: |
| Negative | **66.9%** | **97.4%** | 64–65 |
| Neutral | **52.5%** | **51.5%** | 29–31 |
| Positive | **47.6%** | **82.5%** | 35–39 |
| Positive → negative | **44.4%** | **38.9%** | 2–3 |
| Negative → positive | **66.7%** | **28.6%** | 7 |

Precision and recall are arithmetic means of the three per-seed ratios. Support is the number of reference direction labels within each seed's matched triples; it is neither the number of documents nor the full test-set support. Show the per-seed range rather than adding the same reference information across repeated runs. The overall conditional micro-F1 remains **66.9 ± 1.5 points**, as on slide 17; the per-category table is not averaged to obtain that micro-F1.

**Speaking notes / interpretation:**

- Negative directions are rarely missed within the matched targets, but additional negative labels reduce precision. Positive directions also have relatively high recall with lower precision; neutral directions are less reliably recovered.
- **Both complex directions must be discussed:** Positive → negative has 38.9% recall on only 2–3 reference labels per seed; Negative → positive has 28.6% recall on 7. Their low recall is relevant, but the small support prevents a strong comparison between them or a general conclusion about all complex trends.
- The matrix is a multi-label exploratory diagnostic. Off-diagonal entries do not count directly observed label swaps, and diagonal/total is not an accuracy score. Explain the alignment rule in questions if necessary; the example and exact reproduction are in Appendix C.
- Missing/extra labels in the matrix occur **within matched triples**. Missed or extra triples are outside this conditional analysis and are covered by the detection score on slide 17.
- The reference is known to be incomplete, so unmatched predictions are not automatically scientifically incorrect.

Use Appendix C's embedded matrix values and reproduction code as the durable source; do not depend on temporary plot files from the analysis session. Rebuild/export the chart when the slides are finalized. No change to the repository's confusion-matrix implementation is needed.

## Shared wording and consistency

### Making F1 understandable

Use **“F1 points — higher is better”** on a 0–100 scale. An introductory explanation can be:

> F1 balances finding the reference information with avoiding unmatched answers. 100 points means complete agreement with the reference.

Then use concise callouts such as “50 F1 points” and “25.5 F1 points.” Avoid “50% of answers are correct,” “25% of statements are fully correct,” or treating F1 as accuracy. Precision and recall may still be expressed as percentages.

Use slide 14 to explain the practical meaning of recall/precision. Keep the imperfect reference in mind: unmatched predictions are not automatically scientifically incorrect. Use observed test results as the headline results; the development-set correction is a separate finding.

### Models, colours, and comparisons

- Prefer **open-weight models** and **proprietary model / commercial API** as labels.
- Use one consistent distinction on slides 12 and 16 and, where useful, slide 10.
- Slide 17 contains Qwen only. No cross-model mean or GPT-5 series is wanted there.
- Preserve exact model/checkpoint identities in notes or sources; short model names are sufficient on the slide.
- Keep manuscript results and chart labels on the same scale. Convert 0.255 to 25.5 points, not to 0.255 points.

### Dataset denominators

- **≈1,500 inputs:** development + testing, summed across four sets.
- **500 / 430:** the two task test-input counts.
- **869:** unique PDFs across the two test sets.
- **865:** unique PDFs retained for the source-type chart after four missing-metadata exclusions.
- **21–37% German:** document shares for the two test sets, as reported in the manuscript.
- **Source-type chart percentages:** character shares among the retained, deduplicated test documents.

These counts describe different scopes and can coexist when their labels are clear. Do not label the combined chart “930 distinct documents” or the scale teaser “1,500 test documents.”

## Source and analysis inventory

All paths in this section are relative to the `kibad-llm` repository root unless stated otherwise.

| Source | Purpose |
| --- | --- |
| `presentations/2026_feda_status_conference/Manuscript draft KIBA D.docx` | Primary scientific background; methods and evaluation definitions; dataset Table 2; results; extraction timing Table 4. |
| `../kibad-crawler/` | Implementation evidence for the short literature-discovery slide. |
| `src/kibad_llm/statistics/pdf.py` | Existing statistics CLI, now available on `feat/pdf-stats`. |
| `data/cluster-mirror/splits/test/` | CoreSchema test PDFs. |
| `data/cluster-mirror/test-set-AuO-WVC/` | OrganismTrends test PDFs. |
| `data/kibad-llm-results/data/processed/faktencheck/test/` | Converted CoreSchema test Markdown in JSONL files. |
| `data/kibad-llm-results/data/processed/faktencheck/test-set-AuO-WVC/` | Converted OrganismTrends test Markdown in JSONL files. |
| `data/external/faktencheck-db/Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv` | Source-type metadata. |
| `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/` | Corrected trend experiment: README, raw evaluation results, chart exports, prediction configurations. |

Pinned inputs used for the calculations:

- Statistics branch revision: `f676b27cfdc7f80d74c552b698fbd9b3261b7560` (`feat/pdf-stats`).
- Results repository revision: `dc7afea1bcc5af89b8e400712b4886079e301256`.
- Metadata SHA-256: `4e4c5657f39a25982c932263e9ff8721b58244632c8053fd6c6cce05c240ec08`.

GitHub provenance:

- [PR #636: PDF statistics and individual-dataset tables](https://github.com/DFKI-NLP/kibad-llm/pull/636).
- [Issue #521: publication experiment plan](https://github.com/DFKI-NLP/kibad-llm/issues/521), especially the [final experiment summary](https://github.com/DFKI-NLP/kibad-llm/issues/521#issuecomment-5660062464).
- [Issue #583: incorrect forest-specific prompt and rerun](https://github.com/DFKI-NLP/kibad-llm/issues/583).
- [PR #586: corrected trend test experiment](https://github.com/DFKI-NLP/kibad-llm/pull/586).
- [PR #549: original trend test experiment, superseded](https://github.com/DFKI-NLP/kibad-llm/pull/549).
- [Issue #207: repeated runs and averaging](https://github.com/DFKI-NLP/kibad-llm/issues/207).

Some later discussion in issue #383 still refers to #549. The corrected experiment history and numerical checks establish #586 as the source matching the current manuscript values; see Appendix B.

## Completion checklist

- [ ] Simplify slide 7 and keep crawling brief; distinguish planned work and omit unsupported peripheral claims if no ready source exists.
- [ ] Rebuild slide 8's extraction output as coloured columns/boxes with an ellipsis.
- [ ] Add slide 8's three reveals and verify text/annotation alignment.
- [ ] Correct slide 9's footer.
- [ ] Reformat slide 10 with concrete resource/cost estimates and a concise assumption note; remove the licence claim.
- [ ] Keep slide 11's task panels, group the four trend fields, and replace the lower strip with facts and one combined source-type chart.
- [ ] Use the agreed ≈1,500-input wording and correct denominators.
- [ ] Apply open/proprietary colours on slide 12 and correct the F1 wording.
- [ ] Emphasize the recall priority on slide 14, keeping development/test findings separate.
- [ ] Rebuild slide 16's chart without the open-model mean, apply the colour convention, and correct its takeaway/F1 wording.
- [ ] Rebuild slide 17 for Qwen only using version B: detection 37.3, conditional direction categorisation 66.9, complete extraction 25.5; label the conditional subset.
- [ ] Add the Qwen direction-categorisation backup slide with all five classes, including both transition directions, the full matrix, per-class precision/recall, and support/caveat labels.
- [ ] Omit slide 25.
- [ ] Check wording, charts, footers, builds, hidden/backup slides, and readability in the actual presentation application.
- [ ] Confirm all 14 comment threads are addressed or deliberately omitted as documented; resolve comments after checking the edits.
- [ ] Preserve the supplied original and deliver a clearly named finished PPTX. If exporting a PDF, confirm the intended final build state is visible.

The remaining choices are routine implementation details: precise colours, spacing, native build mechanics, and whether the available space favors the recommended stacked bar or a pie. There is no outstanding scientific-data requirement for the agreed edits.

## Appendix A — Qwen results and averaging provenance

Moved to [PR #636 comment](https://github.com/DFKI-NLP/kibad-llm/pull/636#issuecomment-6526264782).

## Appendix B — Version B: Qwen results, derivation, and reproduction

This appendix supersedes the earlier version A slide diagnostics. Version B changes the evaluation projection and conditioning; the predictions, reference labels, checkpoint, and three seeds remain the same. Only this handover was updated; the slides and source data were not changed. No logs or predictions were copied.

### Inputs and provenance

- Checkpoint: `Qwen/Qwen3-30B-A3B-Thinking-2507`.
- Source experiment: [PR #586](https://github.com/DFKI-NLP/kibad-llm/pull/586), following [issue #583](https://github.com/DFKI-NLP/kibad-llm/issues/583). It corrects the forest-specific prompt and missing prediction inputs in the earlier #549/#574 trend runs.
- Test habitat: Agrar- und Offenland; **430 prediction records per seed**, including documents without reference trends.
- Prediction prompt override: `organism_trends_v1_with_chunking_AuO`.
- Seeds: **42, 1337, 7331**; model override `qwen3_30b_in_process`.
- Original results repository revision: `dc7afea1bcc5af89b8e400712b4886079e301256`.
- Re-evaluation used the existing metric implementation at `kibad-llm` revision `a397ac2efe0798a3ec79096349f3fa6b93c05164`.
- Reference CSV: `data/external/organism_trends/Weighted Vote Count Agrar- und Offenland Literatur - Sheet1.csv`.
- Reference CSV SHA-256: `b4995a46fcd3f950f8fb3bb49c532929a40107c76c1a14dd0bbd4c41d600a350`.

Original evaluation metadata is located under:

```text
data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/
  evaluate/multiruns/2026-09-03_14-46-39/{6,7,8}/job_return_value.json
```

Jobs 6, 7, and 8 correspond to seeds 42, 1337, and 7331. Their metadata identifies the prediction file for each run. The three prediction files are below `data/kibad-llm-results/predictions/586_organism_trends_bestconfig_testset_rerun/2026-08-27_16-03-08/`:

- Seed 42: `2026-08-27_16-03-10_301281/predictions.jsonl`; SHA-256 `283973272d29a0626328701aa294412c375a4713debdda121544f59be0025d7d`.
- Seed 1337: `2026-08-28_00-51-21_102508/predictions.jsonl`; SHA-256 `3c821888db2f5215ae28feff4602c0f69f955867ec8ff9ccacfae4213c8a7363`.
- Seed 7331: `2026-08-28_09-41-01_994483/predictions.jsonl`; SHA-256 `5c9836edf87eaaab01d59fb3cd82b0863e8cdc1a0d85022c84484056a1a41c20`.

### Exact derivation

Use the existing `F1MicroMultipleFieldsMetric`, reporting its **`ALL` micro-average**, not the `AVG` macro-average:

1. **Detection B:** compare sets of `(habitat, group, variable)` triples per document. Ignore `Trend` and `Untergruppe_RoteListen`. Include missed and extra triples.
2. **Direction categorisation B:** group each document's tuples by `(habitat, group, variable)`; compare sets of `Trend` values only for groups present in both prediction and reference (`ignore_missing_entries=True`). Exclude unmatched triples.
3. **Complete extraction:** compare full four-field tuples, ignoring `Untergruppe_RoteListen`, as in the original experiment.
4. Retain all prediction documents. Missing reference records are empty reference sets (`allow_missing_references=True`); they can contribute false positives to detection and complete extraction. Missing predictions for reference documents remain an error.
5. Within each seed, pool TP/FP/FN over documents and compute precision, recall, and F1. Average the **three run-level scores** and report the **sample SD (`ddof=1`)**. Multiply by 100 for F1 points and precision/recall percentages. Do not pool repeated seeds, average model families, or calculate F1 from averaged precision and recall.

The computations use exact enum-label matching and set deduplication per document. They do not score evidence spans or distinct observations sharing the same evaluated fields. A neutral/no-change direction (`no`) counts as a trend category, not as absence of a detected target.

### Per-seed F1 points

| Evaluation | Seed 42 | Seed 1337 | Seed 7331 | Mean F1 points | Sample SD (points) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Detection B: habitat + group + variable | 36.079545 | 38.081395 | 37.685460 | 37.282134 | 1.060120 |
| Direction categorisation B, conditional | 67.283951 | 68.221574 | 65.243902 | 66.916476 | 1.522469 |
| Complete extraction | 24.660633 | 26.896552 | 25.000000 | 25.519062 | 1.204949 |

### Raw counts

| Seed | Evaluation | TP | FP | FN | Reference support (TP + FN) |
| --- | --- | ---: | ---: | ---: | ---: |
| 42 | Detection B: habitat + group + variable | 127 | 307 | 143 | 270 |
| 42 | Direction categorisation B, conditional | 109 | 77 | 29 | 138 |
| 42 | Complete extraction | 109 | 481 | 185 | 294 |
| 1337 | Detection B: habitat + group + variable | 131 | 287 | 139 | 270 |
| 1337 | Direction categorisation B, conditional | 117 | 83 | 26 | 143 |
| 1337 | Complete extraction | 117 | 459 | 177 | 294 |
| 7331 | Detection B: habitat + group + variable | 127 | 277 | 143 | 270 |
| 7331 | Direction categorisation B, conditional | 107 | 82 | 32 | 139 |
| 7331 | Complete extraction | 107 | 455 | 187 | 294 |

Detection always has 270 reference triples. Conditional direction support varies by seed because only correctly matched triples are retained. It can exceed the number of matched triples (127, 131, 127) because a triple can have multiple reference directions. Full extraction has 294 reference four-tuples. These supports are counts of evaluated labels/tuples, not document counts.

### Summary, mean ± sample SD on a 0–100 scale

| Evaluation | Precision (%) | Recall (%) | F1 points |
| --- | ---: | ---: | ---: |
| Detection B: habitat + group + variable | 30.679343 ± 1.227810 | 47.530864 ± 0.855334 | 37.282134 ± 1.060120 |
| Direction categorisation B, conditional | 57.905302 ± 1.119677 | 79.260702 ± 2.431590 | 66.916476 ± 1.522469 |
| Complete extraction | 19.275407 ± 0.941465 | 37.755102 ± 1.799831 | 25.519062 ± 1.204949 |

### Checks performed

- Verified the model, corrected AuO prompt, seeds, and 430 prediction records per run against the source metadata.
- Recomputed complete extraction and reproduced the original precision, recall, F1, and support for all three seeds to numerical tolerance `1e-12`.
- Recomputed all three old diagnostics (habitat–group detection, conditional variable-only, conditional variable+direction) and reproduced their saved scores/supports at the same tolerance. This checks that the same data loading and reference conventions are used.
- Independently reproduced TP/FP/FN for both version B diagnostics and complete extraction with plain set operations, without the project's metric classes. All counts agree.
- Ran the reproduction code below and confirmed the same new scores.

### Reproduction from the repository root

Use the existing project environment with dependencies installed. The following command reads the existing files, computes the three requested metrics, checks complete extraction against the saved original results, and prints the raw counts and summaries. It performs no inference and writes no files:

```bash
.venv/bin/python - <<'PYTHON'
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from statistics import mean, stdev

from kibad_llm.dataset.csv import read_grouped_csv_records
from kibad_llm.dataset.json import read_and_preprocess
from kibad_llm.dataset.utils import merge_references_into_predictions
from kibad_llm.metrics.f1 import F1MicroMultipleFieldsMetric
from kibad_llm.utils.path import strip_filename_extension

root = Path("data/kibad-llm-results")
run = root / "logs/586_organism_trends_bestconfig_testset_rerun"
csv = Path("data/external/organism_trends/Weighted Vote Count Agrar- und Offenland Literatur - Sheet1.csv")
assert sha256(csv.read_bytes()).hexdigest() == "b4995a46fcd3f950f8fb3bb49c532929a40107c76c1a14dd0bbd4c41d600a350"
field = "organism_trends"
h, s, v, d = "Lebensraum", "Hauptgruppe_RoteListen", "Antwortvariable", "Trend"
sub = "Untergruppe_RoteListen"
configs = {
    "detection_B": {"ignore_subfields": {field: [d, sub]}},
    "direction_B": {
        "subfield_keys": {field: [h, s, v]},
        "subfield_values": {field: [d]},
        "ignore_missing_entries": True,
    },
    "complete": {"ignore_subfields": {field: [sub]}},
}
references = read_grouped_csv_records(
    file=str(csv), output_key=field, columns=[s, sub, h, v, d]
)
samples = {name: [] for name in configs}
for job in (6, 7, 8):
    source = run / f"evaluate/multiruns/2026-09-03_14-46-39/{job}/job_return_value.json"
    saved = json.loads(source.read_text())
    metadata = saved["prediction"]
    assert metadata["overrides"]["extractor/llm"] == "qwen3_30b_in_process"
    assert metadata["overrides"]["extractor/prompt_template"] == "organism_trends_v1_with_chunking_AuO"
    predictions = read_and_preprocess(
        file=root / metadata["job_return_value"]["output_file"],
        id_key="file_name", process_id=strip_filename_extension,
        preprocess=lambda row: row.get("structured"),
    )
    assert len(predictions) == 430
    dataset = merge_references_into_predictions(
        predictions=predictions, references=references,
        allow_missing_references=True,
    )
    print("Seed", metadata["overrides"]["seed"])
    for name, options in configs.items():
        metric = F1MicroMultipleFieldsMetric(fields=[field], **options)
        for record_id, example in dataset.items():
            metric.update(prediction=example["prediction"], reference=example["reference"], record_id=record_id)
        counts = {
            k: sum(m.state_count[k] for m in metric.metrics.values())
            for k in ("tp", "fp", "fn")
        }
        scores = metric.compute()["ALL"]
        if name == "complete":
            assert all(isclose(scores[k], saved["data"]["ALL"][k], abs_tol=1e-12)
                       for k in ("precision", "recall", "f1", "support"))
        samples[name].append(scores)
        print(name, json.dumps({**scores, **counts}, sort_keys=True))
print("Mean +/- sample SD, on a 0-100 scale:")
for name, rows in samples.items():
    for metric in ("precision", "recall", "f1"):
        values = [100 * row[metric] for row in rows]
        print(name, metric, f"{mean(values):.6f} +/- {stdev(values):.6f}")
PYTHON
```

The output's F1 summaries are:

```text
detection_B f1 37.282134 +/- 1.060120
direction_B f1 66.916476 +/- 1.522469
complete f1 25.519062 +/- 1.204949
```

### Difference from the earlier diagnostics

Version A used habitat + group as the detected identity and variable + direction as the conditional payload. Its Qwen F1 scores were 49.551929 for detection, 71.495195 for conditional variable-only, and 47.693695 for conditional variable+direction. Those remain valid under that older definition, but are not version B scores.

The earlier manuscript averages were obtained by averaging each model's three run-level micro-F1 scores and then taking an equal-weight mean across the four open-weight models. They are retained only as historical context; slide 17 now uses Qwen alone and version B. Full extraction is unchanged at 25.519062 F1 points.

The higher conditional direction score in version B reflects both a narrower task (direction only) and selection of correctly identified triples. It is not an improvement to the underlying model, does not cover unmatched targets, and cannot be multiplied by detection F1 to recover the complete-extraction score.

## Appendix C — Conditional direction confusion matrix (version B)

The Qwen direction confusion matrices were calculated using the existing **`ConfusionMatrixCollection`** implementation, with the grouping already specified in `configs/experiment/evaluate/organism_trends_confusion_matrix_conditional_trend_only.yaml`: keys = habitat + species group + variable; value = direction; `ignore_missing_entries=True`. No metric implementation or configuration was changed. The inputs are the same three PR #586 prediction runs and reference CSV as Appendix B.

### What the existing code measures

This is a **multi-label, alignment-averaged confusion matrix**, not a conventional single-label confusion matrix. After exact matches are assigned to the diagonal, the code distributes unmatched reference/prediction labels uniformly over all partial one-to-one alignments. Unpaired reference labels go to `UNDETECTED`; unpaired predictions go to `UNASSIGNABLE`. The off-diagonal cells are expected error allocations under that rule, not observed label swaps or uncertainty estimates.

For example, reference `{negative}` and prediction `{positive}` contribute **0.5** to negative→positive, **0.5** to negative→missing, and **0.5** to unassigned→positive. A conventional single-label matrix would put 1 into negative→positive. This difference is deliberate in the existing implementation and must be explained when showing its output.

Here, only **220 of 385 matched target occurrences across the three seeds (57.1%)** have exactly one reference and one predicted direction. The remainder are multi-label on at least one side. A conventional 5×5 matrix restricted to the singleton subset would exclude 42.9% of the matched targets and describe a different evaluation population.

### Matrix: mean counts across seeds

Rows are reference labels; columns are predicted labels. “Neutral” displays the schema's `no` label. The five direction labels plus the extra row/column must be retained; hiding the extra row would hide a substantial part of the mismatch. Fractional values arise both from alignment averaging within a run and averaging the three runs.

| Reference \ Predicted | Negative | Neutral | Positive | Positive → negative | Negative → positive | Missing direction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Negative | 62.67 | 0.00 | 0.44 | 0.00 | 0.00 | 1.22 |
| Neutral | 2.44 | 15.33 | 3.56 | 0.00 | 0.00 | 8.33 |
| Positive | 1.11 | 1.00 | 30.00 | 0.28 | 0.00 | 3.94 |
| Positive → negative | 0.67 | 0.17 | 0.00 | 1.00 | 0.00 | 0.83 |
| Negative → positive | 1.11 | 0.00 | 0.94 | 0.00 | 2.00 | 2.94 |
| Unassigned prediction | 25.67 | 13.17 | 28.06 | 1.06 | 1.00 | 0.00 |

“Missing direction” and “unassigned prediction” concern labels **within matched triples**. They do not represent missed or extra triples: those were excluded by the conditional evaluation. Do not interpret the bottom-right cell as true negatives. The sum of all matrix cells is not a conventional sample count, and diagonal/total is not an accuracy measure.

### Exact per-direction diagnostics

The following are observed binary presence/absence counts for each direction within matched triples. They do not require assigning an unmatched reference label to an unmatched prediction label. Counts are means across seeds; precision and recall are means of the three per-seed ratios, consistent with Appendix B's reporting convention.

| Direction | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Negative | 62.67 | 31.00 | 1.67 | 66.9% | 97.4% |
| Neutral | 15.33 | 14.33 | 14.33 | 52.5% | 51.5% |
| Positive | 30.00 | 33.00 | 6.33 | 47.6% | 82.5% |
| Positive → negative | 1.00 | 1.33 | 1.67 | 44.4% | 38.9% |
| Negative → positive | 2.00 | 1.00 | 5.00 | 66.7% | 28.6% |

Relative to the reference, negative directions are rarely missed, but the model also adds negative labels; neutral trends are recovered less reliably. Transition categories have low support and should not drive a strong conclusion. Unmatched predictions are not automatically scientifically incorrect, given the known incompleteness of the reference.

### Verification and recommendation

Per-seed diagonal totals are **109, 117, 107**, exactly matching the conditional F1 true positives. Real-reference row sums are **138, 143, 139**, matching its supports. Real-prediction column sums are **186, 200, 189**, matching TP + FP. Independently computed per-direction TP/FP/FN also sum to the conditional metric's totals. These checks ensure the matrix uses the same evaluated subset as the **66.9 ± 1.5 F1-point** result.

The existing code is suitable for the requested **backup slide**. Keep the conditional F1 score as the main slide's headline; use the full matrix and a five-category precision/recall breakdown on the backup slide specified above. Include **Positive → negative** and **Negative → positive** separately, with their low reference support visible. A matrix shown publicly should be explicitly labelled **“alignment-averaged, multi-label; matched targets only.”**

### Reproduction

Run from the repository root using the existing environment and inputs. This prints per-seed matrices, their mean, exact binary diagnostics, the singleton-subset matrix, and the verification counts as JSON. It does not perform inference or modify the input files. To save the output, redirect stdout to a scratch JSON file.

```bash
.venv/bin/python - <<'PYTHON'
"""Existing repo confusion matrix for Qwen version-B conditional categorisation."""

from ast import literal_eval
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from statistics import mean

from kibad_llm.dataset.csv import read_grouped_csv_records
from kibad_llm.dataset.json import read_and_preprocess
from kibad_llm.dataset.utils import merge_references_into_predictions
from kibad_llm.metrics import ConfusionMatrixCollection, F1MicroMultipleFieldsMetric
from kibad_llm.utils.path import strip_filename_extension

ROOT = Path("data/kibad-llm-results")
RUN = ROOT / "logs/586_organism_trends_bestconfig_testset_rerun"
CSV = Path("data/external/organism_trends/Weighted Vote Count Agrar- und Offenland Literatur - Sheet1.csv")
FIELD = "organism_trends"
H, S, V, D = "Lebensraum", "Hauptgruppe_RoteListen", "Antwortvariable", "Trend"
LABELS = ["negative", "no", "positive", "positive to negative", "negative to positive"]
OPTIONS = dict(fields=[FIELD], subfield_keys={FIELD: [H, S, V]}, subfield_values={FIELD: [D]}, ignore_missing_entries=True)
assert sha256(CSV.read_bytes()).hexdigest() == "b4995a46fcd3f950f8fb3bb49c532929a40107c76c1a14dd0bbd4c41d600a350"
refs = read_grouped_csv_records(file=str(CSV), output_key=FIELD, columns=[H, S, V, D, "Untergruppe_RoteListen"])


def label(s):
    return s if s in ("UNDETECTED", "UNASSIGNABLE") else dict(literal_eval(s))[D]


def groups(entry):
    result = defaultdict(set)
    for trend in (entry or {}).get(FIELD) or []:
        result[tuple(trend[k] for k in (H, S, V))].add(trend[D])
    return result


report = {"rows": LABELS + ["UNASSIGNABLE"], "columns": LABELS + ["UNDETECTED"], "runs": []}
for job in (6, 7, 8):
    source = RUN / f"evaluate/multiruns/2026-09-03_14-46-39/{job}/job_return_value.json"
    saved = json.loads(source.read_text())
    metadata = saved["prediction"]
    assert metadata["overrides"]["extractor/llm"] == "qwen3_30b_in_process"
    assert metadata["overrides"]["extractor/prompt_template"] == "organism_trends_v1_with_chunking_AuO"
    predictions = read_and_preprocess(file=ROOT / metadata["job_return_value"]["output_file"], id_key="file_name", process_id=strip_filename_extension, preprocess=lambda x: x.get("structured"))
    assert len(predictions) == 430
    dataset = merge_references_into_predictions(predictions=predictions, references=refs, allow_missing_references=True)
    cm = ConfusionMatrixCollection(**OPTIONS)
    f1 = F1MicroMultipleFieldsMetric(**OPTIONS)
    binary = {v: Counter(tp=0, fp=0, fn=0, tn=0) for v in LABELS}
    singles = Counter()
    group_types = Counter()
    total_matched = 0
    for record_id, example in dataset.items():
        cm.update(prediction=example["prediction"], reference=example["reference"], record_id=record_id)
        f1.update(prediction=example["prediction"], reference=example["reference"], record_id=record_id)
        pg, rg = groups(example["prediction"]), groups(example["reference"])
        for key in pg.keys() & rg.keys():
            p, r = pg[key], rg[key]
            total_matched += 1
            group_types[(len(r), len(p))] += 1
            if len(r) == len(p) == 1:
                singles[(next(iter(r)), next(iter(p)))] += 1
            for v in LABELS:
                binary[v]["tp" if v in r and v in p else "fn" if v in r else "fp" if v in p else "tn"] += 1
    counts = {k: sum(m.state_count[k] for m in cm.metrics.values()) for k in ("tp", "fp", "fn")}
    fm = f1.compute()["ALL"]
    aggregated = Counter()
    for matrix in cm.compute().values():
        for gold, columns in matrix.items():
            for pred, value in columns.items():
                aggregated[(label(gold), label(pred))] += value
    dense = [[aggregated[(r, c)] for c in report["columns"]] for r in report["rows"]]
    assert isclose(sum(aggregated[(v, v)] for v in LABELS), counts["tp"])
    assert isclose(sum(aggregated[(r, c)] for r in LABELS for c in report["columns"]), fm["support"])
    assert isclose(sum(aggregated[(r, c)] for r in report["rows"] for c in LABELS), counts["tp"] + counts["fp"])
    assert sum(v["tp"] for v in binary.values()) == counts["tp"]
    assert sum(v["fp"] for v in binary.values()) == counts["fp"]
    assert sum(v["fn"] for v in binary.values()) == counts["fn"]
    assert all(sum(v.values()) == total_matched for v in binary.values())
    report["runs"].append({"seed": metadata["overrides"]["seed"], "matched_triples": total_matched, "group_cardinalities": {str(k): v for k, v in sorted(group_types.items())}, "tp_fp_fn": counts, "conditional_scores": fm, "matrix": dense, "binary": binary, "single_label_subset_n": sum(singles.values()), "single_label_subset_matrix": [[singles[(r, c)] for c in LABELS] for r in LABELS]})
report["mean_matrix"] = [[mean(x["matrix"][i][j] for x in report["runs"]) for j in range(6)] for i in range(6)]
report["mean_binary"] = {v: {k: mean(x["binary"][v][k] for x in report["runs"]) for k in ("tp", "fp", "fn", "tn")} for v in LABELS}
report["mean_single_label_subset_matrix"] = [[mean(x["single_label_subset_matrix"][i][j] for x in report["runs"]) for j in range(5)] for i in range(5)]
print(json.dumps(report, indent=2))
PYTHON
```
