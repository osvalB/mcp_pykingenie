from importlib.metadata import version
import importlib
from io import StringIO
from pathlib import Path
import runpy
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from fastmcp import Client
from packaging.version import Version

import mcp_pykingenie
import mcp_pykingenie.server as server
import mcp_pykingenie.stdio as stdio_module
import mcp_pykingenie.tools._pykingenie as pykingenie_tools
from mcp_pykingenie.main import run_app
import mcp_pykingenie.main as main_module
from mcp_pykingenie.paths import (
    RESULTS_DIR_ENV_VAR,
    USER_DATA_DIR_NAME,
    get_example_data_root,
    get_user_data_root,
)


MIN_PYKINGENIE_VERSION = Version("1.0.0")
TEST_DATA_DIR = Path(__file__).parent / "data"


def _load_example_and_selected_fitting():
    """Load bundled Octet data and prepare one real fitting dataset."""
    pykingenie_tools.load_octet_example()
    df_json = pykingenie_tools.obtain_sample_info_table()
    df = pd.read_json(StringIO(df_json), orient='records')
    df["Select"] = [True] * 8 + [False] * (len(df) - 8)
    pykingenie_tools.initiate_fitting_datasets(df.to_json(orient='records'))
    return df


def _saved_path_from_message(message: str) -> Path:
    """Extract the generated artifact path from a tool result message."""
    return Path(message.split(": ", 1)[1].strip())


class AsyncLineStream:
    """Minimal async iterator for stdio tests."""

    def __init__(self, lines):
        """Store raw lines to be yielded asynchronously."""
        self._lines = iter(lines)

    def __aiter__(self):
        """Return this object as its async iterator."""
        return self

    async def __anext__(self):
        """Return the next raw line or stop asynchronous iteration."""
        try:
            return next(self._lines)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeMcpRunner:
    """Minimal MCP server runner for stdio transport tests."""

    def __init__(self):
        """Initialize captured initialization and run calls."""
        self.initialization_options = None
        self.run_call = None

    def create_initialization_options(self, notification_options):
        """Capture and return initialization options."""
        self.initialization_options = notification_options
        return {"notification_options": notification_options}

    async def run(self, read_stream, write_stream, initialization_options, stateless=False):
        """Capture the server run call arguments."""
        self.run_call = {
            "read_stream": read_stream,
            "write_stream": write_stream,
            "initialization_options": initialization_options,
            "stateless": stateless,
        }


class FakeFastMcpServer:
    """Minimal FastMCP-like server for stdio transport tests."""

    name = "fake-server"
    version = None

    def __init__(self):
        """Initialize the fake MCP runner and lifespan event log."""
        self._mcp_server = FakeMcpRunner()
        self.lifespan_events = []

    @stdio_module.asynccontextmanager
    async def _lifespan_manager(self):
        """Record entry and exit from the server lifespan."""
        self.lifespan_events.append("enter")
        try:
            yield
        finally:
            self.lifespan_events.append("exit")


def test_package_has_version():
    """Testing package version exist."""
    assert mcp_pykingenie.__version__ is not None


def test_pykingenie_version():
    """Testing pykingenie version used by the test environment."""
    assert Version(version("pykingenie")) >= MIN_PYKINGENIE_VERSION


def test_user_data_root_defaults_to_home(monkeypatch):
    """Testing default root folder for generated files."""
    monkeypatch.delenv(RESULTS_DIR_ENV_VAR, raising=False)
    assert get_user_data_root() == Path.home() / USER_DATA_DIR_NAME


def test_user_data_root_uses_configured_results_dir(monkeypatch, tmp_path):
    """Testing RESULTS_DIR override for generated files."""
    results_dir = tmp_path / "results"
    monkeypatch.setenv(RESULTS_DIR_ENV_VAR, str(results_dir))
    assert get_user_data_root() == results_dir.resolve()


def test_example_data_root_points_to_packaged_data():
    """Testing packaged example data folder resolution."""
    example_data_dir = get_example_data_root()
    assert example_data_dir.is_dir()
    assert (example_data_dir / "test_bli_folder").is_dir()


def test_server_instructions_show_current_data_folder():
    """Testing server instructions include the current output folder."""
    assert server.DATA_DIR in server.SERVER_INSTRUCTIONS
    assert "Plots and generated files for this session are saved in:" in server.SERVER_INSTRUCTIONS


def test_server_import_creates_results_directories(monkeypatch, tmp_path):
    """Testing server startup creates the base and dated results folders."""
    results_dir = tmp_path / "created-results"
    monkeypatch.setenv(RESULTS_DIR_ENV_VAR, str(results_dir))
    monkeypatch.delenv("MCP_PYKINGENIE_SKIP_USER_DATA_INIT", raising=False)

    reloaded_server = importlib.reload(server)

    assert results_dir.is_dir()
    assert Path(reloaded_server.DATA_DIR).is_dir()
    assert Path(reloaded_server.DATA_DIR).parent == results_dir


def test_cli_prints_results_folder():
    """Testing CLI reports the active results folder at startup."""
    runner = CliRunner()
    calls = []

    with patch.object(stdio_module, "run_stdio", lambda server: calls.append({"transport": "stdio"})):
        result = runner.invoke(run_app, [])

    assert result.exit_code == 0
    assert calls == [{"transport": "stdio"}]
    assert f"mcp_pykingenie results folder: {server.DATA_DIR}" in result.stderr


def test_cli_version_prints_package_version_without_starting_transport():
    """Testing CLI version flag returns the installed package version."""
    runner = CliRunner()

    result = runner.invoke(run_app, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"{mcp_pykingenie.__version__}\n"


def test_development_transport_http_and_custom_modes_call_mcp_run():
    """Testing development transport dispatch without starting real servers."""
    calls = []
    fake_mcp = SimpleNamespace(run=lambda **kwargs: calls.append(kwargs))

    main_module.run_development_transport(fake_mcp, "http", 8123, "127.0.0.1")
    main_module.run_development_transport(fake_mcp, "sse", 8124, "localhost")

    assert calls == [
        {"transport": "http", "port": 8123, "host": "127.0.0.1"},
        {"transport": "sse"},
    ]


def test_cli_production_environment_is_not_implemented():
    """Testing production mode currently reports that it is not implemented."""
    runner = CliRunner()

    result = runner.invoke(run_app, ["--env", "production"])

    assert isinstance(result.exception, NotImplementedError)


def test_main_module_entrypoint_prints_version():
    """Testing python -m style module entrypoint."""
    with patch.object(sys, "argv", ["mcp_pykingenie.main", "--version"]):
        with pytest.warns(RuntimeWarning, match="mcp_pykingenie.main"):
            with pytest.raises(SystemExit) as exc_info:
                runpy.run_module("mcp_pykingenie.main", run_name="__main__")

    assert exc_info.value.code == 0


def test_package_entrypoint_prints_version():
    """Testing package __init__ entrypoint guard."""
    init_path = Path(mcp_pykingenie.__file__)

    with patch.object(sys, "argv", [str(init_path), "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(init_path), run_name="__main__")

    assert exc_info.value.code == 0


@pytest.mark.asyncio
async def test_stdio_server_ignores_empty_lines():
    """Testing stdio transport filters blank JSON-RPC lines."""
    observed_lines = []

    @stdio_module.asynccontextmanager
    async def fake_stdio_server(stdin=None, stdout=None):
        """Capture the first non-empty line sent to the stdio transport."""
        async for line in stdin:
            observed_lines.append(line)
            break
        yield "read-stream", "write-stream"

    with patch.object(stdio_module, "stdio_server", fake_stdio_server):
        async with stdio_module.stdio_server_ignoring_empty_lines(
            stdin=AsyncLineStream(["\n", "   \n", '{"jsonrpc":"2.0","id":1,"method":"ping"}\n']),
            stdout=object(),
        ) as streams:
            assert streams == ("read-stream", "write-stream")

    assert observed_lines == ['{"jsonrpc":"2.0","id":1,"method":"ping"}\n']


@pytest.mark.asyncio
async def test_stdio_transport_defaults_to_process_stdin():
    """Testing stdio helper wraps process stdin by default."""
    observed_lines = []

    @stdio_module.asynccontextmanager
    async def fake_stdio_server(stdin=None, stdout=None):
        """Capture the default stdin stream after empty lines are filtered."""
        async for line in stdin:
            observed_lines.append(line)
            break
        yield "read-stream", "write-stream"

    with (
        patch.object(stdio_module.sys, "stdin", SimpleNamespace(buffer="raw-stdin")),
        patch.object(stdio_module, "TextIOWrapper", lambda buffer, encoding: f"{encoding}:{buffer}"),
        patch.object(
            stdio_module.anyio,
            "wrap_file",
            lambda stream: AsyncLineStream(["\n", '{"jsonrpc":"2.0","id":1,"method":"ping"}\n']),
        ),
        patch.object(stdio_module, "stdio_server", fake_stdio_server),
    ):
        async with stdio_module.stdio_server_ignoring_empty_lines():
            pass

    assert observed_lines[0].strip().startswith("{")


def test_run_stdio_sync_wrapper_dispatches_anyio_run():
    """Testing synchronous stdio wrapper delegates execution to anyio."""
    calls = []

    with patch.object(stdio_module.anyio, "run", lambda runner: calls.append(runner)):
        stdio_module.run_stdio("server", stateless=True)

    assert calls


@pytest.mark.asyncio
async def test_run_stdio_ignoring_empty_lines_runs_lifespan_and_mcp_server():
    """Testing stdio runner enters lifespan, configures streams, and resets cleanly."""
    fake_server = FakeFastMcpServer()
    stdio_events = []

    @stdio_module.asynccontextmanager
    async def fake_stdio_context():
        """Yield fake read/write streams and record context events."""
        stdio_events.append("enter")
        try:
            yield "read-stream", "write-stream"
        finally:
            stdio_events.append("exit")

    await stdio_module.run_stdio_ignoring_empty_lines(
        fake_server,
        show_banner=False,
        log_level="INFO",
        stateless=True,
        stdio_context=fake_stdio_context,
    )

    assert fake_server.lifespan_events == ["enter", "exit"]
    assert stdio_events == ["enter", "exit"]
    assert fake_server._mcp_server.initialization_options.tools_changed is True
    assert fake_server._mcp_server.run_call == {
        "read_stream": "read-stream",
        "write_stream": "write-stream",
        "initialization_options": {
            "notification_options": fake_server._mcp_server.initialization_options,
        },
        "stateless": True,
    }


@pytest.mark.asyncio
async def test_run_stdio_ignoring_empty_lines_uses_default_context_and_banner():
    """Testing stdio runner resolves the default context and can show the banner."""
    fake_server = FakeFastMcpServer()

    @stdio_module.asynccontextmanager
    async def fake_stdio_context():
        """Yield fake read/write streams for default-context resolution."""
        yield "read-stream", "write-stream"

    with patch.object(stdio_module, "stdio_server_ignoring_empty_lines", fake_stdio_context):
        await stdio_module.run_stdio_ignoring_empty_lines(
            fake_server,
            stateless=False,
        )

    assert fake_server._mcp_server.run_call["stateless"] is False


def test_list_files_in_folder_returns_only_real_files(tmp_path):
    """Testing folder listing uses the real filesystem and ignores folders."""
    folder = tmp_path / "files"
    folder.mkdir()
    (folder / "alpha.txt").write_text("alpha")
    (folder / "beta.csv").write_text("beta")
    (folder / "nested").mkdir()

    files = pykingenie_tools.list_files_in_folder(str(folder))

    assert set(files) == {"alpha.txt", "beta.csv"}


def test_list_files_in_folder_reports_missing_folder():
    """Testing folder listing reports inaccessible folders."""
    missing_folder = Path(server.DATA_DIR) / "does-not-exist"

    with pytest.raises(FileNotFoundError, match="does-not-exist"):
        pykingenie_tools.list_files_in_folder(str(missing_folder))


def test_list_files_in_folder_requires_folder_argument():
    """Testing folder listing returns a useful error for empty input."""
    result = pykingenie_tools.list_files_in_folder()

    assert isinstance(result, FileNotFoundError)
    assert str(result) == "No folder provided. Please specify a folder."


def test_import_octet_experiment_accepts_folder_relative_to_data_dir():
    """Testing Octet import resolves relative folders from the active data dir."""
    relative_folder = "relative_octet"
    shutil.copytree(
        get_example_data_root() / "test_bli_folder",
        Path(server.DATA_DIR) / relative_folder,
    )

    message = pykingenie_tools.import_octet_experiment(relative_folder, "Relative Experiment")

    assert message == f"Octet experiment added from {relative_folder}."
    assert pykingenie_tools.list_experiment_names() == ["Relative Experiment"]


def test_import_gator_experiment_accepts_folder_relative_to_data_dir():
    """Testing Gator import resolves relative folders from the active data dir."""
    relative_folder = "gator_minimal"
    shutil.copytree(
        TEST_DATA_DIR / relative_folder,
        Path(server.DATA_DIR) / relative_folder,
    )

    message = pykingenie_tools.import_gator_experiment(relative_folder, "Gator Example")

    experiment = server.PY_KINETICS.experiments["Gator Example"]
    assert message == f"Gator experiment added from {relative_folder}."
    assert pykingenie_tools.list_experiment_names() == ["Gator Example"]
    assert experiment.sensor_names == ["A", "B", "C", "D", "E", "F", "G", "H"]
    assert len(experiment.xs) == 8
    assert experiment.no_steps > 0
    assert len(experiment.xs[0]) > 0
    assert experiment.ligand_conc_df["SampleID"].str.contains("EGFR-Cetuximab").any()


def test_import_gator_experiment_accepts_absolute_zip_file():
    """Testing Gator import extracts and reads a real zip file."""
    zip_stem = "gator_zip_case"
    zip_path = Path(server.DATA_DIR) / f"{zip_stem}.zip"

    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for source_file in (TEST_DATA_DIR / "gator_minimal").iterdir():
            zip_file.write(source_file, Path(zip_stem) / source_file.name)

    message = pykingenie_tools.import_gator_experiment(str(zip_path), "Gator Zip Example")

    experiment = server.PY_KINETICS.experiments["Gator Zip Example"]
    assert message == f"Gator experiment added from {zip_stem}."
    assert experiment.sensor_names == ["A", "B", "C", "D", "E", "F", "G", "H"]
    assert experiment.no_steps > 0
    assert len(experiment.xs[0]) > 0


def test_import_kingenie_surface_csv_accepts_relative_and_absolute_paths():
    """Testing KinGenie CSV import uses real simulation CSV files."""
    csv_name = "single_cycle_kingenie.csv"
    csv_path = Path(server.DATA_DIR) / csv_name
    shutil.copy2(TEST_DATA_DIR / csv_name, csv_path)

    relative_message = pykingenie_tools.import_kingenie_surface_csv(csv_name, "CSV Experiment")
    absolute_message = pykingenie_tools.import_kingenie_surface_csv(str(csv_path), "CSV Experiment")

    experiment = server.PY_KINETICS.experiments["CSV Experiment"]
    duplicate_experiment = server.PY_KINETICS.experiments["CSV Experiment1"]
    assert relative_message == f"Experiment added from {csv_name}."
    assert absolute_message == f"Experiment added from {csv_path}."
    assert pykingenie_tools.list_experiment_names() == ["CSV Experiment", "CSV Experiment1"]
    assert experiment.sensor_names == ["sim. sensor 1"]
    assert duplicate_experiment.sensor_names == ["sim. sensor 1"]
    assert len(experiment.xs[0]) > 0
    assert len(experiment.ligand_conc_df) == 8


def test_numeric_experiment_id_and_reference_index_use_loaded_octet_data():
    """Testing numeric selectors operate on the real loaded experiment."""
    pykingenie_tools.load_octet_example()

    association_message = pykingenie_tools.align_association(experiment_id="1")
    dissociation_message = pykingenie_tools.align_dissociation(experiment_id="1")
    subtraction_message = pykingenie_tools.subtract_reference(experiment_id="1", reference_sensor="1")

    assert "Association phase aligned for experiment: Example Experiment" in association_message
    assert "Dissociation phase aligned for experiment: Example Experiment" in dissociation_message
    assert "Reference sensor 'H1' subtracted" in subtraction_message
    assert "H1" in server.PY_KINETICS.experiments["Example Experiment"].sensor_names


def test_invalid_experiment_selectors_return_not_found_messages():
    """Testing invalid experiment selectors report the expected error text."""
    pykingenie_tools.load_octet_example()

    expected = "Experiment with index 99 not found in kingenie."

    assert pykingenie_tools.plot_sample_plate_info(experiment_id="99") == expected
    assert pykingenie_tools.align_association(experiment_id="99") == expected
    assert pykingenie_tools.subtract_reference(experiment_id="99") == expected
    assert pykingenie_tools.align_dissociation(experiment_id="99") == expected
    assert pykingenie_tools.align_and_subtract(experiment_id="99") == expected

    with pytest.raises(KeyError, match=expected):
        pykingenie_tools.list_experiment_attributes("99")


def test_invalid_reference_selectors_return_not_found_messages():
    """Testing invalid reference selectors report the expected error text."""
    pykingenie_tools.load_octet_example()

    assert (
        pykingenie_tools.subtract_reference(experiment_id="Example Experiment", reference_sensor="99")
        == "Reference sensor '99' not found in the list of sensors for experiment 'Example Experiment'."
    )
    assert (
        pykingenie_tools.align_and_subtract(experiment_id="Example Experiment", reference_sensor="missing")
        == "Reference sensor 'missing' not found in the list of sensors for experiment 'Example Experiment'."
    )


def test_experiment_properties_and_attributes_reflect_loaded_data():
    """Testing property and attribute tools inspect a real loaded experiment."""
    pykingenie_tools.load_octet_example()

    sensor_names = pykingenie_tools.list_experiment_properties("sensor_names")
    attributes = pykingenie_tools.list_experiment_attributes("1")

    assert sensor_names == [["H1", "G1", "F1", "D1", "E1", "A1", "B1", "C1"]]
    assert attributes["sensor_names"] == ["H1", "G1", "F1", "D1", "E1", "A1", "B1", "C1"]
    assert "sensor_names_unique" in attributes


def test_align_and_subtract_runs_real_combined_workflow():
    """Testing combined alignment/subtraction mutates the real experiment."""
    pykingenie_tools.load_octet_example()

    message = pykingenie_tools.align_and_subtract(
        experiment_id="Example Experiment",
        reference_sensor="H1",
        align_dissociation=True,
    )

    sensor_names = server.PY_KINETICS.experiments["Example Experiment"].sensor_names
    assert "Association phase aligned and reference sensor 'H1' subtracted" in message
    assert "Dissociation phase aligned" in message
    assert "G1 - H1" in sensor_names
    assert "H1" in sensor_names


@pytest.mark.asyncio
async def test_plot_tools_save_html_artifacts_for_real_octet_data():
    """Testing plot tools produce real image and HTML artifacts."""
    _load_example_and_selected_fitting()

    all_steps_path = _saved_path_from_message(
        await pykingenie_tools.plot_traces_with_all_steps(
            save_html=True,
        )
    )
    steady_state_path = _saved_path_from_message(await pykingenie_tools.plot_steady_state(save_html=True))
    kinetic_traces_path = _saved_path_from_message(await pykingenie_tools.plot_kinetic_traces(save_html=True))

    for image_path in [all_steps_path, steady_state_path, kinetic_traces_path]:
        assert image_path.is_file()
        assert image_path.with_suffix(".html").is_file()


def test_sample_plate_plot_saves_image_and_html_for_numeric_experiment_id():
    """Testing sample plate plotting resolves numeric IDs against real data."""
    pykingenie_tools.load_octet_example()

    image_path = _saved_path_from_message(
        pykingenie_tools.plot_sample_plate_info(
            experiment_id="1",
            save_html=True,
        )
    )

    assert image_path.is_file()
    assert image_path.with_suffix(".html").is_file()


def test_sample_plate_plot_accepts_experiment_name():
    """Testing sample plate plotting accepts a real experiment name."""
    pykingenie_tools.load_octet_example()

    image_path = _saved_path_from_message(
        pykingenie_tools.plot_sample_plate_info(
            experiment_id="Example Experiment",
        )
    )

    assert image_path.is_file()


def test_initiate_fitting_datasets_falls_back_to_default_table_for_invalid_json():
    """Testing invalid JSON uses the real default sample table."""
    pykingenie_tools.load_octet_example()

    message = pykingenie_tools.initiate_fitting_datasets("not valid json")

    assert "Fitting datasets generated with the following names:" in message
    assert pykingenie_tools.PY_KINETICS.fittings_names


@pytest.mark.asyncio
async def test_mcp_server():
    """Testing MCP server."""
    async with Client(mcp_pykingenie.mcp) as client:
        result = await client.call_tool("print_data_dir", {})
        assert result.data == server.DATA_DIR

        result = await client.call_tool("load_octet_example", {})
        assert "Octet experiment added from" in result.data

        result = await client.call_tool("get_legends_table", {})
        df_json = result.data
        df = pd.read_json(StringIO(df_json), orient='records')

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"Internal_ID", "Color", "Legend", "Show"}
        assert set(df["Legend"]) == {"A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"}

        result = await client.call_tool("plot_traces_with_all_steps", {"legends_df": df_json})

        assert "Plot saved to" in result.data

        result = await client.call_tool("list_experiment_names", {})

        assert 'Example Experiment' == result.data[0]

        result = await client.call_tool("align_association", {"experiment_id": "Example Experiment"})

        assert "Association phase aligned for experiment" in result.data

        result = await client.call_tool("align_dissociation", {"experiment_id": "Example Experiment"})

        assert "Dissociation phase aligned for experiment" in result.data

        result = await client.call_tool("subtract_reference", {"reference_sensor": "H1"})

        assert "Reference sensor" in result.data

        result = await client.call_tool("obtain_sample_info_table", {})

        df_json = result.data
        df = pd.read_json(StringIO(df_json), orient='records')

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {
            "Sensor",
            "[Analyte] (\u03bcM)",
            "SampleID",
            "Select",
            "Smax_ID",
            "Analyte_location",
            "Loading_location",
            "Replicate",
        }
        assert len(df) == 72
        assert "wt - imd" in set(df["SampleID"])

        # Set only the first eight rows to True
        df["Select"] = [True] * 8 + [False] * (len(df) - 8)

        df_json_new = df.to_json(orient='records')

        result = await client.call_tool("initiate_fitting_datasets", {"json_str": df_json_new})

        assert "Fitting datasets generated" in result.data

        result = await client.call_tool("plot_steady_state", {})

        assert "Plot saved to" in result.data

        result = await client.call_tool("plot_kinetic_traces", {})

        assert "Plot saved to" in result.data

        result = await client.call_tool("run_fitting", {})
        assert (
            "Fitting submitted with model: one_to_one, "
            "region: association_dissociation, linked Smax: False."
        ) == result.data

        result = await client.call_tool("get_kinetics_fitting_results", {})

        results_json = result.data
        df = pd.read_json(StringIO(results_json), orient='records')
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {
            "Kd [\u00b5M]",
            "k_off [1/s]",
            "Smax",
            "(Derived) k_on [1/\u00b5M/s]",
            "Name",
        }
        assert len(df) == 7
        assert df["Name"].unique().tolist() == ["wt - imd"]

        np.testing.assert_allclose(df.loc[0, "k_off [1/s]"], 0.00235, rtol=0.01)
