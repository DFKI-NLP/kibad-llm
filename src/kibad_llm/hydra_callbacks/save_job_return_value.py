"""Save Hydra jobs' and multiruns' outputs to disk.

Classes:
    SaveJobReturnValueCallback: Handles the saving of job return-values at the ends of jobs and multiruns.

Functions:
    to_py_obj: Recursively converts numpy arrays to python lists.
    list_of_dicts_to_dict_of_lists_recursive: Recursively converts a list of dicts to a dict of lists.
    remove_common_overrides: Removes the common overrides from a list of lists of overrides.
    overrides_to_identifiers: Converts a list of lists of overrides to a list of identifiers.
    identifier_to_dict: Converts an identifier string back to a dictionary of overrides.
    handle_previous_overrides: Handles previous result overrides in the job return object.

"""

from collections.abc import Hashable, Iterable
import json
import logging
import os
from pathlib import Path
from typing import Any, cast

from hydra.core.utils import JobReturn
from hydra.experimental.callback import Callback
import numpy as np
from omegaconf import DictConfig
import pandas as pd

from kibad_llm.config import RESULT_FORMAT_VERSION_KEY
from kibad_llm.utils.dictionary import flatten_dict, unflatten_dict
from kibad_llm.utils.job_return import (
    dict_to_overrides,
    mixed_group_by,
    multi_index_to_single,
    overrides_to_dict,
)


def to_py_obj(obj: Any) -> Any:
    """Recursively convert numpy arrays to python lists.

    Recurses dictionaries (value only), lists, tuples.

    Modified version of transformers.utils.generic.to_py_obj.

    Args:
        obj: A py_obj possibly holding a numpy array.

    Returns:
        The obj, but with numpy arrays converted to python lists and numpy scalars to python scalars.
    """
    if isinstance(obj, dict):
        return {k: to_py_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return type(obj)(to_py_obj(o) for o in obj)
    elif isinstance(obj, (np.ndarray, np.number)):  # tolist also works on 0d np arrays
        return cast(list, obj.tolist())
    else:
        return obj


def list_of_dicts_to_dict_of_lists_recursive(
    list_of_dicts: list[Any],
) -> dict[Any, Any] | list[Any]:
    """Convert a list of dicts to a dict of lists recursively.

    Args:
        list_of_dicts: A list of dicts (optionally nested).

    Returns:
        An arbitrarily nested dict of lists.

    Examples:
        works with nested dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}])
        {'a': [1, 3], 'b': {'c': [2, 4]}}

        works with incomplete dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": 2}, {"a": 3}])
        {'a': [1, 3], 'b': [2, None]}

        works with nested incomplete dicts
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": 3}])
        {'a': [1, 3], 'b': {'c': [2, None]}}

        works with nested incomplete dicts with None values
        >>> list_of_dicts_to_dict_of_lists_recursive([{"a": 1, "b": {"c": 2}}, {"a": None}])
        {'a': [1, None], 'b': {'c': [2, None]}}

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
                [(d[k] if d is not None and k in d else None) for d in list_of_dicts],
            )
            for k in keys
        }
    else:
        # If items are not all dict/None, just return the list as is (base case).
        return list_of_dicts


def remove_common_overrides(
    overrides_per_result: Iterable[Iterable[str]],
) -> list[list[str]]:
    """Remove the common overrides from a list of lists of overrides.

    Args:
        overrides_per_result: A list of lists of overrides.

    Returns:
        A list of lists of overrides with common overrides removed.

    Examples:
        >>> overrides_per_result = [
        ...     ["a=1", "b=2", "c=3"],
        ...     ["a=1", "b=2", "c=4"],
        ...     ["a=1", "b=3", "c=3"],
        ... ]
        >>> remove_common_overrides(overrides_per_result)
        [['b=2', 'c=3'], ['b=2', 'c=4'], ['b=3', 'c=3']]
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
    """Convert a list of lists of overrides to a list of identifiers.

    Args:
        overrides_per_result: A list of lists of overrides.
        sep: The separator to use between the overrides.
        remove_common: If True, remove common overrides.

    Returns:
        A list of identifiers or None if the identifiers are not unique.

    Examples:
        >>> overrides_per_result = [
        ...     ["a=1", "b=2", "c=3"],
        ...     ["a=1", "b=2", "c=4"],
        ...     ["a=1", "b=3", "c=3"],
        ... ]
        >>> overrides_to_identifiers(overrides_per_result)
        ['b=2-c=3', 'b=2-c=4', 'b=3-c=3']
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

    Args:
        identifier: The identifier string.
        sep: The separator used between the overrides.

    Returns:
        The dictionary of overrides.

    Examples:
        >>> identifier = "b=2-c=3"
        >>> identifier_to_dict(identifier)
        {'b': '2', 'c': '3'}
    """
    overrides = identifier.split(sep)
    as_dict = overrides_to_dict(overrides)
    return as_dict


def handle_previous_overrides(
    job_return: JobReturn, key: str, replace_existing: bool = False
) -> None:
    """Handle previous result overrides in the job return object.

    If the job return value contains a
    `<key>` field with an `"overrides"` field, the overrides are either used to replace the existing
    overrides in the job return object (if replace_existing is True) or simply converted to a dictionary.

    The `"overrides"` field is popped from the job return-value in either case. It is only added back, converted to
    a dictionary, when replace_existing is False and the field was non-empty. `job_return` is modified in place.

    Args:
        job_return: The job return object.
        key: The key to look for in the job return value (e.g. "prediction").
        replace_existing: If True, replace existing overrides by the previous result's overrides.
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
    """Save each job's return-value in `${output_dir}/${filename}`, for every entry in `filenames`.

    This also works for multi-runs (e.g. sweeps for hyperparameter search). In this case, the result will be saved
    additionally in a common file in the multi-run log directory. If integrate_multirun_result=True, the
    job return-values are also aggregated (e.g. mean, min, max) and saved in another file.

    This class exists to postprocess job and multirun outputs, by overwriting [Hydra's no-op callback hooks](https://hydra.cc/docs/experimental/callbacks/).

    Outputs can be saved as json and markdown. The markdown output is just a table with no text around it.

    Attributes:
        filenames (list[str]): The filename(s) of the file(s) to save the job return-value to. The type is always a list of strings.
            If an entry ends with ".json", the return-value is saved as a json file. If it ends
            with ".md", the return-value is saved as a markdown file. Json files are more complete data wise, whilst
            markdown files have more settings that can be applied for readability.
        _log (logging.Logger): The logger of this callback.
        _job_returns (list[JobReturn]): The return objects of all jobs seen by on_job_end so far. Consumed by
            on_multirun_end.

    **Used by `on_job_end`:**

    Attributes:
        handle_previous_result (str | None): If provided, assume the job return-value contains a field with the given
            name (e.g. "prediction") that itself contains an "overrides" field. The overrides from this field are
            either used to replace the existing overrides in the job return object (if replace_existing_overrides is
            True) or simply converted to a dictionary and added back to the job return-value (if
            replace_existing_overrides is False). Furthermore, on the legacy markdown path (see markdown_data_key),
            the field is removed from the job return-value before saving it as markdown to avoid destroying the
            table structure.
        replace_existing_overrides (bool): If True, replace existing overrides in the job return-value with the
            overrides from the job return object if available. If False, the overrides are just converted to a
            dictionary, if available.
        paths_file (str | None): The file to append the paths of the log directories to. If None, the paths are not
            saved.
        markdown_data_key (str | None): If provided and present in the job return-value, save only the value at this
            key when saving single job results to markdown. This is useful to strip metadata from the job result and,
            thus, allow for correct table formatting of metric results, for instance. If the key is absent (or None),
            a legacy path is used instead, which drops the handle_previous_result field and the result format version
            key from the markdown output.

    **Used by `on_multirun_end`:**

    Attributes:
        integrate_multirun_result (bool): If True, the job return-values of all jobs from a multi-run are rearranged
            into a dict of lists (maybe nested), where the keys are the keys of the job return-values and the values
            are lists of the corresponding values of all jobs. This is useful if you want to access specific values
            of all jobs in a multi-run all at once. Also, aggregated values (e.g. mean, min, max) are created for all
            numeric values and saved in another file.
        multirun_aggregator_blacklist (list[str] | None): A list of keys to exclude from the aggregation (of multirun
            results), such as "count" or "25%". If None, all keys are included. See `pd.DataFrame.describe()` for
            possible aggregation keys. For numeric values, it is recommended to use `["min", "25%", "50%", "75%",
            "max"]` which will result in keeping only the count, mean and std values.
        multirun_create_ids_from_overrides (bool): If True, create job identifiers from the overrides of the jobs in a
            multi-run. If False, the job index is used as identifier.
        multirun_job_id_key (str): The key to use for the job identifiers in the integrated multi-run result.
        multirun_convert_job_ids (bool): If True, convert job ids to dictionaries. Works only if
            integrate_multirun_result is True.
        multirun_add_overrides_as_dict (bool): If True, add the overrides as a dictionary to each job return-value
            under the key "overrides".
        multirun_show_file_contents (list[str]): A list of filenames (from the filenames attribute or
            aggregated files) whose contents are logged to the console after saving the multi-run results.
        multirun_overrides_separator (str): The separator to use when creating job identifiers from overrides.
        multirun_markdown_group_by (list[str] | None): The column(s) to group by when saving the multi-run result as
            a markdown file. For numeric columns, the mean and std are calculated. For non-numeric columns, a list of
            values is created. If None, no grouping is applied. A single string is wrapped into a list.
        multirun_paths_file (str | None): The file to save the paths of the multi-run log directories to. If None,
            the paths are not saved.
        multirun_path_id (str | None): A prefix to add to each line in the multirun_paths_file, separated by a colon.
            If None, no prefix is added.

    **Used by `_save`:**

    Attributes:
        sort_markdown_columns (bool): If True, the columns of the markdown table are sorted alphabetically.
        markdown_round_digits (int | None): The number of digits to round the values in the markdown file to. If None,
            no rounding is applied.
        multirun_markdown_transpose (bool): If True, transpose the markdown table for multi-run results.

    **Not used:**

    Attributes:
        path_id (str | None): This is currently not in use. A prefix to add to each line in the paths_file,
            separated by a colon. If None, no prefix is added.

    Methods:
        on_job_end: Save a single job's return-value once the job finishes.
        on_multirun_end: Collate and save all jobs' return-values once the multi-run finishes.
    """

    def __init__(
        self,
        filenames: str | list[str] = "job_return_value.json",
        integrate_multirun_result: bool = False,
        multirun_aggregator_blacklist: list[str] | None = None,
        sort_markdown_columns: bool = True,
        markdown_round_digits: int | None = 3,
        markdown_data_key: str | None = None,
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
        """Assign args to attributes and do some safety conversions beforehand.
        For more info on the args, check their respective attributes in the class docstring.

        Args:
            filenames: If a string is passed, it will be wrapped in a list.
            integrate_multirun_result:
            multirun_aggregator_blacklist:
            sort_markdown_columns:
            markdown_round_digits:
            markdown_data_key:
            multirun_create_ids_from_overrides:
            multirun_job_id_key:
            multirun_convert_job_ids:
            handle_previous_result:
            replace_existing_overrides:
            multirun_add_overrides_as_dict:
            multirun_show_file_contents: If None is passed, saves [] instead.
            multirun_overrides_separator:
            multirun_markdown_group_by: If a string is passed, it will be wrapped in a list.
            multirun_markdown_transpose:
            paths_file:
            path_id:
            multirun_paths_file:
            multirun_path_id:
        """
        self._log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.filenames = [filenames] if isinstance(filenames, str) else filenames
        self.multirun_show_file_contents = multirun_show_file_contents or []
        self.integrate_multirun_result = integrate_multirun_result
        self._job_returns: list[JobReturn] = []
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
        self.markdown_data_key = markdown_data_key
        self.multirun_paths_file = multirun_paths_file
        self.multirun_path_id = multirun_path_id
        self.paths_file = paths_file
        self.path_id = path_id

    def on_job_end(self, config: DictConfig, job_return: JobReturn, **kwargs: Any) -> None:
        """Save a single job's return-value to each of the configured filenames via the internal `_save` method.

        Also appends the job to `job_returns` for later use by
        [`on_multirun_end`][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback.on_multirun_end],
        and appends the job's output directory to `paths_file` if one is configured. For markdown output, metadata
        fields are stripped from the return-value first (see `markdown_data_key` and `handle_previous_result`) to
        keep the table structure intact.

        Args:
            config: Hydra config of the given job. Only `hydra.runtime.output_dir` is read.
            job_return: The Hydra job's output object, e.g. the output of [`predict()`][kibad_llm.predict.predict].

        Keyword Args:
            **kwargs: Ignored; accepted for Hydra callback interface compatibility.
        """
        if self.handle_previous_result is not None:
            handle_previous_overrides(
                job_return,
                key=self.handle_previous_result,
                replace_existing=self.replace_existing_overrides,
            )
        self._job_returns.append(job_return)
        output_dir = Path(config.hydra.runtime.output_dir)
        if self.paths_file is not None:
            # append the output_dir to the file
            with open(self.paths_file, "a") as file:
                file.write(f"{output_dir}\n")

        for filename in self.filenames:
            # Remove previous result field and "version" (RESULT_FORMAT_VERSION_KEY) from job return-value before
            # saving as markdown. Otherwise, this may destroy the table structure of the saved job return-value.
            obj = job_return.return_value
            if filename.lower().endswith(".md") and isinstance(obj, dict):
                obj = dict(obj)
                if self.markdown_data_key in obj:
                    obj = obj[self.markdown_data_key]
                else:  # legacy code path for compatibility
                    if (
                        self.handle_previous_result is not None
                        and self.handle_previous_result in obj
                    ):
                        obj.pop(self.handle_previous_result)
                    if RESULT_FORMAT_VERSION_KEY in obj:
                        obj.pop(RESULT_FORMAT_VERSION_KEY)
                    if self.markdown_data_key in obj:
                        obj = obj[self.markdown_data_key]
            self._save(obj=obj, filename=filename, output_dir=output_dir)

    def on_multirun_end(self, config: DictConfig, **kwargs: Any) -> None:
        """Collate a multi-run and all its jobs' data, then save it.

        Args:
            config: The multi-run's Hydra config.

        Keyword Args:
            **kwargs: Ignored; accepted for Hydra callback interface compatibility.
        """
        job_ids: list[str] | list[int] | None = None
        if self.multirun_create_ids_from_overrides:
            overrides_per_result = [jr.overrides or [] for jr in self._job_returns]
            job_ids = overrides_to_identifiers(
                overrides_per_result, sep=self.multirun_overrides_separator, remove_common=True
            )
            if job_ids is None:
                self._log.warning(
                    "Job identifiers created from overrides are not unique! "
                    "Use the job indexes instead."
                )

        if job_ids is None:
            job_ids = list[int](range(len(self._job_returns)))

        if self.multirun_add_overrides_as_dict:
            for jr in self._job_returns:
                jr.return_value["overrides"] = overrides_to_dict(
                    jr.overrides or [], remove_plus_prefix=True
                )

        if self.integrate_multirun_result:
            # WARN: list_of_dicts may return lists. There is a safety backup (the {"value": obj} wrapper),
            #   but this is very sketchy.
            #
            # rearrange the job return-values of all jobs from a multi-run into a dict of lists (maybe nested),
            obj = list_of_dicts_to_dict_of_lists_recursive(
                [jr.return_value for jr in self._job_returns]
            )
            if not isinstance(obj, dict):
                obj = {"value": obj}
            if self.multirun_create_ids_from_overrides:
                obj[self.multirun_job_id_key] = job_ids

            # also create an aggregated result
            # convert to python object to allow selecting numeric columns
            obj_py = to_py_obj(obj)
            obj_flat = flatten_dict(cast(dict[str | int, Any], obj_py))
            # create dataframe from flattened dict
            df_flat = pd.DataFrame(obj_flat)
            # select only the numeric values
            df_numbers_only = df_flat.select_dtypes(["number"])
            cols_removed: set[tuple[str | int, ...]] = (
                set(df_flat.columns) - set(df_numbers_only.columns) - {(self.multirun_job_id_key,)}  # type: ignore
            )
            if len(cols_removed) > 0:
                self._log.warning(
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
                identifier: jr.return_value for identifier, jr in zip(job_ids, self._job_returns)
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
                self._log.info(f"Contents of {output_dir / fn}:\n{contents}")

    def _save(
        self,
        obj: Any,
        filename: str,
        output_dir: Path,
        is_tabular_data: bool = False,
        unstack_last_index_level: bool = False,
        markdown_group_by: list[str] | None = None,
    ) -> None:
        """Save `obj` to `output_dir / filename` as JSON or markdown.

        The output format is chosen from the filename extension: ".json" writes the data as JSON, ".md" writes it as
        a markdown table. Any other extension raises. numpy arrays are converted to native python types beforehand.

        Args:
            obj: Data to save to file.
            filename: Output file name. Must end with ".json" or ".md".
            output_dir: Directory to save to. Created if it does not exist.
            is_tabular_data: Whether `obj` holds a whole table of data (a value per key per job) rather than a single
                Series (one value per key). Only affects markdown output.
            unstack_last_index_level: If True, unstack the last index level (the aggregation key) instead of the first
                when building the markdown table. Only relevant for markdown output of aggregated multi-run results.
            markdown_group_by: Column(s) to group the markdown table by via
                [`mixed_group_by`][kibad_llm.utils.job_return.mixed_group_by]. If None, no grouping is applied.

        Raises:
            ValueError: If obj needs to be flattened, but can't.
            ValueError: If filename has an unknown extension.
        """
        self._log.info(f"Saving job_return in {output_dir / filename}")
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
