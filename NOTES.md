- alle eval runs in vier reduzieren und auf ganzem dir laufen lassen
- gpt_oss, gemma und mistral neu evaluieren
- analyse machen
bzgl Analyse:
1. Hauptaussage: chunking best setup (all docs, short chunks) vs. previous results (380_faktencheck_core) --> quite big performance improvements
2. Ablations
2.1 Effect of smaller input sizes: chunking (small docs, short chunks) vs. previous results (380_faktencheck_core, but only small docs) --> ???
2.2 effect of processing all documents: chunking (all docs, large chunks) vs. chunking (small docs, large docs) --> ???
 


- open source the repo - wip

- rerun eval to see what max_char_buffer we should be using

  - with 10 different max_char_buffer values (gpt_oss) - wip

- run second evaluation on large chunks for comparability

- how to document what was adapted from the original code?

- test runs with large chunks and small chunks?

ConditionalUnionExtractor:

- improve prompt for chunking
- improve docs
- whitespace tokenizer
- fix mypy issues
- CAn we get the number of chunks from the prediction outputs???

reference for testing

- data/predictions/readme.md
- https://github.com/DFKI-NLP/kibad-llm/issues/277

./run_in_process.sh -pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-u "-m kibad_llm.predict \
name=277_baseline_faktencheck_core_v1_with_evi \
experiment/predict=faktencheck_core_fields_schema_for_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm/gpt_oss_20b_in_process \
seed=23,42,2048 \
--multirun"
