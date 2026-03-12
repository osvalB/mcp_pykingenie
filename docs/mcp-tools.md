# MCP Tools Reference

`mcp_pykingenie` exposes the following tools to your AI assistant.

## Data Import

| Tool | Description |
|------|-------------|
| `load_octet_example` | Load the bundled BLI example dataset (no files needed) |
| `import_octet_experiment` | Import an Octet experiment from a folder of `.frd` files |
| `import_gator_experiment` | Import a Gator experiment from a folder or `.zip` file |

## File Utilities

| Tool | Description |
|------|-------------|
| `print_data_dir` | Print the current output data directory path |
| `list_files_in_folder` | List all files in a specified folder |

## Experiment Inspection

| Tool | Description |
|------|-------------|
| `list_experiment_names` | List all loaded experiment names |
| `list_experiment_properties` | Get a property (e.g. `sensor_names`) across all experiments |
| `list_experiment_attributes` | List all attributes of a single experiment |
| `obtain_sample_info_table` | Get analyte concentration and sensor metadata as JSON |

## Data Processing

| Tool | Description |
|------|-------------|
| `align_association` | Align the association phase of sensors |
| `align_dissociation` | Align the dissociation phase of sensors |
| `subtract_reference` | Subtract a reference sensor from other sensors |
| `align_and_subtract` | Combined align + subtract in one step |

## Plotting

| Tool | Description |
|------|-------------|
| `plot_sample_plate_info` | Plot the sample plate layout for an experiment |
| `get_legends_table` | Get sensor legend DataFrame (input for trace plots) |
| `plot_traces_with_all_steps` | Plot all BLI steps (baseline, assoc., dissoc., regen.) |
| `plot_kinetic_traces` | Plot association/dissociation traces from fitting datasets |
| `plot_steady_state` | Plot steady-state binding data |

## Fitting

| Tool | Description |
|------|-------------|
| `initiate_fitting_datasets` | Generate fitting datasets from a sample info JSON |
| `run_fitting` | Run kinetic fitting (`one_to_one`, `one_to_one_mtl`, `one_to_one_if`) |
| `get_kinetics_fitting_results` | Retrieve fitting results (Kd, k_off, Smax, etc.) |
