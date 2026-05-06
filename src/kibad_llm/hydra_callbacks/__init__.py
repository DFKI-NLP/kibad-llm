"""Custom Hydra callbacks used in predict and evaluate pipelines.

Re-exports [`SaveJobReturnValueCallback`][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback],
which saves job return values (and aggregated multirun summaries) to JSON or Markdown
files after each Hydra job.
"""

from .save_job_return_value import SaveJobReturnValueCallback
