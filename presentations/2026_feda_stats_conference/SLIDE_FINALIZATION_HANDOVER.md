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
7. Use **Qwen 3 only** on slide 17; remove GPT-5 and the average across open-weight model families from that slide.
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

**Final decision:** show **Qwen 3 only**, not GPT-5 and not the mean across the four open-weight model families. Qwen 3 was the best open model for complete trend extraction. Repeated seeds of this one model may still be summarized with a mean and SD.

**Verified checkpoint:** `Qwen/Qwen3-30B-A3B-Thinking-2507`.

| Evaluation | Qwen F1 points, mean ± sample SD |
| --- | ---: |
| Detection: habitat–species-group pair | **49.6 ± 0.9** |
| Variable alone, conditional on detection | **71.5 ± 1.1** |
| Variable + direction, conditional on detection | **47.7 ± 1.6** |
| Complete four-field extraction | **25.5 ± 1.2** |

These are three repetitions with seeds **42, 1337, 7331** from the corrected agricultural/open-land test experiment, **PR #586**. Do not substitute the older #549 results. Appendix B gives the provenance, individual values and original file paths.

#### What the evaluations actually mean

The existing metrics support a detection/categorisation interpretation, with a specific definition of detection. They are different views of the same predictions; separate inference stages are not required.

| Evaluation | Matching unit | Treatment of missed/extra base pairs |
| --- | --- | --- |
| Detection | Document-level **habitat + species-group pair**, projected from trend tuples; variable/direction ignored. | Both penalized. |
| Conditional categorisation | **Variable + direction** combinations for base pairs present in both prediction and reference. | Pairs found on only one side are excluded. |
| Complete extraction | Exact **habitat + species group + variable + direction** tuple. | Both penalized. |

Example reference: `agricultural land · birds · abundance · negative`.

- Predicting the same habitat and species group with a **positive** direction succeeds at detection but fails at categorisation and complete extraction.
- Missing that base pair hurts detection and complete extraction; it contributes nothing to the conditional categorisation score.
- Several trends with the same habitat–group pair collapse to one detection target. This is not detection of every individual evidence passage or trend statement. Such an evaluation would need a more specific statement identity, variable, or evidence annotation.

Useful configuration files, relative to the repository root:

- `configs/experiment/evaluate/organism_trends_f1_micro_base_entries.yaml`.
- `configs/experiment/evaluate/organism_trends_f1_micro_conditional_variable_only.yaml`.
- `configs/experiment/evaluate/organism_trends_f1_micro_conditional_variable_and_trend.yaml`.
- `configs/experiment/evaluate/organism_trends_f1_micro.yaml`.

#### Suggested slide arrangement and interpretation

Show detection **49.6** and conditional categorisation **47.7** as two diagnostic panels, with a visually separate **complete extraction: 25.5** panel below or alongside them. Add a small callout:

> Identifying the variable is easier; adding trend direction lowers conditional F1 from 71.5 to 47.7.

**Update the old takeaway:** detection is not the sole bottleneck for Qwen. Both finding the relevant pair and assigning the full variable–direction combination remain challenging. The conditionally evaluated subset must be labelled.

This is a **diagnostic breakdown, not an arithmetic decomposition**. The units and evaluated subsets differ; do not multiply/add the F1 values or use a waterfall/stacked chart implying that relationship. Use a common 0–100 F1 axis where appropriate.

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
- [ ] Rebuild slide 17 for Qwen only, using verified values, conditional labels, and the revised interpretation.
- [ ] Omit slide 25.
- [ ] Check wording, charts, footers, builds, hidden/backup slides, and readability in the actual presentation application.
- [ ] Confirm all 14 comment threads are addressed or deliberately omitted as documented; resolve comments after checking the edits.
- [ ] Preserve the supplied original and deliver a clearly named finished PPTX. If exporting a PDF, confirm the intended final build state is visible.

The remaining choices are routine implementation details: precise colours, spacing, native build mechanics, and whether the available space favors the recommended stacked bar or a pie. There is no outstanding scientific-data requirement for the agreed edits.

## Appendix A — Qwen results and averaging provenance

Moved to [PR #636 comment](https://github.com/DFKI-NLP/kibad-llm/pull/636#issuecomment-6526264782).

## Appendix B — Qwen results and averaging provenance

The following analysis records the per-seed results and their original files. Paths inside it are relative to the repository root.

### Qwen 3 trend evaluation: verified presentation values

Checkpoint: `Qwen/Qwen3-30B-A3B-Thinking-2507`. Test habitat: Agrar- und Offenland. Results repository revision: `dc7afea1bcc5af89b8e400712b4886079e301256`.

The corrected test experiment is [PR #586](https://github.com/DFKI-NLP/kibad-llm/pull/586), following [issue #583](https://github.com/DFKI-NLP/kibad-llm/issues/583). It replaces the earlier #549/#574 trend runs, which used forest-specific prompt text and lacked predictions for 11 reference PDFs. [Issue #521](https://github.com/DFKI-NLP/kibad-llm/issues/521#issuecomment-5660062464) identifies #586 as the final test experiment. The later comment on issue #383 mentioning #549 conflicts with that history; the numerical checks below identify #586 as matching the current manuscript.

Every value below was checked against the original per-run `job_return_value.json` files, including the model, corrected AuO prompt, seed, and `data.ALL.f1`. Those numbers match the `figure_data/*-ALL-data.json` samples.

| Evaluation | Seed 42 | Seed 1337 | Seed 7331 | Mean F1 points | Sample SD (points) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Detection: habitat + species-group pair | 48.473968 | 50.181818 | 50.000000 | 49.551929 | 0.937958 |
| Variable, conditional on detected pair | 70.360111 | 72.576177 | 71.549296 | 71.495195 | 1.109023 |
| Variable + direction, conditional on detected pair | 46.881720 | 49.576271 | 46.623094 | 47.693695 | 1.635479 |
| Complete four-field extraction | 24.660633 | 26.896552 | 25.000000 | 25.519062 | 1.204949 |

#### Reconstructing the manuscript averages

Per-run micro-F1 is computed from that run's pooled TP, FP and FN counts. The model result is the arithmetic mean of the three run-level F1 values (seeds 42, 1337, 7331), not F1 recomputed from averaged precision and recall and not a merged prediction ensemble. An equal-weight mean of the four open-model results reproduces the manuscript/slide values:

| Evaluation | GPT OSS | Mistral | Gemma | Qwen | Open-model mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| Detection: habitat + species-group pair | 36.678679 | 34.765966 | 32.252705 | 49.551929 | 38.312320 |
| Variable, conditional on detected pair | 74.420739 | 66.868308 | 73.191206 | 71.495195 | 71.493862 |
| Variable + direction, conditional on detected pair | 46.805258 | 35.243350 | 39.980283 | 47.693695 | 42.430646 |
| Complete four-field extraction | 19.161915 | 13.428457 | 14.107166 | 25.519062 | 18.054150 |

#### Source files

**Detection: habitat + species-group pair**

- Seed 42: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-02/6/job_return_value.json`; support = 225.
- Seed 1337: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-02/7/job_return_value.json`; support = 225.
- Seed 7331: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-02/8/job_return_value.json`; support = 225.

**Variable, conditional on detected pair**

- Seed 42: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-26/6/job_return_value.json`; support = 174.
- Seed 1337: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-26/7/job_return_value.json`; support = 178.
- Seed 7331: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-26/8/job_return_value.json`; support = 175.

**Variable + direction, conditional on detected pair**

- Seed 42: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-44/6/job_return_value.json`; support = 191.
- Seed 1337: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-44/7/job_return_value.json`; support = 195.
- Seed 7331: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-47-44/8/job_return_value.json`; support = 192.

**Complete four-field extraction**

- Seed 42: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-46-39/6/job_return_value.json`; support = 294.
- Seed 1337: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-46-39/7/job_return_value.json`; support = 294.
- Seed 7331: `data/kibad-llm-results/logs/586_organism_trends_bestconfig_testset_rerun/evaluate/multiruns/2026-09-03_14-46-39/8/job_return_value.json`; support = 294.

#### Interpretation

Detection evaluates document-level habitat–species-group pairs projected from predicted/reference trend tuples. Conditional categorisation compares variable–direction sets for pairs found on both sides. Missing/extra pairs are excluded from the conditional score. Full extraction evaluates exact four-field tuples. The units and evaluated subsets differ; the three F1 values do not form an arithmetic decomposition.

For Qwen, detection (49.6 points) and joint variable/direction categorisation on matched pairs (47.7) are both challenging. Variable-only conditional F1 is 71.5; adding direction is a substantial further requirement. The earlier blanket claim that detection is the single bottleneck should be revised.

For slide 17, present Qwen only. Means/SD describe repeated seeds of this one model, with no averaging across model families.
