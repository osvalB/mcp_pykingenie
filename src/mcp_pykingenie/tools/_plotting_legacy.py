"""Legacy PyKinGenie plotting tools, kept for reference only.

These tools were replaced by the XY plotting tools in
:mod:`mcp_pykingenie.tools._plotting_xy`. The code is commented out so it is
neither imported nor registered with the MCP server. To restore a tool,
uncomment it, move it back to :mod:`mcp_pykingenie.tools._pykingenie` and
add it to :mod:`mcp_pykingenie.tools`.
"""

# @mcp.tool()
# def plot_sample_plate_info(experiment_id: str = '1', font_size: int = 18, save_html: bool = False) -> str:
#     """
#     Save a PyKinGenie sample-plate layout plot for one experiment.
#
#     The plot is produced by :func:`pykingenie.plot_plate_info` and written as a
#     PNG in ``DATA_DIR``. The experiment may be selected by name or by 1-based
#     analyzer index.
#
#     Parameters
#     ----------
#     experiment_id : str
#         The name or index of the experiment to plot. If a number is provided,
#         it will be used to select the experiment by its index.
#     font_size : int
#         The font size for the plot annotations.
#     save_html : bool
#         If True, saves the plot as an HTML file for interactive viewing.
#
#     Returns
#     -------
#     str
#         Message containing the saved PNG path.
#     """
#
#     if experiment_id not in PY_KINETICS.experiment_names:
#         try:
#             experiment_name = PY_KINETICS.experiment_names[int(experiment_id) - 1]
#         except (ValueError, IndexError):
#             return f"Experiment with index {experiment_id} not found in kingenie."
#     else:
#         experiment_name = experiment_id
#
#     fig = pykingenie.plot_plate_info(
#         PY_KINETICS,
#         experiment_name,
#         font_size=font_size
#     )
#
#     time_str = current_hour_min_sec()
#
#     # Combine the data directory and the time string to create a unique filename
#     image_filename = os.path.join(DATA_DIR, f'sample_plate_info_{experiment_name}_{time_str}.png')
#
#     fig.write_image(image_filename, format='png')
#
#     if save_html:
#         # Save the plot also as an HTML file for interactive viewing
#         html_filename = os.path.join(DATA_DIR, f'sample_plate_info_{experiment_name}_{time_str}.html')
#         fig.write_html(html_filename)
#
#     return 'Image saved to: ' + image_filename + '\n'


# @mcp.tool()
# async def plot_traces_with_all_steps(legends_df: list[dict[str, Any]] | str | None = None,
#                                      plot_width: int = 26,
#                                      plot_height: int = 24,
#                                      plot_type: str = 'png',
#                                      font_size: int = 18,
#                                      show_grid_x: bool = True,
#                                      show_grid_y: bool = True,
#                                      marker_size: int = 3,
#                                      line_width: int = 2,
#                                      save_html: bool = False) -> str:
#     """
#     Save a PyKinGenie plot containing all loaded trace steps.
#
#     The plot is produced by :func:`pykingenie.plot_traces_all` using a legend
#     table created by ``get_legends_table`` or supplied as JSON records. It can
#     include baseline, loading, association, dissociation, and regeneration
#     segments present in the imported experiments.
#
#     Parameters
#     ----------
#     legends_df : str
#         A JSON string representing the legend DataFrame.
#     plot_width : int
#         Plot width forwarded to PyKinGenie/Plotly.
#     plot_height : int
#         Plot height forwarded to PyKinGenie/Plotly.
#     plot_type : str
#         Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
#     font_size : int
#         Font size for the plot annotations.
#     show_grid_x : bool
#         Whether to show grid lines on the x-axis.
#     show_grid_y : bool
#         Whether to show grid lines on the y-axis.
#     marker_size : int
#         Size of the markers in the plot.
#     line_width : int
#         Width of the lines in the plot.
#     save_html : bool
#         Whether to save the plot as an HTML file for interactive viewing.
#
#     Returns
#     -------
#     str
#         Message containing the saved image path.
#     """
#
#     if not legends_df:
#         legends_df = get_legends_table()
#
#     if isinstance(legends_df, str):
#         legends_df = json.loads(legends_df)
#
#     legends_df = pd.DataFrame(legends_df)
#
#     fig = pykingenie.plot_traces_all(PY_KINETICS, legends_df,
#                                      plot_width,
#                                      plot_height,
#                                      plot_type,
#                                      font_size,
#                                      show_grid_x, show_grid_y, marker_size, line_width)
#
#     time_str = current_hour_min_sec()
#     # Combine the data directory and the time string to create a unique filename
#     image_filename = os.path.join(DATA_DIR, f'kingenie_traces_{time_str}.{plot_type}')
#
#     fig.write_image(image_filename, format=plot_type)
#
#     if save_html:
#         # Save the plot also as an HTML file for interactive viewing
#         html_filename = os.path.join(DATA_DIR, f'kingenie_traces_{time_str}.html')
#         fig.write_html(html_filename)
#
#     # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
#     return 'Plot saved to: ' + image_filename + '\n'


# @mcp.tool()
# async def plot_steady_state(plot_width: int = 26,
#                             plot_height: int = 24,
#                             plot_type: str = 'png',
#                             font_size: int = 18,
#                             show_grid_x: bool = True,
#                             show_grid_y: bool = True,
#                             marker_size: int = 3,
#                             line_width: int = 2,
#                             save_html: bool = False) -> str:
#     """
#     Save a PyKinGenie steady-state plot for generated fittings.
#
#     This calls :func:`pykingenie.plot_steady_state` with ``plot_fit=True`` and
#     requires fitting datasets generated by ``initiate_fitting_datasets``.
#
#     Parameters
#     ----------
#     plot_width : int
#         Plot width forwarded to PyKinGenie/Plotly.
#     plot_height : int
#         Plot height forwarded to PyKinGenie/Plotly.
#     plot_type : str
#         Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
#     font_size : int
#         Font size for the plot annotations.
#     show_grid_x : bool
#         Whether to show grid lines on the x-axis.
#     show_grid_y : bool
#         Whether to show grid lines on the y-axis.
#     marker_size : int
#         Size of the markers in the plot.
#     line_width : int
#         Width of the lines in the plot.
#     save_html : bool
#         Whether to save the plot as an HTML file for interactive viewing.
#
#     Returns
#     -------
#     str
#         Message containing the saved image path.
#     """
#
#     fig = pykingenie.plot_steady_state(PY_KINETICS,
#                                        plot_width,
#                                        plot_height,
#                                        plot_type,
#                                        font_size,
#                                        show_grid_x,
#                                        show_grid_y,
#                                        marker_size,
#                                        line_width,
#                                        plot_fit=True)
#
#     time_str = current_hour_min_sec()
#     # Combine the data directory and the time string to create a unique filename
#     image_filename = os.path.join(DATA_DIR, f'kingenie_steady_state_{time_str}.{plot_type}')
#
#     fig.write_image(image_filename, format=plot_type)
#
#     if save_html:
#         # Save the plot also as an HTML file for interactive viewing
#         html_filename = os.path.join(DATA_DIR, f'kingenie_steady_state_{time_str}.html')
#         fig.write_html(html_filename)
#     # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
#     return 'Plot saved to: ' + image_filename + '\n'


# @mcp.tool()
# async def plot_kinetic_traces(plot_width: int = 26,
#                               plot_height: int = 24,
#                               plot_type: str = 'png',
#                               font_size: int = 16,
#                               show_grid_x: bool = True,
#                               show_grid_y: bool = True,
#                               marker_size: int = 3,
#                               line_width: int = 2,
#                               split_by_smax_id: bool = False,
#                               max_points_per_plot: int = 1000,
#                               smooth_curves_fit: bool = False,
#                               rolling_window: int = 10,
#                               save_html: bool = False) -> str:
#     """
#     Save a PyKinGenie association/dissociation plot for fittings.
#
#     Requires that the fitting datasets have been generated using the
#     ``initiate_fitting_datasets`` tool. The ligand concentrations are colored by
#     PyKinGenie, and fitted curves are included when fitting results are present.
#
#     Parameters
#     ----------
#     plot_width : int
#         Plot width forwarded to PyKinGenie/Plotly.
#     plot_height : int
#         Plot height forwarded to PyKinGenie/Plotly.
#     plot_type : str
#         Type of the plot to generate (``'png'``, ``'svg'``, ``'jpeg'``).
#     font_size : int
#         Font size for the plot annotations.
#     show_grid_x : bool
#         Whether to show grid lines on the x-axis.
#     show_grid_y : bool
#         Whether to show grid lines on the y-axis.
#     marker_size : int
#         Size of the markers in the plot.
#     line_width : int
#         Width of the lines in the plot.
#     split_by_smax_id : bool
#         If True, splits the plots by Smax ID.
#     max_points_per_plot : int
#         Maximum number of points per plot. If exceeded, data will be subsetted.
#     smooth_curves_fit : bool
#         If True, asks PyKinGenie to smooth fitted curves.
#     rolling_window : int
#         Rolling-window value forwarded to PyKinGenie for smoothing.
#     save_html : bool
#         If True, saves the plot as an HTML file for interactive viewing.
#
#     Returns
#     -------
#     str
#         Message containing the saved image path.
#     """
#
#     fig = pykingenie.plot_association_dissociation(PY_KINETICS,
#                                                    plot_width=plot_width,
#                                                    plot_height=plot_height,
#                                                    plot_type=plot_type,
#                                                    font_size=font_size,
#                                                    show_grid_x=show_grid_x,
#                                                    show_grid_y=show_grid_y,
#                                                    marker_size=marker_size,
#                                                    line_width=line_width,
#                                                    split_by_smax_id=split_by_smax_id,
#                                                    max_points_per_plot=max_points_per_plot,
#                                                    smooth_curves_fit=smooth_curves_fit,
#                                                    rolling_window=rolling_window
#                                                    )
#
#     time_str = current_hour_min_sec()
#     # Combine the data directory and the time string to create a unique filename
#     image_filename = os.path.join(DATA_DIR, f'kingenie_kinetic_traces_{time_str}.{plot_type}')
#
#     fig.write_image(image_filename, format=plot_type)
#
#     if save_html:
#         # Save the plot also as an HTML file for interactive viewing
#         html_filename = os.path.join(DATA_DIR, f'kingenie_kinetic_traces_{time_str}.html')
#         fig.write_html(html_filename)
#     # Return the path to the saved image. Both the image and HTML files are saved in the DATA_DIR.
#     return 'Plot saved to: ' + image_filename + '\n'
