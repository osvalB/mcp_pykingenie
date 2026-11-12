"""Tests for the steady-state and kinetics residual plotting tools.

NOTE: These tests are AI generated (Claude Code, Claude Opus 5.5).
"""

from pathlib import Path

import pandas as pd
import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

import mcp_pykingenie.tools._plotting_xy as plotting_xy_tools
import mcp_pykingenie.tools._pykingenie as pykingenie_tools
from mcp_pykingenie.mcp import mcp


RESIDUAL_TOOLS = ("plot_steady_state_residuals", "plot_kinetics_residuals")


def _load_example_and_selected_fitting():
    """Load bundled Octet data and prepare one real fitting dataset."""
    pykingenie_tools.load_octet_example()
    df = pd.DataFrame(pykingenie_tools.obtain_sample_info_table())
    df["Select"] = [True] * 8 + [False] * (len(df) - 8)
    pykingenie_tools.initiate_fitting_datasets(df.to_dict(orient="records"))


def _saved_path_from_message(message: str) -> Path:
    """Extract the generated artifact path from a tool result message."""
    assert message.startswith("Plot saved to: ")
    return Path(message.split(": ", 1)[1].strip())


def _result_text(result) -> str:
    """Return the text content of an MCP tool call result."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return result.content[0].text


def test_residual_tools_are_exported():
    """Testing residual tools are exported by the tools package."""
    import mcp_pykingenie.tools as tools

    for name in RESIDUAL_TOOLS:
        assert name in tools.__all__
        assert callable(getattr(tools, name))


@pytest.mark.asyncio
async def test_residual_tools_are_registered_on_the_mcp_server():
    """Testing residual tools are listed by the MCP server."""
    async with Client(mcp) as client:
        listed = {tool.name for tool in (await client.list_tools()).tools}

    assert set(RESIDUAL_TOOLS) <= listed


@pytest.mark.asyncio
async def test_steady_state_residuals_saves_image_and_html():
    """Testing steady-state residuals are saved as image and HTML."""
    _load_example_and_selected_fitting()
    await pykingenie_tools.run_steady_state_fitting()

    image_path = _saved_path_from_message(
        await plotting_xy_tools.plot_steady_state_residuals(save_html=True)
    )

    assert image_path.parent == Path(pykingenie_tools.DATA_DIR)
    assert image_path.name.startswith("kingenie_steady_state_residuals_xy_")
    assert image_path.suffix == ".png"
    assert image_path.is_file()
    assert image_path.with_suffix(".html").is_file()


@pytest.mark.asyncio
async def test_kinetics_residuals_saves_image_and_html():
    """Testing kinetics residuals are saved as image and HTML."""
    _load_example_and_selected_fitting()
    await pykingenie_tools.run_kinetics_fitting()

    image_path = _saved_path_from_message(
        await plotting_xy_tools.plot_kinetics_residuals(save_html=True)
    )

    assert image_path.name.startswith("kingenie_kinetics_residuals_xy_")
    assert image_path.suffix == ".png"
    assert image_path.is_file()
    assert image_path.with_suffix(".html").is_file()


@pytest.mark.asyncio
async def test_residual_plots_without_html_only_save_image():
    """Testing residual plots skip the HTML file by default."""
    _load_example_and_selected_fitting()
    await pykingenie_tools.run_steady_state_fitting()
    await pykingenie_tools.run_kinetics_fitting()

    for tool in (plotting_xy_tools.plot_steady_state_residuals,
                 plotting_xy_tools.plot_kinetics_residuals):
        image_path = _saved_path_from_message(await tool())
        assert image_path.is_file()
        assert not image_path.with_suffix(".html").exists()


@pytest.mark.asyncio
async def test_residual_plots_follow_shared_xy_configs():
    """Testing residual plots use the shared plot type and trace settings."""
    _load_example_and_selected_fitting()
    await pykingenie_tools.run_steady_state_fitting()
    await pykingenie_tools.run_kinetics_fitting()

    plotting_xy_tools.update_xy_plot_config(plot_type="svg", plot_width=600, plot_height=400)
    plotting_xy_tools.update_xy_trace_config(smooth_curves=True, rolling_window=5)
    plotting_xy_tools.update_xy_layout_config(split_by_smax_id=True)

    for tool in (plotting_xy_tools.plot_steady_state_residuals,
                 plotting_xy_tools.plot_kinetics_residuals):
        image_path = _saved_path_from_message(await tool())
        assert image_path.suffix == ".svg"
        assert image_path.is_file()


@pytest.mark.asyncio
async def test_kinetics_plots_use_blues_palette():
    """Testing the kinetics plots color concentrations with the Blues palette."""
    _load_example_and_selected_fitting()
    await pykingenie_tools.run_kinetics_fitting()

    plotting_xy_tools.update_xy_plot_config(plot_type="svg", palette="blues")

    for tool in (plotting_xy_tools.plot_kinetic_traces,
                 plotting_xy_tools.plot_kinetics_residuals):
        image_path = _saved_path_from_message(await tool())
        svg = image_path.read_text().lower()
        # The highest concentration takes the darkest Blues color.
        assert "#08306b" in svg or "rgb(8,48,107)" in svg.replace(" ", "")
        assert "#fde725" not in svg  # brightest Viridis color


@pytest.mark.asyncio
async def test_steady_state_residuals_requires_steady_state_fit():
    """Testing steady-state residuals report a missing steady-state fit."""
    _load_example_and_selected_fitting()
    # A kinetic fit alone does not provide steady-state residuals.
    await pykingenie_tools.run_kinetics_fitting()

    with pytest.raises(ToolError, match="No steady-state fits"):
        await plotting_xy_tools.plot_steady_state_residuals()


@pytest.mark.asyncio
async def test_kinetics_residuals_requires_kinetics_fit():
    """Testing kinetics residuals report a missing kinetics fit."""
    _load_example_and_selected_fitting()
    # A steady-state fit alone does not provide kinetics residuals.
    await pykingenie_tools.run_steady_state_fitting()

    with pytest.raises(ToolError, match="No kinetics fits"):
        await plotting_xy_tools.plot_kinetics_residuals()


@pytest.mark.asyncio
async def test_residual_tools_through_mcp_client():
    """Testing residual tools end to end through the MCP client."""
    async with Client(mcp) as client:
        await client.call_tool("load_octet_example", {})
        sample_info = pd.DataFrame(pykingenie_tools.obtain_sample_info_table())
        sample_info["Select"] = [True] * 8 + [False] * (len(sample_info) - 8)
        await client.call_tool(
            "initiate_fitting_datasets",
            {"sample_info": sample_info.to_dict(orient="records")},
        )

        # Before fitting, both tools return an error to the client.
        for tool in RESIDUAL_TOOLS:
            result = await client.call_tool(tool, {})
            assert result.is_error
            assert "run the fitting first" in _result_text(result)

        await client.call_tool("run_steady_state_fitting", {})
        await client.call_tool("run_kinetics_fitting", {})

        for tool in RESIDUAL_TOOLS:
            result = await client.call_tool(tool, {"save_html": True})
            assert not result.is_error
            image_path = _saved_path_from_message(_result_text(result))
            assert image_path.is_file()
            assert image_path.with_suffix(".html").is_file()
