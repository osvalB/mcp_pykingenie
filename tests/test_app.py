from importlib.metadata import version
from io import StringIO

import numpy as np
import pandas as pd
import pytest
from fastmcp import Client
from packaging.version import Version

import mcp_pykingenie


MIN_PYKINGENIE_VERSION = Version("1.0.0")


def test_package_has_version():
    """Testing package version exist."""
    assert mcp_pykingenie.__version__ is not None


def test_pykingenie_version():
    """Testing pykingenie version used by the test environment."""
    assert Version(version("pykingenie")) >= MIN_PYKINGENIE_VERSION


@pytest.mark.asyncio
async def test_mcp_server():
    """Testing MCP server."""
    async with Client(mcp_pykingenie.mcp) as client:
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
