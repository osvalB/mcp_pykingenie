MCP Tools Reference
===================

``mcp_pykingenie`` exposes the following tools to your AI assistant. These
tools are intended only for surface-based binding data, such as Octet and Gator
BLI experiments.

Data Import
-----------

Import tools accept absolute paths, or paths relative to the active MCP data
directory shown by ``print_data_dir``. Imported experiments are kept in memory
for the current MCP session and can be checked with ``list_experiment_names``.

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``load_octet_example``
     - Load the bundled Octet BLI example dataset.
   * - ``import_octet_experiment``
     - Import an Octet experiment from a folder of ``.frd`` sensor files and sample plate metadata.
   * - ``import_gator_experiment``
     - Import a Gator experiment from a folder or ``.zip`` file containing channel CSV files, ``Setting.ini``, and ``ExperimentStep.ini``.
   * - ``import_kingenie_surface_csv``
     - Import a KinGenie surface-simulation CSV file with trace and concentration columns.

Import Notes
^^^^^^^^^^^^

``import_octet_experiment``
   Pass a folder path. The folder should contain the Octet ``.frd`` files and
   sample plate files exported by the Octet software. If the path is not
   absolute, it is resolved inside the active MCP data directory.

``import_gator_experiment``
   Pass either a folder path or a ``.zip`` archive. The input should include the
   assay channel CSV files plus ``Setting.ini`` and ``ExperimentStep.ini``. Zip
   archives are extracted into the active MCP data directory, then loaded from
   the extracted folder.

``import_kingenie_surface_csv``
   Pass a CSV file path. The file is expected to describe surface-based traces,
   with columns such as ``Time``, ``Signal``, ``Smax``, and
   ``Analyte_concentration_micromolar_constant``.

``load_octet_example``
   Loads the packaged example as ``Example Experiment``. This is useful for
   verifying that plotting, preprocessing, and fitting tools are working before
   importing your own data. Download the raw example files as
   :download:`octet_bli_example_data.zip
   <_static/downloads/octet_bli_example_data.zip>`.

File Utilities
--------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``print_data_dir``
     - Print the current output data directory path.
   * - ``list_files_in_folder``
     - List all files in a specified folder.

Experiment Inspection
---------------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``list_experiment_names``
     - List all loaded experiment names.
   * - ``list_experiment_properties``
     - Get a property, such as ``sensor_names``, across experiments.
   * - ``list_experiment_attributes``
     - List all attributes of a single experiment.
   * - ``obtain_sample_info_table``
     - Get analyte concentration and sensor metadata as JSON.

Data Processing
---------------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``align_association``
     - Align the association phase of sensors.
   * - ``align_dissociation``
     - Align the dissociation phase of sensors.
   * - ``subtract_reference``
     - Subtract a reference sensor from other sensors.
   * - ``subtract_experiment``
     - Subtract one surface-based experiment from another sensor by sensor.
   * - ``subtract_sensor_columns``
     - Subtract paired sensor columns within one surface-based experiment.
   * - ``align_and_subtract``
     - Align and subtract a reference sensor in one step.

Plotting
--------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``plot_sample_plate_info``
     - Plot the sample plate layout for an experiment.
   * - ``get_legends_table``
     - Get the sensor legend DataFrame used by trace plots.
   * - ``plot_traces_with_all_steps``
     - Plot all BLI steps, including baseline, association, dissociation, and regeneration phases.
   * - ``plot_kinetic_traces``
     - Plot association and dissociation traces from fitting datasets.
   * - ``plot_steady_state``
     - Plot steady-state binding data.

Fitting
-------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``initiate_fitting_datasets``
     - Generate fitting datasets from a sample info JSON table.
   * - ``run_steady_state_fitting``
     - Run steady-state fitting as an alternative to kinetic fitting. Supports ``one_to_one`` and ``two_to_one``.
   * - ``run_kinetics_fitting``
     - Run kinetic fitting as an alternative to standalone steady-state fitting. The tool handles PyKinGenie's required starting values internally. ``one_to_one`` supports ``association_dissociation``, ``association``, and ``dissociation``; ``one_to_one_mtl``, ``one_to_one_if``, and ``two_to_one`` support only ``association_dissociation``.
   * - ``get_kinetics_fitting_results``
     - Retrieve fitting results, including ``Kd``, ``k_off``, ``Smax``, and derived ``k_on``.
   * - ``create_export_df``
     - Export raw or fitted association/dissociation trace points from generated fitting datasets as JSON records.
