## User

Please have a look at "shared_task/Advanced NLP shared tasks task descriptions.docx", "Task C: Information extraction for biodiversity assessment". I need standalone eval scripts for all subtasks (can also be a single script, if this is less complex). See the document for how it needs to be used. The logic should follow the eval logic used/implemented in the kibad-llm project. I added examples downloaded from the dfki cloud mentioned in the document data into the example-data folder (`train` contains input pdfs from the "https://cloud.dfki.de/owncloud/index.php/s/cHAQ6Z3acdtSwie", `train.jsonl` the unmodified file downloaded from https://cloud.dfki.de/owncloud/index.php/s/9bj5wyrXsHSc9YA (you do not need to download them again). Put the script(s) into the "shared_task/evaluation" folder. Also add a README.md explaining relevant details of the evaluation, usage etc. but keep it concise.

Anything else we need to clarify before implementing this?

## Assistant

Yes—two points need clarifying after reviewing Task C, the 908 training records, and the project’s metrics:

1. **BERTScore settings:** The document requires “best-match BERTScore,” but doesn’t specify the model, matching formula, averaging, or treatment of missing predictions. The project currently implements exact-match F1, with no BERTScore implementation. Do you have required settings, or should I choose and document a reproducible definition?

2. **CodaBench integration:** Should this include a CodaBench scoring entry point, or just a standalone command accepting reference and prediction JSONL files? I suggest supporting both through one shared implementation.

For everything else, I’d use these defaults:

- Cover C1 and all three C2 groups with one script, independent of the installed `kibad_llm` package.
- Follow the project’s categorical evaluation: flatten nested subfields, deduplicate values per paper, ignore empty values, compare strings exactly, and pool TP/FP/FN across papers.
- Compute C1 from exactly the five fields listed in the document. The project’s existing core configuration additionally includes German and scientific taxa names; those belong to C2b here and would retain exact matching.
- Require one prediction record per reference ID, rejecting duplicate, missing, or unknown IDs; omitted fields count as empty.
- Report per-field scores, group macro F1, and overall micro F1, keeping BERTScore separate.
- Keep categorical scoring dependency-free, with additional dependencies for BERTScore.

No need to download the PDFs or references again. I haven’t changed any files yet.

## User

feedback:
 - "1. BERTScore settings": yes, please choose and document a reproducible definition
 - "2. CodaBench integration:": yes, supporting both through one shared implementation, sounds good

One more detail: Please create two documentation documents, one for me (the maintainer), where you exactly describe how you derived teh screipt from the existing kibad-llm code. And then the README.md which should be independent of kibad-llm code. Especially, it should not leak what's not already in the script (the participants should not be lead to the kibad-llm repo).

Anything else? If not, please implement this.