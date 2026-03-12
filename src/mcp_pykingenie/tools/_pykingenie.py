from mcp_pykingenie.mcp import mcp

import os
import pandas as pd

from ..server import PY_KINETICS, DATA_DIR, EXAMPLE_DATA_DIR

from datetime import datetime

import pykingenie


def current_hour_min_sec():
    """
    Get the current time in HH-MM-SS format.
    Returns:
        str: Current time as a string.
    """
    now = datetime.now()
    return now.strftime('%H-%M-%S')


# To be called by mcp tools import_octet_experiment and load_octet_example
def import_octet_experiment_base(folder: str = '.', exp_name: str = 'Experiment') -> str:
    """
    Add a new experiment to the pykinetics analyzer from an Octet folder.
    Args:
        folder: Name of the folder containing the Octet data files. (.frd files)
        exp_name: Name of the experiment to be added.
    Returns:
        A confirmation message.
    """

    # Find if full path is provided or just the folder name
    if os.path.isabs(folder):
        folder_path = folder
    else:
        folder_path = os.path.join(DATA_DIR, folder)

    octet = pykingenie.OctetExperiment()

    files = os.listdir(folder_path)
    files = [os.path.join(folder_path, f) for f in files]

    octet.read_sensor_data(files)
    octet.read_sample_plate_info(files)

    PY_KINETICS.add_experiment(octet, exp_name)

    return f"Octet experiment added from {folder}."


@mcp.tool()
def print_data_dir() -> str:
    """
    Print the path to the data directory, where the generated files will be stored.
    Returns:
        The path to the data directory.
    """
    return f"{DATA_DIR}"


@mcp.tool()
def list_files_in_folder(folder: str = '') -> list:
    """
    List all files in the selected folder
    Args:
        folder: The folder to list files from
    Returns:
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
    Add a new experiment to the pykinetics analyzer.
    The csv file can be created using the simulation tool in the KinGenie online tool.
    Args:
        csv: Path to the CSV file containing the simulaton data.
        exp_name: Name of the experiment to be added.
    Returns:
        A confirmation message.
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
    Add a new experiment to the pykinetics analyzer from an Octet folder.
    Args:
        folder: Name of the folder containing the Octet data files. (.frd files)
        exp_name: Name of the experiment to be added.
    Returns:
        A confirmation message.
    """

    return import_octet_experiment_base(folder, exp_name)


@mcp.tool()
def import_gator_experiment(folder: str = '.', exp_name: str = 'Experiment') -> str:
    """
    Add a new experiment to the pykinetics analyzer from a Gator folder / zip file.
    Args:
        folder: Name of the folder containing the Gator data files:
            ('Assay_#_Channel#.csv') and the corresponding files describing the metadata
            (Setting.ini and ExperimentStep.ini)
        exp_name: Name of the experiment to be added.
    Returns:
        A confirmation message.
    """

    # Find if full path is provided or just the folder name
    if os.path.isabs(folder):
        folder_path = folder
    else:
        folder_path = os.path.join(DATA_DIR, folder)

    # Check if we have a zip file or a folder, if we have a zip, extract it to a folder
    if folder_path.endswith('.zip'):
        import zipfile
        with zipfile.ZipFile(folder, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)  # Extract to the data directory
            # Obtain the name of the zip file without the .zip extension
            # and use it as the folder name
            folder = os.path.splitext(os.path.basename(folder))[0]
            # Update the folder path to the extracted folder
            folder_path = os.path.join(DATA_DIR, folder)

    gator = pykingenie.GatorExperiment()

    files = os.listdir(folder_path)
    files = [os.path.join(folder_path, f) for f in files]

    gator.read_all_gator_data(files)

    PY_KINETICS.add_experiment(gator, exp_name)

    return f"Gator experiment added from {folder}."


@mcp.tool()
def load_octet_example() -> str:
    """
    Load an example experiment from the pykinetics analyzer.
    The example experiment comes from an Octet (Biolayer interferometry) experiment.
    This will load the example data provided with the pykingenie package.
    Returns:
        A confirmation message.
    """
    example_folder_path = os.path.join(EXAMPLE_DATA_DIR, 'test_bli_folder')

    return import_octet_experiment_base(folder=example_folder_path, exp_name='Example Experiment')


@mcp.tool()
def plot_sample_plate_info(experiment_id: str = '1', font_size: int = 18, save_html: bool = False) -> str:
    """
    Plot the sample plate information for a given experiment in the pykinetics analyzer.
    Args:
    experiment_name: The name of the experiment to plot. If a number is provided, it will be used to select the experiment by its index.
    font_size: The font size for the plot annotations.
    save_html: If True, saves the plot as an HTML file for interactive viewing.
    Returns:
        The html string of a Plotly Figure object containing the sample plate information.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except KeyError:
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
    Get the legend dataframe containing the sensor names, their unique IDs, and colors.
    Returns:
        A JSON string representing the legend DataFrame.
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
    Plot the traces from the pykinetics analyzer using the provided legend DataFrame.
    The legend DataFrame can be first created using the `get_legends_table` tool.
    The plot will include all steps such as the baseline, association, dissociation, and regeneration phases.
    Args:
        legends_df: A JSON string representing the legend DataFrame.
        plot_width: Width of the plot in pixels*50.
        plot_height: Height of the plot in pixels*50.
        plot_type: Type of the plot to generate ('png', 'svg', 'jpeg').
        font_size: Font size for the plot annotations.
        show_grid_x: Whether to show grid lines on the x-axis.
        show_grid_y: Whether to show grid lines on the y-axis.
        marker_size: Size of the markers in the plot.
        line_width: Width of the lines in the plot.
        save_html: Whether to save the plot as an HTML file for interactive viewing.
    Returns:
        A string indicating the path to the saved image file.
    """

    # generate legends_df if not provided
    if not legends_df:
        legends_df = get_legends_table()

    legends_df = pd.read_json(legends_df, orient='records')

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

    Plot the steady state data from the pykinetics analyzer. It uses the 'fitting' objects
    It can only be run after the `generate_fitting_dataset` tool has been run.
    Args:
        plot_width: Width of the plot in pixels*50.
        plot_height: Height of the plot in pixels*50.
        plot_type: Type of the plot to generate ('png', 'svg', 'jpeg').
        font_size: Font size for the plot annotations.
        show_grid_x: Whether to show grid lines on the x-axis.
        show_grid_y: Whether to show grid lines on the y-axis.
        marker_size: Size of the markers in the plot.
        line_width: Width of the lines in the plot.
        save_html: Whether to save the plot as an HTML file for interactive viewing.
    Returns:
        str indicating the path to the saved image file.
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
    Returns:
        A list of experiment names.
    """
    return PY_KINETICS.experiment_names


@mcp.tool()
def align_association(experiment_id: str = '1',
                      sensor_names: list = [],
                      in_place: bool = True,
                      new_names: bool = False) -> str:
    """
    Align the association phase of the specified experiment in the pykinetics analyzer.
    Args:
        experiment_id: The name of the experiment to align. If a number is provided, it will be used to select the experiment by its index.
        sensor_names: A list of sensor names to align.
        in_place: If True, modifies the existing sensors; if False, creates new sensors.
        new_names : If True, uses new names for the aligned sensors.
    Returns:
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except KeyError:
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
    Subtract the reference sensor from the specified sensors in the pykinetics analyzer.
    Args:
        experiment_id: The name of the experiment to subtract the reference from.
        If a number is provided, it will be used to select the experiment by its index.
        list_of_sensor_names: A list of sensor names to subtract the reference from.
        If no names are provided, all sensors in the experiment will be used, except the reference sensor.
        reference_sensor: The name of the reference sensor to subtract.
        If a number is provided, it will be used to select the sensor by its index.
        inplace: If True, modifies the existing sensors; if False, creates new sensors.
    Returns:
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except KeyError:
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
def align_dissociation(experiment_id: str = '1',
                       sensor_names: list = [],
                       in_place: bool = True,
                       new_names: bool = False) -> str:
    """
    Align the dissociation phase of the specified experiment in the pykinetics analyzer.
    Args:
        experiment_id: The name of the experiment to align. If a number is provided, it will be used to select the experiment by its index.
        sensor_names: A list of sensor names to align.
        If no names are provided, all sensors in the experiment will be used.
        in_place: If True, modifies the existing sensors; if False, creates new sensors.
        new_names : If True, uses new names for the aligned sensors.
    Returns:
        A confirmation message.
    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except KeyError:
            return f"Experiment with index {experiment_id} not found in kingenie."
    else:
        experiment_name = experiment_id

    # If no sensor names are provided, use all sensors in the experiment
    if not sensor_names:
        sensor_names = PY_KINETICS.experiments[experiment_name].sensor_names

    PY_KINETICS.experiments[experiment_name].align_dissociation(sensor_names, in_place, new_names)

    # Print the message with the experiment and sensor names
    return f"Dissociation phase aligned for experiment: {experiment_name} with sensors: {', '.join(sensor_names)}."


@mcp.tool()
def align_and_subtract(experiment_id: str = '1',
                       reference_sensor: str = '1',
                       align_dissociation: bool = False) -> str:
    """
    Given an experiment ID and a reference sensor, align the association phases of all sensors in the experiment,
    and then subtract the reference sensor from all other sensors.
    Args:
        experiment_id: The name of the experiment. If a number is provided, it will be used to select the experiment by its index.
        reference_sensor: The name of the reference sensor to subtract. If a number is provided, it will be used to select the sensor by its index.
        align_dissociation: If True, aligns the dissociation phase of the sensors after subtraction.

    """

    if experiment_id not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
        except KeyError:
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
    Obtain the dataframe with the analyte concentration, sensor, Smax ID, Sample ID, analyte location and loading location.
    The dataframe can be used to generate a fitting dataset with the tool `initiate_fitting_datasets`.
    Print the dataset to the user as a in a nicely formatted table
    Returns:
        A pandas DataFrame in JSON format.
    """

    PY_KINETICS.merge_ligand_conc_df()
    df = PY_KINETICS.combined_ligand_conc_df
    df_json = df.to_json(orient='records')

    return df_json


@mcp.tool()
def initiate_fitting_datasets(json_str: str) -> str:
    """
    Generate a fitting dataset from the JSON representation of the DataFrame.
    A template for the JSON representation can be generated using the `obtain_df_for_fitting` tool.
    The idea is that the user can edit the JSON string to select only the data they want to fit,
    change the analyte concentrations, or change the sample names.

    Args:
        json_str: JSON string representing the DataFrame.
    """

    try:
        # Load the JSON string into a DataFrame
        df = pd.read_json(json_str, orient='records')
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
    Plot the association and dissociation traces from the pykinetics analyzer.
    It requires that the fitting datasets have been generated using the `initiate_fitting_datasets` tool.
    The ligand concentrations are colored using the viridis color palette.
    If available, the fitted curves will be plotted as well.
    Args:
        plot_width: Width of the plot in pixels*50.
        plot_height: Height of the plot in pixels*50.
        plot_type: Type of the plot to generate ('png', 'svg', 'jpeg').
        font_size: Font size for the plot annotations.
        show_grid_x: Whether to show grid lines on the x-axis.
        show_grid_y: Whether to show grid lines on the y-axis.
        marker_size: Size of the markers in the plot.
        line_width: Width of the lines in the plot.
        split_by_smax_id: If True, splits the plots by Smax ID.
        max_points_per_plot: Maximum number of points per plot. If exceeded, data will be subsetted.
        smooth_curves_fit: If True, applies a rolling window smoothing to the fitted curves.
        rolling_window: Size of the rolling window for smoothing.
        save_html: If True, saves the plot as an HTML file for interactive viewing.

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
async def run_fitting(fitting_model: str = 'one_to_one',
                      fitting_region: str = 'association_dissociation',
                      linked_smax: bool = False) -> str:
    """
    Run the fitting process with the specified model and region.
    Args:
        fitting_model: The model to be used for fitting.
            can be 'one_to_one', 'one_to_one_mtl' (mass transport limitation), 'one_to_one_if' (induced fit)
        fitting_region: The region of the data to be fitted.
            can be 'association_dissociation', 'association', or 'dissociation'.
        linked_smax: Whether to link the Smax values across curves.
            In other words, if we should assume the same sensor capacity
    """

    PY_KINETICS.submit_steady_state_fitting()  # To obtain initial values for the Kd and Smax parameters

    PY_KINETICS.submit_kinetics_fitting(fitting_model=fitting_model,
                                        fitting_region=fitting_region,
                                        linkedSmax=linked_smax)

    return (f"Fitting submitted with model: {fitting_model}, "
            f"region: {fitting_region}, "
            f"linked Smax: {linked_smax}.")


@mcp.tool()
def get_kinetics_fitting_results() -> str:
    """
    Get the results of the fitting process. It creates a DataFrame with the fitted parameters, such as Kd, k_off and Smax
    Returns:
        A JSON string representing the fitting results.
    """

    PY_KINETICS.get_fitting_results()
    df = PY_KINETICS.fit_params_kinetics_all
    results_json = df.to_json(orient='records')

    return results_json


@mcp.tool()
def list_experiment_properties(variable: str, fittings: bool = False) -> list:
    """
    Get the properties of the experiments stored in PY_KINETICS
    Args:
        variable: The attribute to retrieve, e.g., 'ligand_concentration', 'sensor_names', etc.
        fittings: If True, returns attributes from the fitting objects instead of the experiments.
    Returns:
        A list of values for the specified variable from the experiments or fittings.
    """

    return PY_KINETICS.get_experiment_properties(variable, fittings)


@mcp.tool()
def list_experiment_attributes(experiment_name: str) -> dict:
    """
    List all attributes of one experiment in the pykinetics analyzer.
    Run this tool only if the user asks for it specifically.
    Args:
        experiment_name: The name of the experiment to list attributes for.
            If a number is provided, it will be used to select the experiment by its index.
    Returns:
        A list of experiment attributes.
    """

    # Default to the first experiment if no name is provided
    if experiment_name not in PY_KINETICS.experiment_names:
        try:
            experiment_name = PY_KINETICS.experiment_names[int(experiment_name) - 1]
        except KeyError:
            raise KeyError(f"Experiment with index {experiment_name} not found in kingenie.")

    experiment = PY_KINETICS.experiments[experiment_name]

    attributes = vars(experiment)

    return attributes