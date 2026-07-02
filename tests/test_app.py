from importlib.metadata import version
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from fastmcp import Client
from packaging.version import Version

import mcp_pykingenie
import mcp_pykingenie.server as server
import mcp_pykingenie.stdio as stdio_module
from mcp_pykingenie.main import run_app
from mcp_pykingenie.paths import (
    RESULTS_DIR_ENV_VAR,
    USER_DATA_DIR_NAME,
    get_example_data_root,
    get_user_data_root,
)


MIN_PYKINGENIE_VERSION = Version("1.0.0")


class AsyncLineStream:
    """Minimal async iterator for stdio tests."""

    def __init__(self, lines):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


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


def test_cli_prints_results_folder():
    """Testing CLI reports the active results folder at startup."""
    runner = CliRunner()
    calls = []

    with patch.object(stdio_module, "run_stdio", lambda server: calls.append({"transport": "stdio"})):
        result = runner.invoke(run_app, [])

    assert result.exit_code == 0
    assert calls == [{"transport": "stdio"}]
    assert f"mcp_pykingenie results folder: {server.DATA_DIR}" in result.stderr


@pytest.mark.asyncio
async def test_stdio_server_ignores_empty_lines():
    """Testing stdio transport filters blank JSON-RPC lines."""
    observed_lines = []

    @stdio_module.asynccontextmanager
    async def fake_stdio_server(stdin=None, stdout=None):
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
