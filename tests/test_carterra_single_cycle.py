"""Carterra single-cycle example analysed only through MCP tool calls.

Reproduces pyKinGenie's notebook ``16_carterra_global_smax.ipynb``: 13
injections on one sensor, imported with an info sheet, fitted with a one-site
model and one global Smax. Data sources and license: data/carterra_single_cycle.
"""

import json
from pathlib import Path

import pytest
from mcp import Client

from mcp_pykingenie.mcp import mcp

DATA = Path(__file__).parent / "data" / "carterra_single_cycle"
CSV = str(DATA / "carterra_rows.csv")
INFO_SHEET = str(DATA / "Example Data Info Sheet - Carterra.xlsx")

# Values from the notebook (pyKinGenie 1.0.22).
NOTEBOOK_KD_UM = 0.022363
NOTEBOOK_KOFF = 8.5807e-5
NOTEBOOK_SMAX = 224.1835
NOTEBOOK_LOO = {"Kd [µM]": "2.36e-02 ± 2.62e-03", "k_off [1/s]": "9.32e-05 ± 1.01e-05"}


def value(result):
    """Return the Python value of an MCP tool result."""
    structured = result.structured_content
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    if structured is not None:
        return structured
    text = result.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


@pytest.mark.asyncio
async def test_carterra_single_cycle_global_smax_with_tools_only():
    async with Client(mcp) as client:

        async def call(name, args=None):
            result = await client.call_tool(name, args or {})
            assert not result.is_error, result.content
            return value(result)

        formats = await call("detect_data_format", {"paths": [CSV, INFO_SHEET]})
        assert [row["format"] for row in formats] == ["carterra_csv", "unknown"]

        sheet = await call("read_info_sheet", {"path": INFO_SHEET})
        included = [row for row in sheet if row["Included"]]
        assert [row["Position"] for row in included] == ["A1", "A5", "A9"]
        assert {(row["Baseline_s"], row["Association_s"], row["Dissociation_s"]) for row in included} == {
            (120.0, 300.0, 720.0)
        }

        message = await call("import_binding_data", {
            "paths": CSV, "exp_name": "carterra", "info_sheet": INFO_SHEET, "single_cycle": True,
        })
        assert "Experiment 'carterra' imported (carterra_csv)" in message
        assert "Step types: ASSOC x13, DISASSOC x13, BASELINE x1." in message
        assert "Association traces: 13." in message
        assert "without concentration" not in message

        assert Path((await call("plot_traces_with_all_steps")).split(": ", 1)[1].strip()).is_file()
        await call("align_association", {"experiment_id": "carterra"})

        # The info sheet selects its five included concentrations; fit all 13.
        table = await call("obtain_sample_info_table")
        concentrations = [row["[Analyte] (μM)"] for row in table]
        assert len(table) == 13
        assert concentrations[0] == pytest.approx(0.000244)
        assert concentrations[-1] == pytest.approx(1.0)
        assert {row["SampleID"] for row in table} == {"AE.A244"}
        assert sum(row["Select"] for row in table) == 5
        for row in table:
            row["Select"] = True
        assert "AE.A244" in await call("initiate_fitting_datasets", {"sample_info": table})

        await call("run_kinetics_fitting", {
            "fitting_model": "one_to_one", "fitting_region": "association_dissociation", "linked_smax": True,
        })
        [params] = await call("get_kinetics_fitting_results")
        assert params["Kd [µM]"] == pytest.approx(NOTEBOOK_KD_UM, rel=1e-3)
        assert params["k_off [1/s]"] == pytest.approx(NOTEBOOK_KOFF, rel=1e-3)
        assert params["Smax"] == pytest.approx(NOTEBOOK_SMAX, rel=1e-3)

        message = await call("calc_leave_one_out_errors")
        assert "Successful fits: AE.A244. Failed fits: none." in message
        [loo] = await call("get_leave_one_out_results")
        assert {key: loo[key] for key in NOTEBOOK_LOO} == NOTEBOOK_LOO

        for plot in ("plot_kinetic_traces", "plot_kinetics_residuals"):
            assert Path((await call(plot)).split(": ", 1)[1].strip()).is_file()
