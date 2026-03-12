import pytest
import pandas as pd
import  numpy as np

from io import StringIO
from fastmcp import Client

import mcp_pykingenie


def test_package_has_version():
    """Testing package version exist."""
    assert mcp_pykingenie.__version__ is not None


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

        result = await client.call_tool("plot_traces_with_all_steps", {"legends_df" : df_json})

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
        result = await client.call_tool("get_kinetics_fitting_results", {})

        json = result.data
        df = pd.read_json(StringIO(json), orient='records')
        assert isinstance(df, pd.DataFrame)

        np.testing.assert_allclose(df.iloc[0,1],0.00235,rtol=0.01)




