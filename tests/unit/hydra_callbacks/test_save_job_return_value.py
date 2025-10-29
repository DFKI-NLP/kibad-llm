import json

from hydra.core.utils import JobReturn, JobStatus
from omegaconf import OmegaConf
import pytest

from kibad_llm.hydra_callbacks import SaveJobReturnValueCallback


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_config(temp_output_dir):
    """Create a mock Hydra config."""
    config = OmegaConf.create(
        {
            "hydra": {
                "runtime": {"output_dir": str(temp_output_dir)},
                "sweep": {"dir": str(temp_output_dir / "multirun")},
            }
        }
    )
    return config


def _construct_job_return(overrides, return_value) -> JobReturn:
    """Helper function to construct a JobReturn object."""
    job_return = JobReturn(overrides=overrides)
    job_return.return_value = return_value
    job_return.status = JobStatus.COMPLETED
    return job_return


@pytest.fixture(params=["json", "md"])
def extension(request):
    """Fixture for different file extensions."""
    return request.param


class TestSaveJobReturnValueCallback:

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        callback = SaveJobReturnValueCallback()
        assert callback.filenames == ["job_return_value.json"]
        assert callback.integrate_multirun_result is False
        assert callback.multirun_job_id_key == "job_id"

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        callback = SaveJobReturnValueCallback(
            filenames=["result.json", "result.md"],
            integrate_multirun_result=True,
            multirun_job_id_key="run_id",
        )
        assert callback.filenames == ["result.json", "result.md"]
        assert callback.integrate_multirun_result is True
        assert callback.multirun_job_id_key == "run_id"

    def test_on_job_end_saves(self, mock_config, temp_output_dir, extension):
        """Test that on_job_end saves JSON file correctly."""

        callback = SaveJobReturnValueCallback(
            filenames=f"result.{extension}",
            integrate_multirun_result=False,
        )
        job_return = _construct_job_return(
            overrides=["model=resnet", "lr=0.001"], return_value={"accuracy": 0.95, "loss": 0.05}
        )
        callback.on_job_end(config=mock_config, job_return=job_return)

        file_name = temp_output_dir / f"result.{extension}"
        assert file_name.exists()

        if extension == "json":
            with open(file_name) as f:
                data = json.load(f)
            assert data == {"accuracy": 0.95, "loss": 0.05}
        elif extension == "md":
            content = file_name.read_text()
            assert content == (
                "|          |    0 |\n"
                "|:---------|-----:|\n"
                "| accuracy | 0.95 |\n"
                "| loss     | 0.05 |"
            )
        else:
            pytest.fail(f"Unsupported extension: {extension}")

    def test_on_job_end_multiple_files(self, mock_config, temp_output_dir):
        """Test saving to multiple file formats."""
        job_return = _construct_job_return(
            overrides=["model=resnet", "lr=0.001"], return_value={"accuracy": 0.95, "loss": 0.05}
        )

        callback = SaveJobReturnValueCallback(filenames=["result.json", "result.md"])
        callback.on_job_end(config=mock_config, job_return=job_return)

        assert (temp_output_dir / "result.json").exists()
        assert (temp_output_dir / "result.md").exists()

    def test_paths_file_creation(self, mock_config, temp_output_dir, tmp_path):
        """Test creation of paths file."""
        job_return = _construct_job_return(
            overrides=["model=resnet", "lr=0.001"], return_value={"accuracy": 0.95, "loss": 0.05}
        )

        paths_file = tmp_path / "paths.txt"
        callback = SaveJobReturnValueCallback(filenames="result.json", paths_file=str(paths_file))

        callback.on_job_end(config=mock_config, job_return=job_return)

        assert paths_file.exists()
        content = paths_file.read_text()
        assert str(temp_output_dir) in content

    def test_multirun_without_integration(self, mock_config, temp_output_dir, extension):
        """Test multirun result saving without integration."""
        callback = SaveJobReturnValueCallback(
            filenames=f"multirun.{extension}",
            integrate_multirun_result=False,
            multirun_create_ids_from_overrides=False,
        )

        # Simulate multiple jobs
        for accuracy, lr in [(0.90, "0.001"), (0.92, "0.01"), (0.88, "0.1")]:
            jr = _construct_job_return(overrides=[f"lr={lr}"], return_value={"accuracy": accuracy})
            callback.job_returns.append(jr)

        callback.on_multirun_end(config=mock_config)

        multirun_dir = temp_output_dir / "multirun"
        fn = multirun_dir / f"multirun.{extension}"
        assert fn.exists()
        if extension == "json":
            with open(fn) as f:
                data_json = json.load(f)
            assert data_json == {
                "0": {"accuracy": 0.9},
                "1": {"accuracy": 0.92},
                "2": {"accuracy": 0.88},
            }
        elif extension == "md":
            content = fn.read_text()
            assert content == (
                "|    |   accuracy |\n"
                "|---:|-----------:|\n"
                "|  0 |       0.9  |\n"
                "|  1 |       0.92 |\n"
                "|  2 |       0.88 |"
            )
        else:
            pytest.fail(f"Unsupported extension: {extension}")

    def test_multirun_with_aggregation(self, mock_config, temp_output_dir, extension):
        """Test multirun result with aggregation."""
        callback = SaveJobReturnValueCallback(
            filenames=f"multirun.{extension}",
            integrate_multirun_result=True,
            multirun_create_ids_from_overrides=False,
        )

        for accuracy in [0.90, 0.92, 0.88]:
            jr = _construct_job_return(overrides=[], return_value={"accuracy": accuracy})
            callback.job_returns.append(jr)

        callback.on_multirun_end(config=mock_config)

        multirun_dir = temp_output_dir / "multirun"
        fn = multirun_dir / f"multirun.{extension}"
        assert fn.exists()
        fn_aggregated = multirun_dir / f"multirun.aggregated.{extension}"
        assert fn_aggregated.exists()

        # check individual results
        if extension == "json":
            with open(fn) as f:
                data = json.load(f)
            assert data == {"accuracy": [0.9, 0.92, 0.88]}
            # check aggregated result
            with open(fn_aggregated) as f:
                data_aggregated = json.load(f)
            assert data_aggregated == {
                "accuracy": {
                    "25%": pytest.approx(0.89),
                    "50%": pytest.approx(0.9),
                    "75%": pytest.approx(0.91),
                    "count": 3.0,
                    "max": 0.92,
                    "mean": 0.9,
                    "min": 0.88,
                    "std": pytest.approx(0.02),
                }
            }

        elif extension == "md":
            content = fn.read_text()
            assert content == (
                "|    |   ('accuracy',) |\n"
                "|---:|----------------:|\n"
                "|  0 |            0.9  |\n"
                "|  1 |            0.92 |\n"
                "|  2 |            0.88 |"
            )
            # check aggregated
            content_aggregated = fn_aggregated.read_text()
            assert content_aggregated == (
                "|          |   25% |   50% |   75% |   count |   max |   mean |   min |   std |\n"
                "|:---------|------:|------:|------:|--------:|------:|-------:|------:|------:|\n"
                "| accuracy |  0.89 |   0.9 |  0.91 |       3 |  0.92 |    0.9 |  0.88 |  0.02 |"
            )

    def test_multirun_ids_from_overrides(self, mock_config, temp_output_dir, extension):
        """Test creating job IDs from overrides."""
        callback = SaveJobReturnValueCallback(
            filenames=f"multirun.{extension}",
            integrate_multirun_result=True,
            multirun_create_ids_from_overrides=True,
        )

        for accuracy, lr in [(0.90, "0.001"), (0.92, "0.01"), (0.88, "0.1")]:
            jr = _construct_job_return(
                overrides=[f"lr={lr}", "bs=32"], return_value={"accuracy": accuracy}
            )
            callback.job_returns.append(jr)
        callback.on_multirun_end(config=mock_config)

        multirun_dir = temp_output_dir / "multirun"
        fn = multirun_dir / f"multirun.{extension}"
        assert fn.exists()
        if extension == "json":
            with open(fn) as f:
                data = json.load(f)
            assert data == {
                "accuracy": [0.9, 0.92, 0.88],
                "job_id": ["lr=0.001", "lr=0.01", "lr=0.1"],
            }
        elif extension == "md":
            content = fn.read_text()
            assert content == (
                "| job_id   |   ('accuracy',) |\n"
                "|:---------|----------------:|\n"
                "| lr=0.001 |            0.9  |\n"
                "| lr=0.01  |            0.92 |\n"
                "| lr=0.1   |            0.88 |"
            )
        else:
            pytest.fail(f"Unsupported extension: {extension}")

    def test_multirun_ids_from_multiple_overrides(self, mock_config, temp_output_dir, extension):
        """Test creating job IDs from multiple overrides."""
        callback = SaveJobReturnValueCallback(
            filenames=f"multirun.{extension}",
            integrate_multirun_result=True,
            multirun_create_ids_from_overrides=True,
        )

        for accuracy, lr, bs in [(0.90, "0.001", 32), (0.92, "0.01", 64), (0.88, "0.1", 128)]:
            jr = _construct_job_return(
                overrides=[f"lr={lr}", f"bs={bs}"], return_value={"accuracy": accuracy}
            )
            callback.job_returns.append(jr)
        callback.on_multirun_end(config=mock_config)

        multirun_dir = temp_output_dir / "multirun"
        fn = multirun_dir / f"multirun.{extension}"
        assert fn.exists()
        if extension == "json":
            with open(fn) as f:
                data = json.load(f)
            assert data == {
                "accuracy": [0.9, 0.92, 0.88],
                "job_id": ["lr=0.001-bs=32", "lr=0.01-bs=64", "lr=0.1-bs=128"],
            }
        elif extension == "md":
            content = fn.read_text()
            assert content == (
                "| job_id         |   ('accuracy',) |\n"
                "|:---------------|----------------:|\n"
                "| lr=0.001-bs=32 |            0.9  |\n"
                "| lr=0.01-bs=64  |            0.92 |\n"
                "| lr=0.1-bs=128  |            0.88 |"
            )
