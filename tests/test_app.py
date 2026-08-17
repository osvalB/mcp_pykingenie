from importlib.metadata import version
import importlib
import json
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
from mcp import Client
from packaging.version import Version

import mcp_pykingenie
import mcp_pykingenie.server as server
import mcp_pykingenie.config as config
import mcp_pykingenie.tools._pykingenie as pykingenie_tools
from mcp_pykingenie.main import run_app
from mcp_pykingenie.mcp import mcp
import mcp_pykingenie.main as main_module
from mcp_pykingenie.paths import (
    RESULTS_DIR_ENV_VAR,
    USER_DATA_DIR_NAME,
    get_example_data_root,
    get_user_data_root,
)
from pykingenie.surface_exp import SurfaceBasedExperiment


MIN_PYKINGENIE_VERSION = Version("1.0.0")
TEST_DATA_DIR = Path(__file__).parent / "data"


def _load_example_and_selected_fitting():
    """Load bundled Octet data and prepare one real fitting dataset."""
    pykingenie_tools.load_octet_example()
    sample_info = pykingenie_tools.obtain_sample_info_table()
    df = pd.DataFrame(sample_info)
    df["Select"] = [True] * 8 + [False] * (len(df) - 8)
    pykingenie_tools.initiate_fitting_datasets(df.to_dict(orient="records"))
    return df


def _saved_path_from_message(message: str) -> Path:
    """Extract the generated artifact path from a tool result message."""
    return Path(message.split(": ", 1)[1].strip())


def _result_data(result):
    """Extract the Python value returned by an MCP v2 tool call."""
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured

    content = getattr(result, "content", None) or []
    if len(content) == 1 and hasattr(content[0], "text"):
        text = content[0].text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    return content


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


def test_documentation_example_bli_download_archive_contains_raw_data():
    """Testing docs expose a downloadable Octet BLI example archive."""
    archive_path = Path(__file__).parents[1] / "docs" / "_static" / "downloads" / "octet_bli_example_data.zip"

    assert archive_path.is_file()

    with zipfile.ZipFile(archive_path) as zip_file:
        names = set(zip_file.namelist())

    assert "test_bli_folder/230309_001.frd" in names
    assert "test_bli_folder/230309_Manifest.fmx" in names
    assert "test_bli_folder/230309_ExpMethod.fmf" in names


def test_server_instructions_show_current_data_folder():
    """Testing server instructions include the current output folder."""
    instructions = config.build_server_instructions(server.DATA_DIR)

    assert server.DATA_DIR in instructions
    assert "surface-based binding kinetics data only" in instructions
    assert "Plots and generated files for this session are saved in:" in instructions

def test_config_import_creates_results_directories(monkeypatch, tmp_path):
    """Testing config startup creates the base and dated results folders."""
    results_dir = tmp_path / "created-results"
    monkeypatch.setenv(RESULTS_DIR_ENV_VAR, str(results_dir))
    monkeypatch.delenv("MCP_PYKINGENIE_SKIP_USER_DATA_INIT", raising=False)

    reloaded_config = importlib.reload(config)

    assert results_dir.is_dir()
    assert Path(reloaded_config.DATA_DIR).is_dir()
    assert Path(reloaded_config.DATA_DIR).parent == results_dir

    # Restore config without creating the normal user-data directory.
    monkeypatch.setenv("MCP_PYKINGENIE_SKIP_USER_DATA_INIT", "1")
    monkeypatch.delenv(RESULTS_DIR_ENV_VAR, raising=False)
    importlib.reload(config)


def test_cli_prints_results_folder():
    """Testing CLI reports the active results folder at startup."""
    runner = CliRunner()
    calls = []

    fake_mcp = SimpleNamespace(
        run=lambda **kwargs: calls.append(kwargs)
    )

    with patch("mcp_pykingenie.mcp.mcp", fake_mcp):
        result = runner.invoke(run_app, [])

    assert result.exit_code == 0
    assert calls == [{"transport": "stdio"}]
    assert (
        f"mcp_pykingenie results folder: {server.DATA_DIR}"
        in result.stderr
    )


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
    """Testing folder listing raises a useful error for empty input."""
    with pytest.raises(
        FileNotFoundError,
        match="No folder provided. Please specify a folder.",
    ):
        pykingenie_tools.list_files_in_folder()


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


def test_import_gator_experiment_accepts_relative_zip_file():
    """Testing Gator import resolves relative zip files from the active data dir."""
    zip_stem = "gator_relative_zip_case"
    zip_name = f"{zip_stem}.zip"
    zip_path = Path(server.DATA_DIR) / zip_name

    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for source_file in (TEST_DATA_DIR / "gator_minimal").iterdir():
            zip_file.write(source_file, Path(zip_stem) / source_file.name)

    message = pykingenie_tools.import_gator_experiment(zip_name, "Gator Relative Zip Example")

    experiment = server.PY_KINETICS.experiments["Gator Relative Zip Example"]
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
    expected_reference = server.PY_KINETICS.experiments["Example Experiment"].sensor_names[0]

    association_message = pykingenie_tools.align_association(experiment_id="1")
    dissociation_message = pykingenie_tools.align_dissociation(experiment_id="1")
    subtraction_message = pykingenie_tools.subtract_reference(experiment_id="1", reference_sensor="1")

    assert "Association phase aligned for experiment: Example Experiment" in association_message
    assert "Dissociation phase aligned for experiment: Example Experiment" in dissociation_message
    assert f"Reference sensor '{expected_reference}' subtracted" in subtraction_message
    assert expected_reference in server.PY_KINETICS.experiments["Example Experiment"].sensor_names


def test_invalid_experiment_selectors_return_not_found_messages():
    """Testing invalid experiment selectors report the expected error text."""
    pykingenie_tools.load_octet_example()

    expected = "Experiment with index 99 not found in kingenie."

    assert pykingenie_tools.plot_sample_plate_info(experiment_id="99") == expected
    assert pykingenie_tools.align_association(experiment_id="99") == expected
    assert pykingenie_tools.subtract_reference(experiment_id="99") == expected
    assert pykingenie_tools.subtract_experiment(experiment_id="99", reference_experiment_id="1") == expected
    assert pykingenie_tools.subtract_experiment(experiment_id="1", reference_experiment_id="99") == expected
    assert pykingenie_tools.subtract_sensor_columns(experiment_id="99") == expected
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
    loaded_sensor_names = server.PY_KINETICS.experiments["Example Experiment"].sensor_names

    assert sensor_names == [loaded_sensor_names]
    assert attributes["sensor_names"] == loaded_sensor_names
    assert set(loaded_sensor_names) == {"A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"}
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


def test_subtract_experiment_runs_real_surface_experiment_subtraction():
    """Testing experiment subtraction uses PyKinGenie's real Octet traces."""
    pykingenie_tools.load_octet_example()
    pykingenie_tools.import_octet_experiment(
        str(get_example_data_root() / "test_bli_folder"),
        "Reference Experiment",
    )

    message = pykingenie_tools.subtract_experiment(
        experiment_id="Example Experiment",
        reference_experiment_id="Reference Experiment",
    )

    experiment = server.PY_KINETICS.experiments["Example Experiment"]
    assert "Experiment 'Reference Experiment' subtracted" in message
    assert "A1 - A1" in experiment.sensor_names
    np.testing.assert_allclose(experiment.ys[experiment.sensor_names.index("A1 - A1")][0], 0, atol=1e-12)


def test_subtract_sensor_columns_runs_real_surface_column_subtraction():
    """Testing column subtraction calls PyKinGenie's surface experiment method."""
    experiment = SurfaceBasedExperiment("Column Experiment", "synthetic_surface")
    experiment.sensor_names = ["A1", "A2", "B1", "B2"]
    experiment.xs = [[np.array([0.0, 1.0])]] * 4
    experiment.ys = [
        [np.array([1.0, 2.0])],
        [np.array([0.25, 0.75])],
        [np.array([3.0, 5.0])],
        [np.array([1.0, 1.5])],
    ]
    experiment.ligand_conc_df = pd.DataFrame(
        {
            "Sensor": experiment.sensor_names,
            "SampleID": ["Sample A", "Sample A", "Sample B", "Sample B"],
        }
    )
    experiment.traces_loaded = True
    experiment.create_unique_sensor_names()
    server.PY_KINETICS.add_experiment(experiment, "Column Experiment")

    message = pykingenie_tools.subtract_sensor_columns(
        experiment_id="Column Experiment",
        sensors_column_one=1,
        sensors_column_two=2,
    )

    assert "Subtracted A2 from A1" in message
    assert "Subtracted B2 from B1" in message
    assert experiment.sensor_names == ["A1 - A2", "A2", "B1 - B2", "B2"]
    np.testing.assert_allclose(experiment.ys[0][0], [0.75, 1.25])
    np.testing.assert_allclose(experiment.ys[2][0], [2.0, 3.5])


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
async def test_split_fitting_tools_support_real_two_to_one_model():
    """Testing split fitting tools support PyKinGenie's real two-to-one model."""
    _load_example_and_selected_fitting()

    steady_state_message = await pykingenie_tools.run_steady_state_fitting(
        steady_state_model="two_to_one",
        fit_sigma=False,
    )
    assert (
        "Steady-state fitting submitted with model: two_to_one, "
        "fit sigma: False."
    ) == steady_state_message

    _load_example_and_selected_fitting()
    kinetics_message = await pykingenie_tools.run_kinetics_fitting(
        fitting_model="two_to_one",
        fit_sigma=False,
    )

    assert (
        "Kinetics fitting submitted with model: two_to_one, "
        "region: association_dissociation, linked Smax: False, "
        "fit sigma: False."
    ) == kinetics_message


@pytest.mark.asyncio
async def test_create_export_df_returns_real_raw_and_fitted_traces():
    """Testing export DataFrame returns real raw and fitted surface traces."""
    _load_example_and_selected_fitting()

    raw_records = pykingenie_tools.create_export_df()
    raw_df = pd.DataFrame(raw_records)

    await pykingenie_tools.run_kinetics_fitting()
    fitted_records = pykingenie_tools.create_export_df(export_type="fitted")
    fitted_df = pd.DataFrame(fitted_records)

    expected_columns = {
        "Time",
        "Signal",
        "Analyte_concentration_micromolar",
        "Type",
        "ID",
    }
    assert set(raw_df.columns) == expected_columns
    assert set(fitted_df.columns) == expected_columns
    assert {"Association", "Dissociation"} <= set(raw_df["Type"])
    assert {"Association", "Dissociation"} <= set(fitted_df["Type"])
    assert len(raw_df) > 0
    assert len(fitted_df) > 0

    with pytest.raises(ValueError, match="export_type"):
        pykingenie_tools.create_export_df(export_type="unknown")


def test_fitting_result_tools_report_empty_states_clearly():
    """Testing result/export tools reject missing fitting state with clear errors."""
    with pytest.raises(RuntimeError, match="No fitting datasets are available"):
        pykingenie_tools.get_kinetics_fitting_results()

    with pytest.raises(RuntimeError, match="No fitting datasets are available"):
        pykingenie_tools.create_export_df()

    _load_example_and_selected_fitting()

    with pytest.raises(RuntimeError, match="No kinetic fitting results are available"):
        pykingenie_tools.get_kinetics_fitting_results()

    with pytest.raises(RuntimeError, match="No fitted kinetic traces are available"):
        pykingenie_tools.create_export_df(export_type="fitted")


@pytest.mark.asyncio
async def test_run_steady_state_fitting_rejects_unsupported_real_model():
    """Testing steady-state fitting rejects PyKinGenie unsupported models."""
    with pytest.raises(ValueError, match="Unknown steady-state fitting model"):
        await pykingenie_tools.run_steady_state_fitting(steady_state_model="one_to_one_mtl")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        (
            {"fitting_model": "unknown"},
            "Unknown kinetic fitting model",
        ),
        (
            {
                "fitting_model": "one_to_one_mtl",
                "fitting_region": "association",
            },
            "does not support region",
        ),
        (
            {
                "fitting_model": "one_to_one_if",
                "fitting_region": "dissociation",
            },
            "does not support region",
        ),
        (
            {
                "fitting_model": "two_to_one",
                "fitting_region": "association",
            },
            "does not support region",
        ),
    ],
)
async def test_run_kinetics_fitting_rejects_unsupported_real_model_region_combinations(
    kwargs,
    match,
):
    """Testing kinetic fitting rejects PyKinGenie unsupported fitting selections."""
    with pytest.raises(ValueError, match=match):
        await pykingenie_tools.run_kinetics_fitting(**kwargs)


@pytest.mark.asyncio
async def test_mcp_server():
    """Testing MCP server."""
    async with Client(mcp) as client:
        result = await client.call_tool("print_data_dir", {})
        assert _result_data(result) == server.DATA_DIR

        result = await client.call_tool("load_octet_example", {})
        assert "Octet experiment added from" in _result_data(result)

        result = await client.call_tool("get_legends_table", {})
        legends = _result_data(result)
        df = pd.DataFrame(legends)

        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"Internal_ID", "Color", "Legend", "Show"}
        assert set(df["Legend"]) == {"A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"}

        result = await client.call_tool(
            "plot_traces_with_all_steps",
            {"legends_df": legends},
        )

        assert "Plot saved to" in _result_data(result)

        result = await client.call_tool("list_experiment_names", {})

        assert _result_data(result) == ["Example Experiment"]

        result = await client.call_tool("align_association", {"experiment_id": "Example Experiment"})

        assert "Association phase aligned for experiment" in _result_data(result)

        result = await client.call_tool("align_dissociation", {"experiment_id": "Example Experiment"})

        assert "Dissociation phase aligned for experiment" in _result_data(result)

        result = await client.call_tool("subtract_reference", {"reference_sensor": "H1"})

        assert "Reference sensor" in _result_data(result)

        result = await client.call_tool("obtain_sample_info_table", {})

        sample_info = _result_data(result)
        df = pd.DataFrame(sample_info)

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

        sample_info_new = df.to_dict(orient="records")

        result = await client.call_tool(
            "initiate_fitting_datasets",
            {"sample_info": sample_info_new},
        )

        assert "Fitting datasets generated" in _result_data(result)

        result = await client.call_tool("plot_steady_state", {})

        assert "Plot saved to" in _result_data(result)

        result = await client.call_tool("plot_kinetic_traces", {})

        assert "Plot saved to" in _result_data(result)

        result = await client.call_tool("run_steady_state_fitting", {})
        assert (
            "Steady-state fitting submitted with model: one_to_one, "
            "fit sigma: False."
        ) == _result_data(result)

        result = await client.call_tool("run_kinetics_fitting", {})
        assert (
            "Kinetics fitting submitted with model: one_to_one, "
            "region: association_dissociation, linked Smax: False, "
            "fit sigma: False."
        ) == _result_data(result)

        result = await client.call_tool("get_kinetics_fitting_results", {})

        results = _result_data(result)
        df = pd.DataFrame(results)
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

        result = await client.call_tool("create_export_df", {"export_type": "fitted"})
        export_df = pd.DataFrame(_result_data(result))
        assert set(export_df.columns) == {
            "Time",
            "Signal",
            "Analyte_concentration_micromolar",
            "Type",
            "ID",
        }
        assert len(export_df) > 0
