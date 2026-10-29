from mcp_pykingenie.mcp import mcp

import os
import json
import math
import pandas as pd
import numpy as np

from ..server import PY_KINETICS, DATA_DIR, EXAMPLE_DATA_DIR

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

import pykingenie


STEADY_STATE_FITTING_MODELS = {"one_to_one", "two_to_one"}

KINETIC_FITTING_MODEL_REGIONS = {
    "one_to_one": {
        "association_dissociation",
        "association",
        "dissociation",
    },
    "one_to_one_mtl": {"association_dissociation"},
    "one_to_one_if": {"association_dissociation"},
    "two_to_one": {"association_dissociation"},
}

# Every PyKinGenie fit clears all results of a fitting object, so the results
# of the other fit type are saved and restored around each fit.
FIT_RESULT_FIELDS = {
    "kinetics": ("fit_params_kinetics", "fit_params_kinetics_error",
                 "signal_assoc_fit", "signal_disso_fit", "k_obs"),
    "steady_state": ("fit_params_ss", "signal_ss_fit"),
}


def resolve_experiment_name(experiment_id: str) -> str | None:
    """
    Resolve a PyKinGenie experiment name from a name or 1-based index.

    Parameters
    ----------
    experiment_id : str
        Experiment name or 1-based index in ``PY_KINETICS.experiment_names``.

    Returns
    -------
    str or None
        The resolved experiment name, or None when the selector is invalid.
    """
    if experiment_id in PY_KINETICS.experiment_names:
        return experiment_id

    try:
        return PY_KINETICS.experiment_names[int(experiment_id) - 1]
    except (ValueError, IndexError):
        return None


@contextmanager
def keep_fit_results(family: str):
    """
    Restore one fit type's results after running a fit of the other type.

    Parameters
    ----------
    family : str
        Results to keep, ``'kinetics'`` or ``'steady_state'``.
    """
    fields = FIT_RESULT_FIELDS[family]
    snapshots = [
        (name, fitting, {field: deepcopy(getattr(fitting, field)) for field in fields
                         if getattr(fitting, field, None) is not None})
        for name, fitting in PY_KINETICS.fittings.items()
    ]
    try:
        yield
    finally:
        for name, fitting, values in snapshots:
            # Skip fitting objects replaced while the fit was running.
            if PY_KINETICS.fittings.get(name) is fitting:
                for field, value in values.items():
                    setattr(fitting, field, value)


def select_sample_rows(sample_info: list[Any]) -> list[dict[str, Any]]:
    """
    Check sample metadata and return the selected rows with an experiment each.

    Rows that are not selected or have a zero analyte concentration (reference
    traces) are left out. Each remaining row is matched to the one loaded
    experiment that has its association and dissociation data, so the
    ``Experiment`` column is filled in when it is missing.

    Parameters
    ----------
    sample_info : list
        Records from ``obtain_sample_info_table``, possibly edited.

    Returns
    -------
    list of dict
        Selected rows, each with an ``Experiment`` value.

    Raises
    ------
    ValueError
        If a row is invalid, matches no or several experiments, or no row is
        selected.
    """
    if not isinstance(sample_info, list) or not sample_info:
        raise ValueError("Provide sample metadata with at least one selected, positive-concentration trace.")

    selected = []
    for index, original in enumerate(sample_info, 1):
        prefix = f"Sample row {index}"
        if not isinstance(original, dict) or type(original.get("Select")) is not bool:
            raise ValueError(f"{prefix}: Select must be true or false.")
        if not original["Select"]:
            continue

        row = original.copy()
        concentration_keys = [key for key in row if "[Analyte]" in key]
        concentration = row[concentration_keys[0]] if len(concentration_keys) == 1 else None
        if type(concentration) not in (int, float) or not math.isfinite(concentration) or concentration < 0:
            raise ValueError(f"{prefix}: provide one finite, nonnegative analyte concentration in μM.")
        # PyKinGenie leaves zero-concentration references out of the fit.
        if concentration == 0:
            continue

        for key in ("Sensor", "SampleID"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{prefix}: {key} must not be empty.")

        # merge_ligand_conc_df drops columns with a single value, so missing
        # columns take their default unless another row has them.
        for key, minimum, default in (("Smax_ID", 0, None), ("Replicate", 1, 1),
                                      ("Analyte_location", 0, 0), ("Loading_location", 0, 0)):
            if key not in row and default is not None:
                if any(isinstance(other, dict) and key in other for other in sample_info):
                    raise ValueError(f"{prefix}: {key} is missing from this row.")
                row[key] = default
            if type(row.get(key)) is not int or row[key] < minimum:
                raise ValueError(f"{prefix}: {key} must be an integer of at least {minimum}.")

        names = PY_KINETICS.experiment_names
        if "Experiment" in row:
            if row["Experiment"] not in names:
                raise ValueError(f"{prefix}: experiment {row['Experiment']!r} is not loaded.")
            names = [row["Experiment"]]

        candidates = []
        for name in names:
            experiment = PY_KINETICS.experiments[name]
            try:
                available = all(len(experiment.get_step_xy(
                    row["Sensor"], row["Loading_location"], row["Analyte_location"],
                    step_type=phase, replicate=row["Replicate"], type=axis,
                )) for phase in ("ASSOC", "DISASSOC") for axis in ("x", "y"))
            except (ValueError, IndexError, KeyError, TypeError):
                available = False
            if available:
                candidates.append(name)

        if not candidates:
            raise ValueError(f"{prefix}: no loaded experiment contains sensor {row['Sensor']!r}, analyte location "
                             f"{row['Analyte_location']}, loading location {row['Loading_location']}, replicate "
                             f"{row['Replicate']} with association and dissociation data.")
        if len(candidates) > 1:
            raise ValueError(f"{prefix}: the trace matches several experiments ({', '.join(candidates)}). "
                             "Set Experiment in the sample metadata.")
        row["Experiment"] = candidates[0]
        selected.append(row)

    if not selected:
        raise ValueError("Select at least one trace with a positive analyte concentration.")
    return selected


def current_hour_min_sec():
    """
    Get the current time in HH-MM-SS format.

    Returns
    -------
    str
        Current time as a string.
    """
    now = datetime.now()
    return now.strftime('%H-%M-%S')


# To be called by mcp tools import_octet_experiment and load_octet_example
def import_octet_experiment_base(folder: str = '.', exp_name: str = 'Experiment') -> str:
    """
    Import Octet BLI data into the shared PyKinGenie analyzer.

    The folder is read with :class:`pykingenie.OctetExperiment`. PyKinGenie
    parses the ``.frd`` sensor traces and sample plate metadata, then the
    resulting experiment is registered in ``PY_KINETICS``.

    Parameters
    ----------
    folder : str
        Absolute path or ``DATA_DIR``-relative folder containing Octet files.
    exp_name : str
        Name used when storing the experiment in the analyzer.

    Returns
    -------
    str
        Confirmation message naming the imported folder.
    """

    # Find if full path is provided or just the folder name
    if os.path.isabs(folder):
        folder_path = folder
    else:
        folder_path = os.path.join(DATA_DIR, folder)

    octet = pykingenie.OctetExperiment()

    files = sorted(os.listdir(folder_path))
    files = [os.path.join(folder_path, f) for f in files]

    octet.read_sensor_data(files)
    octet.read_sample_plate_info(files)

    PY_KINETICS.add_experiment(octet, exp_name)

    return f"Octet experiment added from {folder}."


@mcp.tool()
def print_data_dir() -> str:
    """
    Print the path to the data directory, where the generated files will be stored.

    Returns
    -------
    str
        The path to the data directory.
    """
    return f"{DATA_DIR}"


@mcp.tool()
def list_files_in_folder(folder: str = '') -> list[str]:
    """
    List all files in the selected folder.

    Parameters
    ----------
    folder : str
        The folder to list files from.

    Returns
    -------
    list
        A list of file names in the data directory.
    """

    if not folder:
        raise FileNotFoundError("No folder provided. Please specify a folder.")

    try:
        files = os.listdir(folder)
    except OSError as exc:
        raise FileNotFoundError(
            f"The folder '{folder}' does not exist or is not accessible."
        ) from exc

    return [x for x in files if os.path.isfile(os.path.join(folder, x))]


@mcp.tool()
def import_kingenie_surface_csv(csv: str, exp_name: str = 'Experiment') -> str:
    """
    Import a KinGenie surface-simulation CSV into the analyzer.

    The CSV is parsed with :class:`pykingenie.KinGenieCsv`. It should contain
    exported surface-simulation columns such as ``Time``, ``Signal``, ``Smax``,
    and ``Analyte_concentration_micromolar_constant``; a ``Cycle`` column is
    supported for single-cycle data. If ``exp_name`` already exists, a numeric
    suffix is appended before storing the experiment in ``PY_KINETICS``.

    Parameters
    ----------
    csv : str
        Absolute path or ``DATA_DIR``-relative path to the simulation CSV file.
    exp_name : str
        Requested experiment name in the analyzer.

    Returns
    -------
    str
        Confirmation message naming the imported CSV path.
    """
    exp = pykingenie.KinGenieCsv()

    # Find if full path is provided or just the file name
    if os.path.isabs(csv):
        csv_path = csv
    else:
        # If not absolute, assume it's in the DATA_DIR
        csv_path = os.path.join(DATA_DIR, csv)

    exp.read_csv(csv_path)

    if exp_name in PY_KINETICS.experiment_names:
        exp_name = exp_name + str(len(PY_KINETICS.experiment_names))

    PY_KINETICS.add_experiment(exp, exp_name)

    return f"Experiment added from {csv}."


@mcp.tool()
def import_octet_experiment(folder: str = '.', exp_name: str = 'Experiment') -> str:
    """
    Import an Octet experiment folder into the shared PyKinGenie analyzer.

    This wraps :class:`pykingenie.OctetExperiment`, loading sensor traces and
    sample plate metadata before adding the experiment to ``PY_KINETICS``.

    Parameters
    ----------
    folder : str
        Absolute path or ``DATA_DIR``-relative folder containing Octet files.
    exp_name : str
        Name used when storing the experiment in the analyzer.

    Returns
    -------
    str
        Confirmation message naming the imported folder.
    """

    return import_octet_experiment_base(folder, exp_name)


@mcp.tool()
def import_gator_experiment(folder: str = '.', exp_name: str = 'Experiment') -> str:
    """
    Import Gator BLI data into the shared PyKinGenie analyzer.

    Folder contents are parsed with :class:`pykingenie.GatorExperiment`, which
    reads experiment steps, settings, and sensor-channel CSV traces. If a zip
    file is provided, it is extracted under ``DATA_DIR`` and then read as a
    folder.

    Parameters
    ----------
    folder : str
        Absolute path or ``DATA_DIR``-relative folder or zip file containing
        ``Assay_#_Channel#.csv`` files plus ``Setting.ini`` and
        ``ExperimentStep.ini``.
    exp_name : str
        Name used when storing the experiment in the analyzer.

    Returns
    -------
    str
        Confirmation message naming the imported folder or zip stem.
    """

    # Find if full path is provided or just the folder name
    if os.path.isabs(folder):
        folder_path = folder
    else:
        folder_path = os.path.join(DATA_DIR, folder)

    # Check if we have a zip file or a folder, if we have a zip, extract it to a folder
    if folder_path.endswith('.zip'):
        import zipfile
        with zipfile.ZipFile(folder_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)  # Extract to the data directory
            # Obtain the name of the zip file without the .zip extension
            # and use it as the folder name
            folder = os.path.splitext(os.path.basename(folder))[0]
            # Update the folder path to the extracted folder
            folder_path = os.path.join(DATA_DIR, folder)

    gator = pykingenie.GatorExperiment()

    files = sorted(os.listdir(folder_path))
    files = [os.path.join(folder_path, f) for f in files]

    gator.read_all_gator_data(files)

    PY_KINETICS.add_experiment(gator, exp_name)

    return f"Gator experiment added from {folder}."


@mcp.tool()
def load_octet_example() -> str:
    """
    Load the packaged Octet example into the shared analyzer.

    The bundled BLI example is imported through the same
    :class:`pykingenie.OctetExperiment` path as ``import_octet_experiment`` and
    stored as ``"Example Experiment"``.

    Returns
    -------
    str
        Confirmation message naming the packaged example folder.
    """
    example_folder_path = os.path.join(EXAMPLE_DATA_DIR, 'test_bli_folder')

    return import_octet_experiment_base(folder=example_folder_path, exp_name='Example Experiment')


@mcp.tool()
def get_legends_table() -> list[dict[str, Any]]:
    """
    Build a plotting legend table from PyKinGenie sensor metadata.

    Sensor names and unique sensor IDs are collected with
    ``PY_KINETICS.get_experiment_properties`` and converted with
    :func:`pykingenie.get_plotting_df`.

    Returns
    -------
    str
        JSON records for a DataFrame with ``Internal_ID``, ``Color``,
        ``Legend``, and ``Show`` columns.
    """

    labels = PY_KINETICS.get_experiment_properties('sensor_names')
    ids = PY_KINETICS.get_experiment_properties('sensor_names_unique')

    # Flatten the lists
    labels = [item for sublist in labels for item in sublist]
    ids = [item for sublist in ids for item in sublist]

    df = pykingenie.get_plotting_df(ids, labels)
    return df.to_dict(orient="records")


@mcp.tool()
def list_experiment_names() -> list[str]:
    """
    Get the names of all experiments in the pykinetics analyzer.

    Returns
    -------
    list
        A list of experiment names.
    """
    return PY_KINETICS.experiment_names


@mcp.tool()
def align_association(experiment_id: str = '1',
                      sensor_names: list[str] | None = None,
                      in_place: bool = True,
                      new_names: bool = False) -> str:
    """
    Align association phases for selected sensors in a PyKinGenie experiment.

    This calls ``SurfaceBasedExperiment.align_association``. PyKinGenie
    subtracts the signal before association from the selected traces and updates
    trace arrays, sensor names, and ligand metadata according to ``in_place`` and
    ``new_names``.

    Parameters
    ----------
    experiment_id : str
        The name of the experiment to align. If a number is provided, it will be
        used to select the experiment by its index.
    sensor_names : list
        Sensor names to align. If empty, all sensors in the experiment are used.
    in_place : bool
        If True, modifies the existing sensors; if False, creates new sensors.
    new_names : bool
        If True, uses new names for the aligned sensors.

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment
    if not sensor_names:
        sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    PY_KINETICS.experiments[experiment_name].align_association(sensor_names, in_place, new_names)

    # Print the message with the experiment and sensor names
    return f"Association phase aligned for experiment: {experiment_name} with sensors: {', '.join(sensor_names)}."


@mcp.tool()
def subtract_reference(experiment_id: str = '1', list_of_sensor_names: list[str] | None = None,
                       reference_sensor: str = '1', inplace: bool = True) -> str:
    """
    Subtract a reference sensor from selected PyKinGenie sensor traces.

    This calls ``SurfaceBasedExperiment.subtraction`` and updates trace arrays,
    sensor names, and ligand metadata. The reference sensor may be named
    directly or selected by 1-based sensor index.

    Parameters
    ----------
    experiment_id : str
        The name of the experiment to subtract the reference from.
        If a number is provided, it will be used to select the experiment by its index.
    list_of_sensor_names : list
        A list of sensor names to subtract the reference from.
        If no names are provided, all sensors except the reference will be used.
    reference_sensor : str
        The name of the reference sensor to subtract.
        If a number is provided, it will be used to select the sensor by its index.
    inplace : bool
        If True, modifies the existing sensors; if False, creates new sensors.

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment, different from the reference sensor
    sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    # If the reference sensor is not in the list of sensor names, try to select it by index
    if reference_sensor not in sensor_names:
        try:
            reference_sensor = sensor_names[int(reference_sensor) - 1]
        except (ValueError, IndexError):
            return f"Reference sensor '{reference_sensor}' not found in the list of sensors for experiment '{experiment_name}'."

    if not list_of_sensor_names:
        list_of_sensor_names = [s for s in sensor_names if s != reference_sensor]

    PY_KINETICS.experiments[experiment_name].subtraction(list_of_sensor_names, reference_sensor, inplace)

    # Obtain the new names of the sensors after subtraction
    new_sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    return (f"Reference sensor '{reference_sensor}' subtracted from sensors: {list_of_sensor_names}. "
            f"New sensor names: {new_sensor_names}.")


@mcp.tool()
def average_sensors(
    experiment_id: str = '1',
    list_of_sensor_names: list[str] | None = None,
    sensor_output_name: str = 'average') -> str:

    """
    Average signal values of selected sensors from a specific experiment

    Parameters
    ----------
    experiment_id : str
        Name or 1-based index of the experiment to modify. 
    list_of_sensor_names : list
        A list of sensor names to subtract the reference from.
        If no names are provided, all sensors will be used.
    sensor_output_name : str
        Name of the new sensor that contains the averaged traces 

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment, different from the reference sensor
    sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    if not list_of_sensor_names:
        list_of_sensor_names = [s for s in sensor_names ]

    PY_KINETICS.experiments[experiment_name].average(list_of_sensor_names, sensor_output_name)

    return (
        f"Successfully averaged {len(list_of_sensor_names)} sensors "
        f"({', '.join(list_of_sensor_names)}) "
        f"into the new sensor '{sensor_output_name}'."
    )

@mcp.tool()
def delete_sensors(
    experiment_id: str = "1",
    list_of_sensor_names: list[str] | None = None) -> str:

    """
    Delete sensor traces from a given experiment.

    Parameters
    ----------
    experiment_id : str
        Name or 1-based index of the experiment to modify.
    list_of_sensor_names : list[str] | None
        Names of sensors to delete.
        If None, all sensors will be deleted.

    Returns
    -------
    str
        Message describing the result.
    """

    # Resolve experiment name
    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            index = int(experiment_id) - 1
            if index < 0:
                raise IndexError
            experiment_name = PY_KINETICS.experiment_names[index]
        except (ValueError, IndexError):
            return f"Experiment '{experiment_id}' not found in KinGenie."
    else:
        experiment_name = experiment_id

    experiment = PY_KINETICS.experiments[experiment_name]
    sensor_names = experiment.sensor_names

    # Default to all sensors
    if list_of_sensor_names is None:
        list_of_sensor_names = list(sensor_names)

    # Validate sensor names
    invalid_sensors = [
        s for s in list_of_sensor_names if s not in sensor_names
    ]

    if invalid_sensors:
        return (
            f"Sensors {invalid_sensors} not found in experiment "
            f"'{experiment_name}'. Available sensors: {list(sensor_names)}."
        )

    # Find indices and sort descending
    indexes = sorted(
        [
            i for i, name in enumerate(sensor_names)
            if name in list_of_sensor_names
        ],
        reverse=True,
    )

    # Delete corresponding traces
    for i in indexes:
        experiment.xs.pop(i)
        experiment.ys.pop(i)

    # Update sensor names once
    experiment.sensor_names = [s for i,s in enumerate(sensor_names) if i not in indexes]

    return (
        f"Successfully deleted {len(indexes)} sensor(s) "
        f"({', '.join(list_of_sensor_names)}) "
        f"from experiment '{experiment_name}'."
    )

@mcp.tool()
def subtract_experiment(experiment_id: str = '1',
                        reference_experiment_id: str = '2',
                        inplace: bool = True) -> str:
    """
    Subtract one surface-based experiment from another sensor by sensor.

    This calls ``SurfaceBasedExperiment.subtract_experiment`` on the selected
    target experiment. PyKinGenie sorts sensor names alphanumerically and
    subtracts each matching sensor trace from the reference experiment. Both
    experiments must have the same number of sensors and compatible time data.

    Parameters
    ----------
    experiment_id : str
        Name or 1-based index of the experiment to modify.
    reference_experiment_id : str
        Name or 1-based index of the experiment to subtract from
        ``experiment_id``.
    inplace : bool
        If True, modifies the target experiment; if False, creates new sensors.
    only_interaction : bool
        If True, only subtracts the interaction terms (baseline before association, assoc. & dissociation phases) between sensors.

    Returns
    -------
    str
        A confirmation message with the updated target sensor names.
    """
    experiment_name = resolve_experiment_name(experiment_id)
    if experiment_name is None:
        return f"Experiment with index {experiment_id} not found in kingenie."

    reference_experiment_name = resolve_experiment_name(reference_experiment_id)
    if reference_experiment_name is None:
        return f"Experiment with index {reference_experiment_id} not found in kingenie."

    target_experiment = PY_KINETICS.experiments[experiment_name]
    reference_experiment = PY_KINETICS.experiments[reference_experiment_name]

    # Find experiment compatibility 
    compatible, compatibility_type = target_experiment.find_experiments_compatibility(reference_experiment)

    if not compatible:
        raise ValueError(
            f"Experiments '{experiment_name}' and '{reference_experiment_name}' are not compatible: {compatibility_type}"
        )

    only_interaction = compatibility_type == "interaction"

    target_experiment.subtract_experiment(reference_experiment, inplace=inplace, only_interaction = only_interaction)

    return (
        f"Experiment '{reference_experiment_name}' subtracted from experiment "
        f"'{experiment_name}'. New sensor names: {target_experiment.sensor_names}."
    )


@mcp.tool()
def subtract_sensor_columns(experiment_id: str = '1',
                            sensors_column_one: int = 1,
                            sensors_column_two: int = 2,
                            inplace: bool = True) -> str:
    """
    Subtract one column of sensors from another in a surface experiment.

    This calls ``SurfaceBasedExperiment.subtraction_by_column``. PyKinGenie
    finds sensor names containing ``sensors_column_one`` and subtracts the
    corresponding sensor obtained by replacing that column number with
    ``sensors_column_two``.

    Parameters
    ----------
    experiment_id : str
        Name or 1-based index of the experiment to modify.
    sensors_column_one : int
        Column number of the sensors to subtract from.
    sensors_column_two : int
        Column number of the reference sensors to subtract.
    inplace : bool
        If True, modifies the target sensors; if False, creates new sensors.

    Returns
    -------
    str
        A confirmation message listing PyKinGenie's subtraction messages and
        updated sensor names.
    """
    experiment_name = resolve_experiment_name(experiment_id)
    if experiment_name is None:
        return f"Experiment with index {experiment_id} not found in kingenie."

    experiment = PY_KINETICS.experiments[experiment_name]
    subtraction_messages = experiment.subtraction_by_column(
        sensors_column_one,
        sensors_column_two,
        inplace=inplace,
    )

    return (
        f"Sensor column {sensors_column_two} subtracted from column "
        f"{sensors_column_one} for experiment '{experiment_name}'. "
        f"Operations: {subtraction_messages}. "
        f"New sensor names: {experiment.sensor_names}."
    )

@mcp.tool()
def inter_step_correction(experiment_id: str = '1',
                        sensor_names: list[str] | None = None,
                        in_place: bool = True,
                        new_names: bool = False,
                        npoints: int = 2) -> str:
    """
    Perform the inter-step correction by shifting the association phase in a PyKinGenie experiment.
    This process step assumes that the baseline and dissociation phases were carried out in the same well.

    Note: in the Octet software, this is called "Inter-Step Correction" with the option "Align data to Dissociation Step"

    This calls ``SurfaceBasedExperiment.assoc_inter_step_correction``. PyKinGenie 
    moves the association traces to match the beginning of the dissociation phase.

    Parameters
    ----------
    experiment_id : str
        The name of the experiment to align. If a number is provided, it will be
        used to select the experiment by its index.
    sensor_names : list
        A list of sensor names to align. If no names are provided, all sensors in
        the experiment will be used.
    in_place : bool
        If True, modifies the existing sensors; if False, creates new sensors.
    new_names : bool
        If True, uses new names for the aligned sensors.
    npoints : int
        Number of points PyKinGenie uses around alignment positions.

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment
    if not sensor_names:
        sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    PY_KINETICS.experiments[experiment_name].assoc_inter_step_correction(sensor_names, in_place, new_names, npoints)

    # Print the message with the experiment and sensor names
    return f"Inter-step correction (shift association) done for experiment: {experiment_name} with sensors: {', '.join(sensor_names)}."

@mcp.tool()
def align_dissociation(experiment_id: str = '1',
                       sensor_names: list[str] | None = None,
                       in_place: bool = True,
                       new_names: bool = False,
                       npoints: int = 2) -> str:
    """
    Align dissociation phases for selected sensors in a PyKinGenie experiment.

    This calls ``SurfaceBasedExperiment.align_dissociation``. PyKinGenie shifts the 
    dissociation traces to match the end of the association phase.

    Parameters
    ----------
    experiment_id : str
        The name of the experiment to align. If a number is provided, it will be
        used to select the experiment by its index.
    sensor_names : list
        A list of sensor names to align. If no names are provided, all sensors in
        the experiment will be used.
    in_place : bool
        If True, modifies the existing sensors; if False, creates new sensors.
    new_names : bool
        If True, uses new names for the aligned sensors.
    npoints : int
        Number of points PyKinGenie uses around alignment positions.

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment
    if not sensor_names:
        sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    PY_KINETICS.experiments[experiment_name].align_dissociation(sensor_names, in_place, new_names, npoints)

    # Print the message with the experiment and sensor names
    return f"Dissociation phase aligned for experiment: {experiment_name} with sensors: {', '.join(sensor_names)}."


@mcp.tool()
def align_and_subtract(experiment_id: str = '1',
                       reference_sensor: str = '1',
                       align_dissociation: bool = False) -> str:
    """
    Align traces and subtract a reference sensor in one PyKinGenie workflow.

    The selected experiment is association-aligned in place, optionally
    dissociation-aligned in place, and then all non-reference sensors are
    reference-subtracted in place.

    Parameters
    ----------
    experiment_id : str
        The name of the experiment. If a number is provided, it will be used to
        select the experiment by its index.
    reference_sensor : str
        The name of the reference sensor to subtract. If a number is provided, it
        will be used to select the sensor by its index.
    align_dissociation : bool
        If True, aligns the dissociation phase of the sensors after subtraction.

    Returns
    -------
    str
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If the reference sensor is not in the list of sensor names, try to select it by index
    sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    if reference_sensor not in sensor_names:
        try:
            reference_sensor = sensor_names[int(reference_sensor) - 1]
        except (ValueError, IndexError):
            return f"Reference sensor '{reference_sensor}' not found in the list of sensors for experiment '{experiment_name}'."

    # Align the association phase of the sensors
    PY_KINETICS.experiments[experiment_name].align_association(sensor_names, inplace=True, new_names=False)

    # If align_dissociation is True, align the dissociation phase of the sensors
    if align_dissociation:
        PY_KINETICS.experiments[experiment_name].align_dissociation(sensor_names, inplace=True, new_names=False)

    # Remove the reference sensor from the list of sensors to be subtracted
    sensor_names = [s for s in sensor_names if s != reference_sensor]

    # Subtract the reference sensor from all other sensors
    PY_KINETICS.experiments[experiment_name].subtraction(sensor_names, reference_sensor, inplace=True)

    # Obtain the new names of the sensors after alignment and subtraction
    new_sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    return (
        f"Association phase aligned and reference sensor '{reference_sensor}' subtracted from sensors: {sensor_names}. "
        f"New sensor names: {new_sensor_names}.\n"
        f"Dissociation phase {'aligned' if align_dissociation else 'not aligned'}.")


@mcp.tool()
def obtain_sample_info_table() -> list[dict[str, Any]]:
    """
    Return merged PyKinGenie sample metadata as JSON records.

    This calls ``PY_KINETICS.merge_ligand_conc_df`` across loaded experiments.
    The resulting table can be edited and passed to
    ``initiate_fitting_datasets`` to choose traces, concentrations, sample names,
    replicates, and Smax grouping. The ``Experiment`` column holds the names
    the experiments were loaded with, and is kept even when only one
    experiment is loaded, so a saved table stays tied to its data.

    Returns
    -------
    str
        JSON records for the merged ligand-concentration DataFrame.
    """

    # PyKinGenie fills Experiment with each experiment's internal name, but
    # generate_fittings looks experiments up by the name they were loaded with.
    for name, experiment in PY_KINETICS.experiments.items():
        if getattr(experiment, "ligand_conc_df", None) is not None:
            experiment.ligand_conc_df["Experiment"] = name

    PY_KINETICS.merge_ligand_conc_df()
    df = PY_KINETICS.combined_ligand_conc_df
    names = PY_KINETICS.experiment_names
    if "Experiment" not in df.columns and len(names) == 1:
        df = df.assign(Experiment=names[0])
    return df.to_dict(orient="records")


@mcp.tool()
def initiate_fitting_datasets(sample_info: list[dict[str, Any]] | str | None = None) -> str:
    """
    Generate PyKinGenie fitting objects from sample metadata JSON.

    A template for the JSON representation can be generated using the
    ``obtain_sample_info_table`` tool. The user can edit the JSON string to select
    only the data they want to fit, change analyte concentrations, change sample
    names, and alter Smax grouping. Without metadata, every trace in the
    default table is used.

    The metadata is checked before the existing fitting objects are reset, so
    invalid or ambiguous rows leave the current fits untouched. Unselected rows
    and zero-concentration references are left out. Rows without
    ``Experiment`` are accepted when each trace is found in one loaded
    experiment only.

    Parameters
    ----------
    sample_info : list[dict] | str | None
        Sample metadata records, or a JSON string with them.

    Returns
    -------
    str
        A message listing the names of the generated fitting datasets.
    """

    if sample_info is None:
        sample_info = obtain_sample_info_table()

    try:
        if isinstance(sample_info, str):
            try:
                sample_info = json.loads(sample_info)
            except json.JSONDecodeError as exc:
                raise ValueError("Sample metadata is not valid JSON.") from exc
        selected = select_sample_rows(sample_info)
    except ValueError as exc:
        raise ToolError(str(exc)) from None

    # Clear all the current fittings in PY_KINETICS
    PY_KINETICS.init_fittings()

    PY_KINETICS.generate_fittings(pd.DataFrame(selected))

    # Find the names of the generated fittings
    fitting_names = PY_KINETICS.fittings_names

    # Return a message with the all the names of the generated datasets
    message = "Fitting datasets generated with the following names:\n"
    for name in fitting_names:
        message += f"- {name}\n"

    return message


@mcp.tool()
async def run_steady_state_fitting(steady_state_model: str = 'one_to_one',
                                   fit_sigma: bool = False) -> str:
    """
    Run PyKinGenie steady-state fitting for generated fitting datasets.

    This calls ``PY_KINETICS.submit_steady_state_fitting`` to fit
    concentration-response data independently from kinetic trace fitting.
    Existing kinetic fitting results are kept.

    Parameters
    ----------
    steady_state_model : str
        Steady-state model to fit. PyKinGenie accepts ``'one_to_one'`` and
        ``'two_to_one'``.
    fit_sigma : bool
        If True with ``'two_to_one'`` steady-state fitting, fit the shared
        cooperativity factor sigma.

    Returns
    -------
    str
        A confirmation message with the steady-state fitting settings used.
    """
    if steady_state_model not in STEADY_STATE_FITTING_MODELS:
        valid_models = ", ".join(sorted(STEADY_STATE_FITTING_MODELS))
        raise ValueError(
            f"Unknown steady-state fitting model '{steady_state_model}'. "
            f"Valid models: {valid_models}."
        )

    with keep_fit_results("kinetics"):
        PY_KINETICS.submit_steady_state_fitting(
            fitting_model=steady_state_model,
            fit_sigma=fit_sigma,
        )

    return (f"Steady-state fitting submitted with model: {steady_state_model}, "
            f"fit sigma: {fit_sigma}.")


@mcp.tool()
async def run_kinetics_fitting(fitting_model: str = 'one_to_one',
                               fitting_region: str = 'association_dissociation',
                               linked_smax: bool = False,
                               fit_sigma: bool = False) -> str:
    """
    Run PyKinGenie kinetic fitting for generated fitting datasets.

    This calculates the starting values required by PyKinGenie internally, then
    calls ``PY_KINETICS.submit_kinetics_fitting`` with the selected kinetic
    model, fitted region, Smax sharing setting, and optional two-site
    cooperativity setting. Use ``run_steady_state_fitting`` separately only
    when you want a standalone steady-state fit. Existing steady-state fitting
    results are kept.

    Inmediatly after the fitting, ask the user if they want to calculate erros by applying the leave-one-out method
    
    Parameters
    ----------
    fitting_model : str
        Kinetic model to fit. PyKinGenie accepts ``'one_to_one'``,
        ``'one_to_one_mtl'`` (mass transport limitation),
        ``'one_to_one_if'`` (induced fit), and ``'two_to_one'``. Only
        ``'one_to_one'`` supports every fitting region; the other kinetic
        models support only ``'association_dissociation'``.
    fitting_region : str
        The region of the data to be fitted. ``'one_to_one'`` supports
        ``'association_dissociation'``, ``'association'``, and
        ``'dissociation'``. ``'one_to_one_mtl'``, ``'one_to_one_if'``, and
        ``'two_to_one'`` support only ``'association_dissociation'``.
    linked_smax : bool
        Whether to link the Smax values across curves, i.e. assume the same
        sensor capacity.
    fit_sigma : bool
        If True with ``'two_to_one'`` kinetic fitting, fit the shared
        cooperativity factor sigma.

    Returns
    -------
    str
        A confirmation message with the kinetic fitting settings used.
    """

    valid_regions = KINETIC_FITTING_MODEL_REGIONS.get(fitting_model)
    if valid_regions is None:
        valid_models = ", ".join(sorted(KINETIC_FITTING_MODEL_REGIONS))
        raise ValueError(
            f"Unknown kinetic fitting model '{fitting_model}'. "
            f"Valid models: {valid_models}."
        )

    if fitting_region not in valid_regions:
        valid_regions_message = ", ".join(sorted(valid_regions))
        raise ValueError(
            f"Fitting model '{fitting_model}' does not support region "
            f"'{fitting_region}'. Valid regions: {valid_regions_message}."
        )

    steady_state_model = "two_to_one" if fitting_model == "two_to_one" else "one_to_one"
    with keep_fit_results("steady_state"):
        # The steady-state fit provides the starting values of the kinetic fit.
        PY_KINETICS.submit_steady_state_fitting(
            fitting_model=steady_state_model,
            fit_sigma=fit_sigma,
        )

        PY_KINETICS.submit_kinetics_fitting(fitting_model=fitting_model,
                                            fitting_region=fitting_region,
                                            shared_smax=linked_smax,
                                            fit_sigma=fit_sigma)

    return (f"Kinetics fitting submitted with model: {fitting_model}, "
            f"region: {fitting_region}, "
            f"linked Smax: {linked_smax}, "
            f"fit sigma: {fit_sigma}.")

@mcp.tool()
async def calc_leave_one_out_errors() -> str:
    """
    Calculate the errors of the fitted parameters, e.g., Kd and k_off, using the leave-one-out method.
    Briefly, for each fitting object (Sample ID), we do n-fits, where n is the total number of curves,
    leaving one curve out each time. Afterwards, the parameter value plus/minus error is available through
    get_leave_one_out_results
    """

    ok_fits, bad_fits = PY_KINETICS.calculate_leave_one_out_errors()

    return (
        f"Leave-one-out error calculation completed. "
        f"Successful fits: {ok_fits}. "
        f"Failed fits: {bad_fits}."
    )

@mcp.tool()
def get_leave_one_out_results() -> list[dict[str, Any]]: 
    
    """
    Return PyKinGenie leave-one-out results as JSON records.

    Returns
    -------
    str
        A JSON string representing the fitting results.
    """
    if not PY_KINETICS.fittings_names:
        raise RuntimeError(
            "No fitting datasets are available. Run initiate_fitting_datasets before retrieving kinetic results."
        )

    has_kinetic_results = any(
        getattr(PY_KINETICS.fittings[name], "fit_params_kinetics", None) is not None
        for name in PY_KINETICS.fittings_names
    )
    if not has_kinetic_results:
        raise RuntimeError(
            "No kinetic fitting results are available. Run run_kinetics_fitting before retrieving results."
        )

    dfs = []

    for name in PY_KINETICS.fittings_names:
        loo_df = PY_KINETICS.fittings[name].df_fit_loo
        if loo_df is not None:
            df = loo_df.copy()
            df['Name'] = name
            dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    return df.to_dict(orient="records")

@mcp.tool()
def get_kinetics_fitting_results() -> list[dict[str, Any]]:
    """
    Return PyKinGenie kinetic fitting results as JSON records.

    This calls ``PY_KINETICS.get_fitting_results`` and serializes
    ``fit_params_kinetics_all``, which contains fitted parameters such as Kd,
    k_off, k_on, and Smax when available.

    Returns
    -------
    str
        A JSON string representing the fitting results.
    """
    if not PY_KINETICS.fittings_names:
        raise RuntimeError(
            "No fitting datasets are available. Run initiate_fitting_datasets before retrieving kinetic results."
        )

    has_kinetic_results = any(
        getattr(PY_KINETICS.fittings[name], "fit_params_kinetics", None) is not None
        for name in PY_KINETICS.fittings_names
    )
    if not has_kinetic_results:
        raise RuntimeError(
            "No kinetic fitting results are available. Run run_kinetics_fitting before retrieving results."
        )

    PY_KINETICS.get_fitting_results()
    df = PY_KINETICS.fit_params_kinetics_all
    return df.to_dict(orient="records")


@mcp.tool()
def get_fitting_parameters() -> list[dict[str, Any]]:
    """
    Return the kinetic and steady-state fitted parameters as JSON records.

    Each record is one row of a dataset's ``fit_params_kinetics`` or
    ``fit_params_ss`` table, labeled with ``Fit type`` (``'Kinetics'`` or
    ``'Steady-state'``) and ``Dataset``. Missing numeric values are returned as
    null. This tool never runs a fit.

    Returns
    -------
    list of dict
        Fitted parameter records, or an empty list before any fit.
    """
    rows = []
    for dataset in PY_KINETICS.fittings_names:
        fitting = PY_KINETICS.fittings[dataset]
        for fit_type, attribute in (("Kinetics", "fit_params_kinetics"), ("Steady-state", "fit_params_ss")):
            table = getattr(fitting, attribute, None)
            if table is None:
                continue
            # The JSON round trip converts NaN to null and NumPy values to Python.
            for record in json.loads(table.to_json(orient="records", double_precision=15)):
                rows.append({**record, "Fit type": fit_type, "Dataset": dataset})
    return rows


@mcp.tool()
def create_export_df(export_type: str = 'raw') -> list[dict[str, Any]]:
    """
    Return exported PyKinGenie association/dissociation traces as JSON records.

    This calls ``PY_KINETICS.create_export_df`` for all generated fitting
    objects. Raw export returns the measured association and dissociation
    signals; fitted export returns fitted curves after ``run_kinetics_fitting``
    has been called.

    Parameters
    ----------
    export_type : str
        Signal type to export. Accepts ``'raw'``, ``'fit'``, or ``'fitted'``.
        ``'fitted'`` is normalized to PyKinGenie's ``'fit'`` spelling.

    Returns
    -------
    str
        JSON records for a DataFrame with exported trace points.
    """
    if export_type not in {"raw", "fit", "fitted"}:
        raise ValueError("export_type must be 'raw', 'fit', or 'fitted'.")

    if not PY_KINETICS.fittings_names:
        raise RuntimeError(
            "No fitting datasets are available. Run initiate_fitting_datasets before exporting traces."
        )

    if export_type in {"fit", "fitted"}:
        has_fitted_traces = any(
            getattr(PY_KINETICS.fittings[name], "signal_assoc_fit", None) is not None
            for name in PY_KINETICS.fittings_names
        )
        if not has_fitted_traces:
            raise RuntimeError(
                "No fitted kinetic traces are available. Run run_kinetics_fitting before exporting fitted traces."
            )

    pykingenie_export_type = "fit" if export_type == "fitted" else export_type
    df = PY_KINETICS.create_export_df(type=pykingenie_export_type)
    return df.to_dict(orient="records")


@mcp.tool()
def list_experiment_properties(variable: str, fittings: bool = False) -> list[Any]:
    """
    Get a PyKinGenie property from all experiments or fittings.

    This is a direct wrapper around ``PY_KINETICS.get_experiment_properties``.

    Parameters
    ----------
    variable : str
        The attribute to retrieve, e.g., ``'ligand_concentration'``,
        ``'sensor_names'``, etc.
    fittings : bool
        If True, returns attributes from the fitting objects instead of
        the experiments.

    Returns
    -------
    list
        A list of values for the specified variable from the experiments or fittings.
    """

    return PY_KINETICS.get_experiment_properties(variable, fittings)


@mcp.tool()
def list_experiment_attributes(experiment_name: str) -> dict[str, Any]:
    """
    Return all stored attributes for one PyKinGenie experiment.

    Run this tool only if the user asks for it specifically.

    Parameters
    ----------
    experiment_name : str
        The name of the experiment to list attributes for.
        If a number is provided, it will be used to select the experiment by its index.

    Returns
    -------
    dict
        A dictionary of experiment attributes.
    """

    # Default to the first experiment if no name is provided
    if experiment_name not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_name) - 1]
        except (ValueError, IndexError):
            raise KeyError(f"Experiment with index {experiment_name} not found in kingenie.")

    experiment = PY_KINETICS.experiments[experiment_name]

    attributes = vars(experiment)

    return attributes
