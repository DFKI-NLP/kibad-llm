"""Hydra callback that persists job return values to disk after each run.

[`SaveJobReturnValueCallback`][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback] is registered in ``configs/predict.yaml`` and
``configs/evaluate.yaml`` via the ``hydra.callbacks`` config key.  After each job it
saves the function's return dict to one or more files (JSON or Markdown).

For Hydra multirun sweeps the callback also:

- Collects all per-job return dicts and aggregates them into a combined output file.
- Optionally integrates them into a ``dict-of-lists`` structure for easy cross-job
  analysis (`integrate_multirun_result`).
- Computes numeric aggregation statistics (mean, std, etc.) and saves them in a
  separate ``.aggregated.json`` / ``.aggregated.md`` file.
- Creates human-readable job identifiers from differing Hydra overrides.
- Optionally groups Markdown output by a column (``multirun_markdown_group_by``).
"""

from collections.abc import Hashable, Iterable
import json
import logging
import os
from pathlib import Path
from typing import Any

from hydra.core.utils import JobReturn
from hydra.experimental.callback import Callback
import numpy as np
from omegaconf import DictConfig
import pandas as pd

from kibad_llm.utils.dictionary import flatten_dict, unflatten_dict
from kibad_llm.utils.job_return import (
    dict_to_overrides,
    mixed_group_by,
    multi_index_to_single,
    overrides_to_dict,
)


def to_py_obj(obj: Any) -> Any:
    """Convert a PyTorch tensor, Numpy array or python list to a python list.

    Modified version of transformers.utils.generic.to_py_obj.
    """
    if isinstance(obj, dict):
        return {k: to_py_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(to_py_obj(o) for o in obj)
    elif isinstance(obj, (np.ndarray, np.number)):  # tolist also works on 0d np arrays
        return obj.tolist()
    else:
        return obj


def list_of_dicts_to_dict_of_lists_recursive(list_of_dicts):
    """Convert a list of dicts to a dict of lists recursively.

    Examples:
        # works with nested dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}])
        {'a': [1, 3], 'b': {'c': [2, 4]}}
        # works with incomplete dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": 2}, {"a": 3}])
        {'a': [1, 3], 'b': [2, None]}

        # works with nested incomplete dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": 3}])
        {'a': [1, 3], 'b': {'c': [2, None]}}

        # works with nested incomplete dicts with None values
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": None}])
        {'a': [1, None], 'b': {'c': [2, None]}}

    Args:
        list_of_dicts (list[dict]): A list of dicts.

    Returns:
        dict: An arbitrarily nested dict of lists.
    """
    if not list_of_dicts:
        return {}

    # Check if all elements are either None or dictionaries
    if all(d is None or isinstance(d, dict) for d in list_of_dicts):
        # Gather all keys from non-None dictionaries
        keys = set()
        for d in list_of_dicts:
            if d is not None:
                keys.update(d.keys())

        # Build up the result recursively
        return {
            k: list_of_dicts_to_dict_of_lists_recursive(
                [(d[k] if d is not None and k in d else None) for d in list_of_dicts]
            )
            for k in keys
        }
    else:
        # If items are not all dict/None, just return the list as is (base case).
        return list_of_dicts


def remove_common_overrides(
    overrides_per_result: Iterable[Iterable[str]],
) -> list[list[str]]:
    """Removes the common overrides from a list of lists of overrides.

    Example:
        >>> overrides_per_result = [
        ...     ["a=1", "b=2", "c=3"],
        ...     ["a=1", "b=2", "c=4"],
        ...     ["a=1", "b=3", "c=3"],
        ]
        >>> remove_common_overrides(overrides_per_result)
        [['b=2', 'c=3'], ['b=2', 'c=4'], ['b=3', 'c=3']]
    Args:
        overrides_per_result (list[list[str]]): A list of lists of overrides.
    Returns:
        list[list[str]]: A list of lists of overrides with common overrides removed.
    """
    as_dicts = [overrides_to_dict(overrides) for overrides in overrides_per_result]
    as_df = pd.DataFrame(as_dicts)
    if len(as_df) > 1:
        differing_data = as_df.loc[:, as_df.nunique(dropna=False) > 1]
    else:
        differing_data = as_df
    differing_as_dicts = [row.to_dict() for _, row in differing_data.iterrows()]
    differing_overrides = [dict_to_overrides(d, remove_na=True) for d in differing_as_dicts]
    return differing_overrides


def overrides_to_identifiers(
    overrides_per_result: Iterable[Iterable[str]], sep: str = "-", remove_common: bool = True
) -> list[str] | None:
    """Converts a list of lists of overrides to a list of identifiers.

    Example:
        >>> overrides_per_result = [
        ...     ["a=1", "b=2", "c=3"],
        ...     ["a=1", "b=2", "c=4"],
        ...     ["a=1", "b=3", "c=3"],
        ]
        >>> overrides_to_identifiers(overrides_per_result)
        ['b=2-c=3', 'b=2-c=4', 'b=3-c=3']

    Args:
        overrides_per_result (list[list[str]]): A list of lists of overrides.
        sep (str, optional): The separator to use between the overrides. Defaults to "-".
        remove_common (bool, optional): If True, remove common overrides. Defaults to True.

    Returns:
        list[str] | None: A list of identifiers or None if the identifiers are not unique.
    """

    if remove_common:
        overrides_per_result = remove_common_overrides(overrides_per_result)
    identifiers = [sep.join(overrides) for overrides in overrides_per_result]
    # if not unique identifiers, return None
    if len(set(identifiers)) < len(identifiers):
        return None

    return identifiers


def identifier_to_dict(identifier: str, sep: str = "-") -> dict[str, str]:
    """Convert an identifier string back to a dictionary of overrides.

    Example:
        >>> identifier = "b=2-c=3"
        >>> identifier_to_dict(identifier)
        {'b': '2', 'c': '3'}

    Args:
        identifier (str): The identifier string.
        sep (str, optional): The separator used between the overrides. Defaults to "-".

    Returns:
        dict[str, str]: The dictionary of overrides.
    """
    overrides = identifier.split(sep)
    as_dict = overrides_to_dict(overrides)
    return as_dict


def handle_previous_overrides(
    job_return: JobReturn, key: str, replace_existing: bool = False
) -> None:
    """Handle previous result overrides in the job return object. If the job return value contains a
    <key>> field with an "overrides" field, the overrides are either used to replace the existing
    overrides in the job return object (if replace_existing is True) or simply converted to a dictionary.

    Args:
        job_return (JobReturn): The job return object.
        key (str): The key to look for in the job return value (e.g. "prediction").
        replace_existing (bool, optional): If True, replace existing overrides by the prediction overrides.
            Defaults to False.
    """
    if (
        isinstance(job_return.return_value, dict)
        and key in job_return.return_value
        and isinstance(job_return.return_value[key], dict)
        and "overrides" in job_return.return_value[key]
    ):
        prediction_overrides = job_return.return_value[key].pop("overrides")
        if prediction_overrides:
            if replace_existing:
                job_return.overrides = list(prediction_overrides)
            else:
                job_return.return_value[key]["overrides"] = overrides_to_dict(
                    prediction_overrides, remove_plus_prefix=True
                )


class SaveJobReturnValueCallback(Callback):
    """Save the job return-value in ${output_dir}/{job_return_value_filename}.

    This also works for multi-runs (e.g. sweeps for hyperparameter search). In this case, the result will be saved
    additionally in a common file in the multi-run log directory. If integrate_multirun_result=True, the
    job return-values are also aggregated (e.g. mean, min, max) and saved in another file.

    params:
    -------
    filenames: str or list[str] (default: "job_return_value.json")
        The filename(s) of the file(s) to save the job return-value to. If it ends with ".json",
        the return-value will be saved as a json file. If it ends with ".md", the return-value will be
        saved as a markdown file.
    integrate_multirun_result: bool (default: True)
        If True, the job return-values of all jobs from a multi-run will be rearranged into a dict of lists (maybe
        nested), where the keys are the keys of the job return-values and the values are lists of the corresponding
        values of all jobs. This is useful if you want to access specific values of all jobs in a multi-run all at once.
        Also, aggregated values (e.g. mean, min, max) are created for all numeric values and saved in another file.
    multirun_aggregator_blacklist: list[str] (default: None)
        A list of keys to exclude from the aggregation (of multirun results), such as "count" or "25%". If None,
        all keys are included. See pd.DataFrame.describe() for possible aggregation keys.
        For numeric values, it is recommended to use ["min", "25%", "50%", "75%", "max"]
        which will result in keeping only the count, mean and std values.
    sort_markdown_columns: bool (default: False)
        If True, the columns of the markdown table are sorted alphabetically.
    markdown_round_digits: int (default: 3)
        The number of digits to round the values in the markdown file. If None, no rounding is applied.
    multirun_create_ids_from_overrides: bool (default: False)
        Create job identifiers from the overrides of the jobs in a multi-run. If False, the job index is used as
        identifier.
    handle_previous_result: str (default: None)
        If provided, assume that the job return-value contains a field with the given name (e.g. "prediction") that itself
        contains an "overrides" field, the overrides from this field are either used to replace the existing overrides
        in the job return object (if replace_existing_overrides is True) or simply converted to a dictionary and added
        back to the job return-value (if replace_existing_overrides is False). Furthermore, the field is removed from
        the job return-value before saving it as markdown to avoid destroying the table structure.
    replace_existing_overrides: bool (default: False)
        If True, replace existing overrides in the job return-value with the overrides from the job return
        object if available. If False, the overrides are just converted to a dictionary, if available.
    add_overrides_as_dict: bool (default: False)
        If True, add the overrides as a dictionary to each job return-value under the key "overrides".
    multirun_job_id_key: str (default: "job_id")
        The key to use for the job identifiers in the integrated multi-run result.
    multirun_convert_job_ids: bool (default: False)
        If True, convert job ids to dictionaries. Works only if integrate_multirun_result is True.
    multirun_show_file_contents: list[str] (default: None)
        A list of filenames (from the filenames parameter or aggregated files) to log the contents
        to the console after saving the multi-run results.
    multirun_overrides_separator: str (default: "-")
        The separator to use when creating job identifiers from overrides.
    multirun_markdown_group_by: str or list[str] (default: None)
        The column(s) to group by when saving the multi-run result as markdown file. For numeric columns,
        the mean and std are calculated. For non-numeric columns, a list of values is created. If None,
        no grouping is applied.
    multirun_markdown_transpose: bool (default: False)
        If True, transpose the markdown table for multi-run results.
    paths_file: str (default: None)
        The file to save the paths of the log directories to. If None, the paths are not saved.
    path_id: str (default: None)
        A prefix to add to each line in the paths_file separated by a colon. If None, no prefix is added.
    multirun_paths_file: str (default: None)
        The file to save the paths of the multi-run log directories to. If None, the paths are not saved.
    multirun_path_id: str (default: None)
        A prefix to add to each line in the multirun_paths_file separated by a colon. If None, no prefix is added.
    """

    def __init__(
        self,
        filenames: str | list[str] = "job_return_value.json",
        integrate_multirun_result: bool = False,
        multirun_aggregator_blacklist: list[str] | None = None,
        sort_markdown_columns: bool = True,
        markdown_round_digits: int | None = 3,
        multirun_create_ids_from_overrides: bool = True,
        multirun_job_id_key: str = "job_id",
        multirun_convert_job_ids: bool = False,
        handle_previous_result: str | None = None,
        replace_existing_overrides: bool = False,
        multirun_add_overrides_as_dict: bool = False,
        multirun_show_file_contents: list[str] | None = None,
        multirun_overrides_separator: str = "-",
        multirun_markdown_group_by: str | list[str] | None = None,
        multirun_markdown_transpose: bool = False,
        paths_file: str | None = None,
        path_id: str | None = None,
        multirun_paths_file: str | None = None,
        multirun_path_id: str | None = None,
    ) -> None:
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.filenames = [filenames] if isinstance(filenames, str) else filenames
        self.multirun_show_file_contents = multirun_show_file_contents or []
        self.integrate_multirun_result = integrate_multirun_result
        self.job_returns: list[JobReturn] = []
        self.multirun_aggregator_blacklist = multirun_aggregator_blacklist
        self.sort_markdown_columns = sort_markdown_columns
        self.multirun_create_ids_from_overrides = multirun_create_ids_from_overrides
        self.handle_previous_result = handle_previous_result
        self.replace_existing_overrides = replace_existing_overrides
        self.multirun_add_overrides_as_dict = multirun_add_overrides_as_dict
        self.multirun_job_id_key = multirun_job_id_key
        self.multirun_convert_job_ids = multirun_convert_job_ids
        self.multirun_overrides_separator = multirun_overrides_separator
        if isinstance(multirun_markdown_group_by, str):
            multirun_markdown_group_by = [multirun_markdown_group_by]
        self.multirun_markdown_group_by = multirun_markdown_group_by
        self.multirun_markdown_transpose = multirun_markdown_transpose
        self.markdown_round_digits = markdown_round_digits
        self.multirun_paths_file = multirun_paths_file
        self.multirun_path_id = multirun_path_id
        self.paths_file = paths_file
        self.path_id = path_id

    def on_job_end(self, config: DictConfig, job_return: JobReturn, **kwargs: Any) -> None:
        if self.handle_previous_result is not None:
            handle_previous_overrides(
                job_return,
                key=self.handle_previous_result,
                replace_existing=self.replace_existing_overrides,
            )
        self.job_returns.append(job_return)
        output_dir = Path(config.hydra.runtime.output_dir)  # / Path(config.hydra.output_subdir)
        if self.paths_file is not None:
            # append the output_dir to the file
            with open(self.paths_file, "a") as file:
                file.write(f"{output_dir}\n")

        for filename in self.filenames:
            # Remove previous result field and "overrides" from job return-value before saving as markdown.
            # Otherwise, this may destroy the table structure of the saved job return-value.
            obj = job_return.return_value
            if filename.lower().endswith(".md") and isinstance(obj, dict):
                if self.handle_previous_result is not None and self.handle_previous_result in obj:
                    if self.handle_previous_result in obj:
                        obj = dict(obj)
                        obj.pop(self.handle_previous_result)
            self._save(obj=obj, filename=filename, output_dir=output_dir)

    def on_multirun_end(self, config: DictConfig, **kwargs: Any) -> None:
        job_ids: list[str] | list[int] | None = None
        if self.multirun_create_ids_from_overrides:
            overrides_per_result = [jr.overrides or [] for jr in self.job_returns]
            job_ids = overrides_to_identifiers(
                overrides_per_result, sep=self.multirun_overrides_separator, remove_common=True
            )
            if job_ids is None:
                self.log.warning(
                    "Job identifiers created from overrides are not unique! "
                    "Use the job indexes instead."
                )

        if job_ids is None:
            job_ids = list[int](range(len(self.job_returns)))

        if self.multirun_add_overrides_as_dict:
            for jr in self.job_returns:
                jr.return_value["overrides"] = overrides_to_dict(
                    jr.overrides or [], remove_plus_prefix=True
                )

        if self.integrate_multirun_result:
            # rearrange the job return-values of all jobs from a multi-run into a dict of lists (maybe nested),
            obj = list_of_dicts_to_dict_of_lists_recursive(
                [jr.return_value for jr in self.job_returns]
            )
            if not isinstance(obj, dict):
                obj = {"value": obj}
            if self.multirun_create_ids_from_overrides:
                obj[self.multirun_job_id_key] = job_ids

            # also create an aggregated result
            # convert to python object to allow selecting numeric columns
            obj_py = to_py_obj(obj)
            obj_flat = flatten_dict(obj_py)
            # create dataframe from flattened dict
            df_flat = pd.DataFrame(obj_flat)
            # select only the numeric values
            df_numbers_only = df_flat.select_dtypes(["number"])
            cols_removed: set[tuple[str | int, ...]] = (
                set(df_flat.columns) - set(df_numbers_only.columns) - {(self.multirun_job_id_key,)}  # type: ignore
            )
            if len(cols_removed) > 0:
                self.log.warning(
                    f"Removed the following columns from the aggregated result because they are not numeric: "
                    f"{cols_removed}"
                )
            if len(df_numbers_only.columns) == 0:
                obj_aggregated = None
            else:
                # aggregate the numeric values
                df_described = df_numbers_only.describe()
                # remove rows in the blacklist
                if self.multirun_aggregator_blacklist is not None:
                    df_described = df_described.drop(
                        self.multirun_aggregator_blacklist, errors="ignore", axis="index"
                    )
                # add the aggregation keys (e.g. mean, min, ...) as most inner keys and convert back to dict
                # TODO: check if "type ignore" is really fine and necessary here
                obj_flat_aggregated: dict[tuple[str | int | float, ...], Any] = df_described.T.stack().to_dict()  # type: ignore
                # unflatten because _save() works better with nested dicts. But don't remove key padding
                # since this is required for proper unstacking in _save() for markdown files.
                obj_aggregated = unflatten_dict(obj_flat_aggregated, unpad_keys=False)

            if self.multirun_convert_job_ids:
                # convert job ids (created from overrides) to dicts
                obj[self.multirun_job_id_key] = list_of_dicts_to_dict_of_lists_recursive(
                    [
                        identifier_to_dict(identifier, sep=self.multirun_overrides_separator)
                        for identifier in obj[self.multirun_job_id_key]
                    ]
                )
        else:
            # create a dict of the job return-values of all jobs from a multi-run
            # (_save() works better with nested dicts)
            obj = {
                identifier: jr.return_value for identifier, jr in zip(job_ids, self.job_returns)
            }
            obj_aggregated = None
        output_dir = Path(config.hydra.sweep.dir)
        if self.multirun_paths_file is not None:
            # append the output_dir to the file
            line = f"{output_dir}\n"
            if self.multirun_path_id is not None:
                line = f"{self.multirun_path_id}:{line}"
            with open(self.multirun_paths_file, "a") as file:
                file.write(line)

        filenames_aggregated = []
        for filename in self.filenames:
            self._save(
                obj=obj,
                filename=filename,
                output_dir=output_dir,
                is_tabular_data=self.integrate_multirun_result,
                markdown_group_by=self.multirun_markdown_group_by,
            )
            # if available, also save the aggregated result
            if obj_aggregated is not None:
                file_base_name, ext = os.path.splitext(filename)
                filename_aggregated = f"{file_base_name}.aggregated{ext}"
                filenames_aggregated.append(filename_aggregated)
                self._save(
                    obj=obj_aggregated,
                    filename=filename_aggregated,
                    output_dir=output_dir,
                    # If we have aggregated (integrated multi-run) results, we unstack the last level,
                    # i.e. the aggregation key.
                    unstack_last_index_level=True,
                )
        saved_files = set(self.filenames + filenames_aggregated)
        for fn in self.multirun_show_file_contents:
            if fn in saved_files:
                with open(str(output_dir / fn)) as file:
                    contents = file.read()
                self.log.info(f"Contents of {output_dir / fn}:\n{contents}")

    def _save(
        self,
        obj: Any,
        filename: str,
        output_dir: Path,
        is_tabular_data: bool = False,
        unstack_last_index_level: bool = False,
        markdown_group_by: list[str] | None = None,
    ) -> None:
        self.log.info(f"Saving job_return in {output_dir / filename}")
        output_dir.mkdir(parents=True, exist_ok=True)
        assert output_dir is not None
        if filename.endswith(".json"):
            # Convert PyTorch tensors and numpy arrays to native python types
            obj_py = to_py_obj(obj)
            if isinstance(obj_py, dict):
                # remove padding from keys for json output
                obj_py = unflatten_dict(flatten_dict(obj_py), unpad_keys=True)
            with open(str(output_dir / filename), "w") as file:
                json.dump(obj_py, file, indent=2, ensure_ascii=False)
        elif filename.endswith(".md"):
            # Convert PyTorch tensors and numpy arrays to native python types
            obj_py = to_py_obj(obj)
            if not isinstance(obj_py, dict):
                obj_py = {"value": obj_py}

            if not all(isinstance(k, (str, int)) for k in obj_py):
                raise ValueError(
                    f"Can not flatten the dictionary, unexpected key types in obj_py: {obj_py.keys()}"
                )
            obj_py_flat = flatten_dict(obj_py)

            job_id_columns: list[Hashable | None] = []
            if is_tabular_data:
                # In the case of (not aggregated) integrated multi-run result, we expect to have
                # multiple values for each key. We therefore just convert the dict to a pandas DataFrame.
                result = pd.DataFrame(obj_py_flat)
                # get job id columns
                job_id_columns = [
                    col for col in result.columns if col[0] == self.multirun_job_id_key
                ]
            else:
                # Otherwise, we have only one value for each key. We convert the dict to a pandas Series.
                series = pd.Series(obj_py_flat)
                # The series has a MultiIndex because flatten_dict() uses a tuple as key.
                if series.index.nlevels <= 1:
                    # If there is only one level, we just use the first level values as index.
                    series.index = series.index.get_level_values(0)
                    result = pd.DataFrame([series])
                else:
                    # If there are multiple levels, we unstack the series to get a DataFrame
                    # providing a better overview.
                    if unstack_last_index_level:
                        # If we have aggregated (integrated multi-run) results, we unstack the last level,
                        # i.e. the aggregation key.
                        result = series.unstack(-1)
                    else:
                        # Otherwise we have a default multi-run result and unstack the first level,
                        # i.e. the identifier created from the overrides, and transpose the result
                        # to have the individual jobs as rows.
                        result = series.unstack(0).T

            if isinstance(result, pd.DataFrame):
                if self.sort_markdown_columns:
                    result = result.sort_index(axis=1)
                # move job id columns to the front
                job_id_columns_sorted = [col for col in result.columns if col in job_id_columns]
                other_columns = [col for col in result.columns if col not in job_id_columns]
                result = result[job_id_columns_sorted + other_columns]

            # flatten the index values and column names
            if isinstance(result.index, pd.MultiIndex):
                result.index = multi_index_to_single(result.index)
            if isinstance(result, pd.DataFrame) and isinstance(result.columns, pd.MultiIndex):
                result.columns = multi_index_to_single(result.columns)

            if markdown_group_by is not None:
                result = mixed_group_by(
                    data=result,
                    by=markdown_group_by,
                    numeric_agg_func=["mean", "std"],
                    numeric_fill_na=0.0,
                    force_list_col_regex=r"^overrides\.",
                )
                job_id_columns = list(result.index.names)
                result = result.reset_index()

            if self.markdown_round_digits is not None and (
                isinstance(result, pd.DataFrame) or result.dtype != "object"
            ):
                result = result.round(self.markdown_round_digits)

            if self.multirun_markdown_transpose:
                result = result.T

            with open(str(output_dir / filename), "w") as file:
                file.write(result.to_markdown(index=len(job_id_columns) == 0))

        else:
            raise ValueError("Unknown file extension")
