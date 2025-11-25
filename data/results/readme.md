## Please describe any files/folders you add to results here!

### 2025-11-21_10-15-33/predictions.jsonl
Contains the predictions on the dev-set-100 PDFs obtained by the run documented in https://github.com/DFKI-NLP/kibad-llm/issues/109.
For the corresponding log file, see /netscratch/hennig/kiba-d/logs/runs/default/2025-11-21_09-28-15/predict.log.

Note that not all PDFs were processed, some were too long and others had JSON decode errors (lines that look like this:
{"file_name":"3WEEGFGW.pdf","structured":null})

Run details:
- Basic + compound types
- Guided decoding
- Prompt - original, based on schema