## Please describe any files/folders you add to results here!

### 2025-11-25_19-49-41/predictions.jsonl
Contains the predictions on the dev-set-100 PDFs obtained by the run documented in 
https://github.com/DFKI-NLP/kibad-llm/issues/109#issuecomment-3576859877.
For a log file to the previous, identical run, see 
/netscratch/hennig/kiba-d/logs/runs/default/2025-11-25_09-23-55/predict.log.

Note that not all PDFs were processed, some were too long and others had JSON decode errors, lines look like this:
{"file_name":"3WEEGFGW.pdf","structured":null,"error_list":["Error code: 400 ..."]}

Run details:
- Basic + compound types
- Guided decoding
- Prompt - original, based on schema



### 2025-12-10_13-36-31 , EcosystemStudyFeaturesMostImportantReduced, gpt-oss-20b
Run with minimal schema v1 "EcosystemStudyFeaturesMostImportantReduced" 
(https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/src/kibad_llm/schema/types.py#L1126C7-L1126C49)
and lengthier prompt instructions: https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/configs/experiment/predict/faktencheck_most_important_schema.yaml

### 2025-12-10_14-48-27 , EcosystemStudyFeaturesMostImportantReduced, qwen3-30b
Run with minimal schema v1 "EcosystemStudyFeaturesMostImportantReduced" 
(https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/src/kibad_llm/schema/types.py#L1126C7-L1126C49)
and lengthier prompt instructions: https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/configs/experiment/predict/faktencheck_most_important_schema.yaml

### 2025-12-11_09-19-30 , EcosystemStudyFeaturesMostImportantReduced, nemotron-nano-12b
Run with minimal schema v1 "EcosystemStudyFeaturesMostImportantReduced" 
(https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/src/kibad_llm/schema/types.py#L1126C7-L1126C49)
and lengthier prompt instructions: https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/configs/experiment/predict/faktencheck_most_important_schema.yaml

### 2025-12-11_09-23-34 , EcosystemStudyFeaturesMostImportantReduced, mistral small 3.2 24b
Run with minimal schema v1 "EcosystemStudyFeaturesMostImportantReduced" 
(https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/src/kibad_llm/schema/types.py#L1126C7-L1126C49)
and lengthier prompt instructions: https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/configs/experiment/predict/faktencheck_most_important_schema.yaml

### 2025-12-11_10-18-31 , EcosystemStudyFeaturesMostImportantReduced, gemma3-27b
Run with minimal schema v1 "EcosystemStudyFeaturesMostImportantReduced" 
(https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/src/kibad_llm/schema/types.py#L1126C7-L1126C49)
and lengthier prompt instructions: https://github.com/DFKI-NLP/kibad-llm/blob/dacf42551b3eca182c7dd8b34cfd6af8fea252fe/configs/experiment/predict/faktencheck_most_important_schema.yaml
