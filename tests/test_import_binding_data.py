"""Tests for format detection, generic import and the fitting options of pykingenie 1.0.22."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from mcp.server.mcpserver.exceptions import ToolError

import mcp_pykingenie.tools._pykingenie as tools

TEST_DATA_DIR = Path(__file__).parent / "data"
KON, KOFF, RMAX = 1.0, 0.01, 10.0  # 1/(µM s), 1/s, RU -> Kd = 0.01 µM
CONCS = [0.005, 0.01, 0.02, 0.04, 0.08]  # µM
T_START, T_END, T_STOP = 10.0, 130.0, 330.0


def one_to_one(conc, t):
    """Simulated 1:1 sensorgram: baseline, association, dissociation."""
    kobs = KON * conc + KOFF
    req = RMAX * conc / (conc + KOFF / KON)
    assoc = req * (1 - np.exp(-kobs * (t - T_START)))
    end = req * (1 - np.exp(-kobs * (T_END - T_START)))
    disso = end * np.exp(-KOFF * (t - T_END))
    return np.where(t < T_START, 0.0, np.where(t < T_END, assoc, disso))


@pytest.fixture
def spr_text(tmp_path):
    t = np.arange(0, T_STOP, 0.5)
    columns = {}
    for cycle, conc in enumerate(CONCS, 1):
        columns[f"Cycle={cycle}_Fc=2-1_X"] = t
        columns[f"Cycle={cycle}_Fc=2-1_Y"] = one_to_one(conc, t)
    path = tmp_path / "spr_export.txt"
    pd.DataFrame(columns).to_csv(path, sep="\t", index=False)
    return path


@pytest.fixture
def carterra_csv(tmp_path):
    t = np.arange(0, T_STOP, 1.0)
    header = ["Label"] + [f"{axis}{i}" for i in range(1, len(t) + 1) for axis in "XY"]
    lines = [",".join(header)]
    for index, conc in enumerate(CONCS, 1):
        values = np.column_stack([t, one_to_one(conc, t)]).ravel()
        lines.append(",".join([f"[Ligand 1-CH1 Conc. {index}]"] + [f"{v:.6g}" for v in values]))
    path = tmp_path / "carterra.csv"
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture
def steps_and_traces(tmp_path):
    steps = tmp_path / "steps.tsv"
    steps.write_text(
        "Step Number\tStep Time\tStep Type Name\n"
        "1\t10\tBaseline\n2\t120\tAssociation\n3\t200\tDissociation\n"
        "4\t10\tBaseline\n5\t120\tAssociation\n6\t200\tDissociation\n"
    )
    t = np.arange(0, 2 * T_STOP, 1.0)
    first, second = t < T_STOP, t >= T_STOP
    signal = np.where(first, one_to_one(0.02, t), one_to_one(0.08, np.where(second, t - T_STOP, 0)))
    traces = tmp_path / "traces.csv"
    pd.DataFrame({"X Values": t, "A1": signal}).to_csv(traces, index=False)
    return steps, traces


def test_detect_data_format_lists_known_files_of_a_folder(tmp_path, spr_text, carterra_csv):
    (tmp_path / "notes.log").write_text("not data")
    records = tools.detect_data_format(str(tmp_path))
    assert {Path(r["file"]).name: r["format"] for r in records} == {
        "spr_export.txt": "spr_text",
        "carterra.csv": "carterra_csv",
    }
    # Single files keep their format, even when unknown.
    assert tools.detect_data_format(str(tmp_path / "notes.log"))[0]["format"] == "unknown"


def test_detect_data_format_recognises_bundled_formats():
    kinds = {r["format"] for r in tools.detect_data_format(str(TEST_DATA_DIR / "gator_minimal"))}
    assert {"gator_steps", "gator_settings", "gator_csv"} <= kinds
    csv = TEST_DATA_DIR / "single_cycle_kingenie.csv"
    assert tools.detect_data_format(str(csv))[0]["format"] == "kingenie_surface"


def test_import_binding_data_reads_octet_folder_without_extra_files():
    folder = Path(tools.EXAMPLE_DATA_DIR) / "test_bli_folder"
    message = tools.import_binding_data(str(folder), exp_name="octet")
    assert "Experiment 'octet' imported (octet_fmf, octet_frd)" in message
    assert tools.PY_KINETICS.experiment_names == ["octet"]


def test_import_binding_data_reads_gator_folder_and_names_it():
    message = tools.import_binding_data(str(TEST_DATA_DIR / "gator_minimal"))
    assert "imported" in message
    assert tools.PY_KINETICS.experiment_names == ["gator_minimal"]


def test_import_binding_data_rejects_spr_text_without_timing(spr_text):
    with pytest.raises(ToolError, match="spr_text"):
        tools.import_binding_data(str(spr_text))
    assert tools.PY_KINETICS.experiment_names == []


def test_import_binding_data_rejects_options_the_reader_does_not_take():
    folder = Path(tools.EXAMPLE_DATA_DIR) / "test_bli_folder"
    with pytest.raises(ToolError, match="takes no options"):
        tools.import_binding_data(str(folder), association_end=10)


def test_import_binding_data_reports_missing_paths():
    with pytest.raises(ToolError, match="not a file or folder"):
        tools.import_binding_data("does/not/exist")


def test_import_binding_data_warns_about_missing_concentrations(spr_text):
    message = tools.import_binding_data(str(spr_text), association_start=T_START, association_end=T_END)
    assert f"Association traces: {len(CONCS)}, {len(CONCS)} without concentration." in message
    assert "Warnings:" in message


@pytest.mark.asyncio
async def test_spr_text_import_fits_the_simulated_kd(spr_text):
    tools.import_binding_data(
        str(spr_text), exp_name="spr", association_start=T_START, association_end=T_END,
        concentrations=[c * 1000 for c in CONCS], concentration_unit="nM", sample_id="analyte",
    )
    tools.initiate_fitting_datasets(trim_time=1)
    assert tools.PY_KINETICS.fittings[tools.PY_KINETICS.fittings_names[0]].trim_time == 1
    await tools.run_kinetics_fitting(compute_k_obs=False)
    params = tools.get_kinetics_fitting_results()[0]
    kd = next(v for k, v in params.items() if k.startswith("Kd"))
    assert kd == pytest.approx(KOFF / KON, rel=0.05)


def test_carterra_dilution_series_sets_concentrations(carterra_csv):
    tools.import_binding_data(
        str(carterra_csv), association_start=T_START, association_end=T_END,
        top_concentration=CONCS[-1], dilution_factor=2, sample_id="analyte",
    )
    rows = tools.obtain_sample_info_table()
    concs = sorted(next(v for k, v in row.items() if "[Analyte]" in k) for row in rows)
    assert concs == pytest.approx(CONCS)


def test_steps_and_traces_import_takes_concentrations(steps_and_traces):
    steps, traces = steps_and_traces
    message = tools.import_binding_data([str(steps), str(traces)], concentrations=[0.02, 0.08])
    assert "Association traces: 2." in message


def test_info_sheet_supplies_timing_and_concentrations(tmp_path, spr_text):
    sheet = tmp_path / "info.csv"
    molar = " ".join(f"{c * 1e-6:g}" for c in CONCS)
    sheet.write_text(
        "Incl.,Analyte,Bsl Start,Baseline,Association,Dissociation,Asso. Skip,All Concentrations,Incl. Conc.\n"
        f"Y,mAb1,0,{T_START:g},{T_END - T_START:g},{T_STOP - T_END:g},2,{molar},All\n"
    )
    rows = tools.read_info_sheet(str(sheet))
    assert rows[0]["Analyte"] == "mAb1"
    assert rows[0]["Association_skip_s"] == 2

    message = tools.import_binding_data(str(spr_text), info_sheet=str(sheet), info_sheet_row=0)
    assert "without concentration" not in message
    ids = {row["SampleID"] for row in tools.obtain_sample_info_table()}
    assert ids == {"mAb1"}


def test_info_sheet_row_requires_info_sheet(spr_text):
    with pytest.raises(ToolError, match="requires info_sheet"):
        tools.import_binding_data(str(spr_text), info_sheet_row=0)


def test_initiate_fitting_datasets_rejects_negative_trim_time():
    with pytest.raises(ToolError, match="trim_time"):
        tools.initiate_fitting_datasets(trim_time=-1)


@pytest.mark.asyncio
async def test_bivalent_analyte_model_runs_on_octet_example():
    tools.load_octet_example()
    df = pd.DataFrame(tools.obtain_sample_info_table())
    df["Select"] = [True] * 4 + [False] * (len(df) - 4)
    tools.initiate_fitting_datasets(df.to_dict(orient="records"))
    message = await tools.run_kinetics_fitting(fitting_model="bivalent_analyte")
    assert "bivalent_analyte" in message
    params = tools.get_kinetics_fitting_results()
    assert params and any("k_a2" in key or "ka2" in key.lower() for key in params[0])


def _load_two_experiments():
    folder = str(Path(tools.EXAMPLE_DATA_DIR) / "test_bli_folder")
    tools.import_binding_data(folder, exp_name="first")
    tools.import_binding_data(folder, exp_name="second")


def test_delete_experiment_by_name_and_index():
    _load_two_experiments()
    message = tools.delete_experiment("2")
    assert "Deleted experiment(s): second." in message
    assert "Still loaded: first." in message
    message = tools.delete_experiment(["first"])
    assert "No experiments are loaded." in message
    assert tools.PY_KINETICS.experiment_names == []
    assert tools.PY_KINETICS.experiments == {}


@pytest.mark.parametrize("selector", ["missing", "0", "-1", "3"])
def test_delete_experiment_checks_every_selector_before_deleting(selector):
    _load_two_experiments()
    with pytest.raises(ToolError, match="not found"):
        tools.delete_experiment(["first", selector])
    assert tools.PY_KINETICS.experiment_names == ["first", "second"]


def test_delete_experiment_clears_fitting_datasets():
    _load_two_experiments()
    df = pd.DataFrame(tools.obtain_sample_info_table())
    df = df[df["Experiment"] == "first"]
    tools.initiate_fitting_datasets(df.to_dict(orient="records"))
    assert tools.PY_KINETICS.fittings_names
    message = tools.delete_experiment("first")
    assert "Fitting datasets were cleared" in message
    assert not tools.PY_KINETICS.fittings_names
    # The remaining experiment can be fitted again.
    assert "Fitting datasets generated" in tools.initiate_fitting_datasets()
