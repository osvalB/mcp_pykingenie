from mcp_pykingenie.mcp import mcp

import os
import pandas as pd

from ..server import PY_KINETICS, DATA_DIR, EXAMPLE_DATA_DIR

from datetime import datetime
from io import StringIO

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
def list_files_in_folder(folder: str = '') -> list:
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

    # Return error if no folder is provided
    if not folder:
        return FileNotFoundError("No folder provided. Please specify a folder.")

    try:

        files = os.listdir(folder)
        return [x for x in files if os.path.isfile(os.path.join(folder, x))]

    except:
        # Return error and message
        raise FileNotFoundError(f"The folder '{folder}' does not exist or is not accessible.")


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
def plot_sample_plate_info(experiment_id: str = '1', font_size: int = 18, save_html: bool = False) -> str:
    """
    Save a PyKinGenie sample-plate layout plot for one experiment.

    The plot is produced by :func:`pykingenie.plot_plate_info` and written as a
    PNG in ``DATA_DIR``. The experiment may be selected by name or by 1-based
    analyzer index.

    Parameters
    ----------
    experiment_id : str
        The name or index of the experiment to plot. If a number is provided,
        it will be used to select the experiment by its index.
    font_size : int
        The font size for the plot annotations.
    save_html : bool
        If True, saves the plot as an HTML file for interactive viewing.

    Returns
    -------
    str
        Message containing the saved PNG path.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except (ValueError, IndexError):
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    fig = pykingenie.plot_plate_info(
        PY_KINETICS,
        experiment_name,
        font_size=font_size
    )

    time_str = current_hour_min_sec()

    # Combine the data directory and the time string to create a unique filename
    image_filename = os.path.join(DATA_DIR, f'sample_plate_info_{experiment_name}_{time_str}.png')

    fig.write_image(image_filename, format='png')

    if save_html:
        # Save the plot also as an HTML file for interactive viewing
        html_filename = os.path.join(DATA_DIR, f'sample_plate_info_{experiment_name}_{time_str}.html')
        fig.write_html(html_filename)

    return 'Image saved to: ' + image_filename + '\n'


@mcp.tool()
def get_legends_table() -> str:
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
    df_json = df.to_json(orient='records')

    return df_json


@mcp.tool()
async def plot_traces_with_all_steps(legends_df: str = "",
                                     plot_width: int = 26,
                                     plot_height: int = 24,
                                     plot_type: str = 'png',
                                     font_size: int = 18,
                                     show_grid_x: bool = True,
                                     show_grid_y: bool = True,
                                     marker_size: int = 3,
                                     line_width: int = 2,
                                     save_html: bool = False) -> str:
    """
    Save a PyKinGenie plot containing all loaded trace steps.

    The plot is produced by :func:`pykingenie.plot_traces_all` using a legend
    table created by ``get_legends_table`` or supplied as JSON records. It can
    include baseline, loading, association, dissociation, and regeneration
    segments present in the imported experiments.

    Parameters
    ----------
    legends_df : str
        A JSON string representing the legend DataFrame.
    plot_width : int
        Plot width forwarded to PyKinGenie/Plotly.
    plot_height : int
        Plot height forwarded to PyKinGenie/Plotly.
    plot_type : str
        Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
    font_size : int
        Font size for the plot annotations.
    show_grid_x : bool
        Whether to show grid lines on the x-axis.
    show_grid_y : bool
        Whether to show grid lines on the y-axis.
    marker_size : int
        Size of the markers in the plot.
    line_width : int
        Width of the lines in the plot.
    save_html : bool
        Whether to save the plot as an HTML file for interactive viewing.

    Returns
    -------
    str
        Message containing the saved image path.
    """

    # generate legends_df if not provided
    if not legends_df:
        legends_df = get_legends_table()

    legends_df = pd.read_json(StringIO(legends_df), orient='records')

    fig = pykingenie.plot_traces_all(PY_KINETICS, legends_df,
                                     plot_width,
                                     plot_height,
                                     plot_type,
                                     font_size,
                                     show_grid_x, show_grid_y, marker_size, line_width)

    time_str = current_hour_min_sec()
    # Combine the data directory and the time string to create a unique filename
    image_filename = os.path.join(DATA_DIR, f'kingenie_traces_{time_str}.{plot_type}')

    fig.write_image(image_filename, format=plot_type)

    if save_html:
        # Save the plot also as an HTML file for interactive viewing
        html_filename = os.path.join(DATA_DIR, f'kingenie_traces_{time_str}.html')
        fig.write_html(html_filename)

    # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
    return 'Plot saved to: ' + image_filename + '\n'


@mcp.tool()
async def plot_steady_state(plot_width: int = 26,
                            plot_height: int = 24,
                            plot_type: str = 'png',
                            font_size: int = 18,
                            show_grid_x: bool = True,
                            show_grid_y: bool = True,
                            marker_size: int = 3,
                            line_width: int = 2,
                            save_html: bool = False) -> str:
    """
    Save a PyKinGenie steady-state plot for generated fittings.

    This calls :func:`pykingenie.plot_steady_state` with ``plot_fit=True`` and
    requires fitting datasets generated by ``initiate_fitting_datasets``.

    Parameters
    ----------
    plot_width : int
        Plot width forwarded to PyKinGenie/Plotly.
    plot_height : int
        Plot height forwarded to PyKinGenie/Plotly.
    plot_type : str
        Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
    font_size : int
        Font size for the plot annotations.
    show_grid_x : bool
        Whether to show grid lines on the x-axis.
    show_grid_y : bool
        Whether to show grid lines on the y-axis.
    marker_size : int
        Size of the markers in the plot.
    line_width : int
        Width of the lines in the plot.
    save_html : bool
        Whether to save the plot as an HTML file for interactive viewing.

    Returns
    -------
    str
        Message containing the saved image path.
    """

    fig = pykingenie.plot_steady_state(PY_KINETICS,
                                       plot_width,
                                       plot_height,
                                       plot_type,
                                       font_size,
                                       show_grid_x,
                                       show_grid_y,
                                       marker_size,
                                       line_width,
                                       plot_fit=True)

    time_str = current_hour_min_sec()
    # Combine the data directory and the time string to create a unique filename
    image_filename = os.path.join(DATA_DIR, f'kingenie_steady_state_{time_str}.{plot_type}')

    fig.write_image(image_filename, format=plot_type)

    if save_html:
        # Save the plot also as an HTML file for interactive viewing
        html_filename = os.path.join(DATA_DIR, f'kingenie_steady_state_{time_str}.html')
        fig.write_html(html_filename)
    # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
    return 'Plot saved to: ' + image_filename + '\n'


@mcp.tool()
def list_experiment_names() -> list:
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
                      sensor_names: list = [],
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
def subtract_reference(experiment_id: str = '1', list_of_sensor_names: list = [],
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

    target_experiment.subtract_experiment(reference_experiment, inplace=inplace)

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
def align_dissociation(experiment_id: str = '1',
                       sensor_names: list = [],
                       in_place: bool = True,
                       new_names: bool = False,
                       npoints: int = 10) -> str:
    """
    Align dissociation phases for selected sensors in a PyKinGenie experiment.

    This calls ``SurfaceBasedExperiment.align_dissociation``. PyKinGenie smooths
    or offsets traces around association-to-dissociation transitions and updates
    trace arrays, sensor names, and ligand metadata according to ``in_place`` and
    ``new_names``.

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
def obtain_sample_info_table() -> str:
    """
    Return merged PyKinGenie sample metadata as JSON records.

    This calls ``PY_KINETICS.merge_ligand_conc_df`` across loaded experiments.
    The resulting table can be edited and passed to
    ``initiate_fitting_datasets`` to choose traces, concentrations, sample names,
    replicates, and Smax grouping.

    Returns
    -------
    str
        JSON records for the merged ligand-concentration DataFrame.
    """

    PY_KINETICS.merge_ligand_conc_df()
    df = PY_KINETICS.combined_ligand_conc_df
    df_json = df.to_json(orient='records')

    return df_json


@mcp.tool()
def initiate_fitting_datasets(json_str: str) -> str:
    """
    Generate PyKinGenie fitting objects from sample metadata JSON.

    A template for the JSON representation can be generated using the
    ``obtain_sample_info_table`` tool. The user can edit the JSON string to select
    only the data they want to fit, change analyte concentrations, change sample
    names, and alter Smax grouping. Existing fitting objects are reset before
    ``PY_KINETICS.generate_fittings`` is called.

    Parameters
    ----------
    json_str : str
        JSON string representing the DataFrame.

    Returns
    -------
    str
        A message listing the names of the generated fitting datasets.
    """

    try:
        # Load the JSON string into a DataFrame
        df = pd.read_json(StringIO(json_str), orient='records')
    except:
        PY_KINETICS.merge_ligand_conc_df()  # So it works in case the user did not run the `obtain_df_for_fitting` tool
        df = PY_KINETICS.combined_ligand_conc_df
        print("Invalid JSON string provided. Using the default DataFrame.")

    # Clear all the current fittings in PY_KINETICS
    PY_KINETICS.init_fittings()

    PY_KINETICS.generate_fittings(df)

    # Find the names of the generated fittings
    fitting_names = PY_KINETICS.fittings_names

    # Return a message with the all the names of the generated datasets
    message = "Fitting datasets generated with the following names:\n"
    for name in fitting_names:
        message += f"- {name}\n"

    return message


@mcp.tool()
async def plot_kinetic_traces(plot_width: int = 26,
                              plot_height: int = 24,
                              plot_type: str = 'png',
                              font_size: int = 16,
                              show_grid_x: bool = True,
                              show_grid_y: bool = True,
                              marker_size: int = 3,
                              line_width: int = 2,
                              split_by_smax_id: bool = False,
                              max_points_per_plot: int = 1000,
                              smooth_curves_fit: bool = False,
                              rolling_window: int = 10,
                              save_html: bool = False) -> str:
    """
    Save a PyKinGenie association/dissociation plot for fittings.

    Requires that the fitting datasets have been generated using the
    ``initiate_fitting_datasets`` tool. The ligand concentrations are colored by
    PyKinGenie, and fitted curves are included when fitting results are present.

    Parameters
    ----------
    plot_width : int
        Plot width forwarded to PyKinGenie/Plotly.
    plot_height : int
        Plot height forwarded to PyKinGenie/Plotly.
    plot_type : str
        Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
    font_size : int
        Font size for the plot annotations.
    show_grid_x : bool
        Whether to show grid lines on the x-axis.
    show_grid_y : bool
        Whether to show grid lines on the y-axis.
    marker_size : int
        Size of the markers in the plot.
    line_width : int
        Width of the lines in the plot.
    split_by_smax_id : bool
        If True, splits the plots by Smax ID.
    max_points_per_plot : int
        Maximum number of points per plot. If exceeded, data will be subsetted.
    smooth_curves_fit : bool
        If True, asks PyKinGenie to smooth fitted curves.
    rolling_window : int
        Rolling-window value forwarded to PyKinGenie for smoothing.
    save_html : bool
        If True, saves the plot as an HTML file for interactive viewing.

    Returns
    -------
    str
        Message containing the saved image path.
    """

    fig = pykingenie.plot_association_dissociation(PY_KINETICS,
                                                   plot_width=plot_width,
                                                   plot_height=plot_height,
                                                   plot_type=plot_type,
                                                   font_size=font_size,
                                                   show_grid_x=show_grid_x,
                                                   show_grid_y=show_grid_y,
                                                   marker_size=marker_size,
                                                   line_width=line_width,
                                                   split_by_smax_id=split_by_smax_id,
                                                   max_points_per_plot=max_points_per_plot,
                                                   smooth_curves_fit=smooth_curves_fit,
                                                   rolling_window=rolling_window
                                                   )

    time_str = current_hour_min_sec()
    # Combine the data directory and the time string to create a unique filename
    image_filename = os.path.join(DATA_DIR, f'kingenie_kinetic_traces_{time_str}.{plot_type}')

    fig.write_image(image_filename, format=plot_type)

    if save_html:
        # Save the plot also as an HTML file for interactive viewing
        html_filename = os.path.join(DATA_DIR, f'kingenie_kinetic_traces_{time_str}.html')
        fig.write_html(html_filename)
    # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
    return 'Plot saved to: ' + image_filename + '\n'


@mcp.tool()
async def run_steady_state_fitting(steady_state_model: str = 'one_to_one',
                                   fit_sigma: bool = False) -> str:
    """
    Run PyKinGenie steady-state fitting for generated fitting datasets.

    This calls ``PY_KINETICS.submit_steady_state_fitting`` to fit
    concentration-response data independently from kinetic trace fitting.

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
    when you want a standalone steady-state fit.

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
def get_kinetics_fitting_results() -> str:
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
    results_json = df.to_json(orient='records')

    return results_json


@mcp.tool()
def create_export_df(export_type: str = 'raw') -> str:
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

    return df.to_json(orient='records')


@mcp.tool()
def list_experiment_properties(variable: str, fittings: bool = False) -> list:
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
def list_experiment_attributes(experiment_name: str) -> dict:
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
