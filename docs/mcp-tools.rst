MCP Tools Reference
===================

``mcp_pykingenie`` exposes the following tools to your AI assistant.

Data Import
-----------

.. list-table::
   :header-rows: 1

   * - Tool
     - Description
   * - ``load_octet_example``
     - Load the bundled BLI example dataset.
   * - ``import_octet_experiment``
     - Import an Octet experiment from a folder of ``.frd`` files.
   * - ``import_gator_experiment``
     - Import a Gator experiment from a folder or ``.zip`` file.
   * - ``import_kingenie_surface_csv``
     - Import a KinGenie simulation CSV file.

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
   * - ``run_fitting``
     - Run fitting. Steady-state initialization supports ``one_to_one`` and ``two_to_one``. Kinetic ``one_to_one`` supports ``association_dissociation``, ``association``, and ``dissociation``; ``one_to_one_mtl``, ``one_to_one_if``, and ``two_to_one`` support only ``association_dissociation``.
   * - ``get_kinetics_fitting_results``
     - Retrieve fitting results, including ``Kd``, ``k_off``, ``Smax``, and derived ``k_on``.
   * - ``create_export_df``
     - Export raw or fitted association/dissociation trace points from generated fitting datasets as JSON records.
