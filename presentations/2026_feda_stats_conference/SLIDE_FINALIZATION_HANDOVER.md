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
| `presentations/2026_feda_stats_conference/Manuscript draft KIBA D.docx` | Primary scientific background; methods and evaluation definitions; dataset Table 2; results; extraction timing Table 4. |
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
