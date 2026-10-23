"""MCP tools for the XY plotting helpers of PyKinGenie.

The plots are produced by :mod:`pykingenie.utils.plotting_xy`, which takes its
settings from reusable dataclasses (``PlotConfig``, ``AxisConfig``,
``LayoutConfig``, ``LegendConfig`` and ``TraceConfig``). One instance of each
is kept in :mod:`mcp_pykingenie.server` and shared by every XY plot tool, so
the ``update_*_config`` tools change the appearance of all following plots.
"""

import inspect
import json
import os
from dataclasses import asdict, fields, replace
from functools import wraps
from typing import Any

import pandas as pd
from mcp.server.mcpserver.exceptions import ToolError
from pykingenie.utils import plotting_xy

from ..mcp import mcp
from ..server import AXIS_CONFIG, LAYOUT_CONFIG, LEGEND_CONFIG, PLOT_CONFIG, TRACE_CONFIG
from . import _pykingenie as kg

XY_IMAGE_FORMATS = {"png", "jpeg", "jpg", "webp", "svg", "pdf"}
XY_RANGE_FIELDS = ("x_range", "y_range", "x_bounds", "y_bounds")


def xy_tool():
    """
    Register an MCP tool that reports invalid settings back to the client.

    Without the conversion, ``ValueError`` messages from the plotting
    dataclasses are hidden behind a generic tool error.

    Returns
    -------
    Callable
        Decorator that registers a function as an MCP tool.
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except (ValueError, TypeError) as exc:
                    raise ToolError(str(exc)) from exc
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except (ValueError, TypeError) as exc:
                    raise ToolError(str(exc)) from exc

        return mcp.tool()(wrapper)

    return decorator


def _update_config(config, **changes) -> dict[str, Any]:
    """
    Update a shared plotting dataclass in place with the non-None values.

    The changes are validated by the dataclass before the shared instance is
    modified, so an invalid value leaves the current configuration untouched.

    Parameters
    ----------
    config : dataclass
        One of the shared XY configuration instances.
    **changes : Any
        Field values to update. ``None`` values are ignored, and an empty list
        clears a range or bounds field.

    Returns
    -------
    dict
        The updated configuration.
    """
    changes = {key: value for key, value in changes.items() if value is not None}
    for key in XY_RANGE_FIELDS:
        if isinstance(changes.get(key), list):
            # An empty list clears the range.
            changes[key] = tuple(changes[key]) or None

    validated = replace(config, **changes)
    for field in fields(config):
        setattr(config, field.name, getattr(validated, field.name))

    return asdict(config)


def reset_xy_configs() -> None:
    """Restore every shared XY configuration to the PyKinGenie defaults."""
    for config in (PLOT_CONFIG, AXIS_CONFIG, LAYOUT_CONFIG, LEGEND_CONFIG, TRACE_CONFIG):
        default = type(config)()
        for field in fields(config):
            setattr(config, field.name, getattr(default, field.name))


def _save_xy_figure(fig, base_name: str, save_html: bool) -> str:
    """
    Save an XY chart or grid in ``DATA_DIR`` using ``PLOT_CONFIG.plot_type``.

    Parameters
    ----------
    fig : xy.Chart or xy.facets.FacetGrid
        Figure returned by a ``pykingenie.utils.plotting_xy`` helper.
    base_name : str
        File name prefix. A time stamp and the extension are appended.
    save_html : bool
        If True, also save a standalone interactive HTML file.

    Returns
    -------
    str
        Message containing the saved image path.
    """
    plot_type = (PLOT_CONFIG.plot_type or "png").lower()
    time_str = kg.current_hour_min_sec()

    image_filename = os.path.join(kg.DATA_DIR, f"{base_name}_{time_str}.{plot_type}")
    fig.write_image(image_filename)

    if save_html:
        # Save the plot also as an HTML file for interactive viewing
        html_filename = os.path.join(kg.DATA_DIR, f"{base_name}_{time_str}.html")
        fig.to_html(html_filename)

    return "Plot saved to: " + image_filename + "\n"


@xy_tool()
def get_xy_plot_configs() -> dict[str, dict[str, Any]]:
    """
    Show the current settings used by the XY plotting tools.

    Fields set to ``None`` keep the defaults of each plot, for example the
    plot size or the axis labels.

    Returns
    -------
    dict
        The plot, axis, layout, legend and trace configurations.
    """
    return {
        "plot_config": asdict(PLOT_CONFIG),
        "axis_config": asdict(AXIS_CONFIG),
        "layout_config": asdict(LAYOUT_CONFIG),
        "legend_config": asdict(LEGEND_CONFIG),
        "trace_config": asdict(TRACE_CONFIG),
    }


@xy_tool()
def reset_xy_plot_configs() -> str:
    """
    Reset every XY plotting configuration to the PyKinGenie defaults.

    Returns
    -------
    str
        Confirmation message.
    """
    reset_xy_configs()
    return "XY plot configurations reset to defaults."


@xy_tool()
def update_xy_plot_config(
    plot_width: int | None = None,
    plot_height: int | None = None,
    plot_type: str | None = None,
    font_size: float | None = None,
    title: str | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
) -> dict[str, Any]:
    """
    Edit the general settings of the XY plots.

    Only the provided parameters are changed; the others keep their current
    value. Use ``reset_xy_plot_configs`` to go back to the defaults.

    Parameters
    ----------
    plot_width : int | None
        Width of the plot in pixels.
    plot_height : int | None
        Height of the plot in pixels.
    plot_type : str | None
        Format of the saved image: ``'png'``, ``'jpeg'``, ``'webp'``,
        ``'svg'`` or ``'pdf'``.
    font_size : float | None
        Font size of titles, axis labels and ticks.
    title : str | None
        Main title of the plot. An empty string hides the title.
    x_range : list[float] | None
        Initial x-axis range in data units, for example ``[0, 1000]``.
        Pass ``[]`` to remove it. The range is shared by all XY plots, so it
        must suit the plot being made (e.g. positive values for the
        logarithmic concentration axis of the steady-state plot).
    y_range : list[float] | None
        Initial y-axis range in data units. Pass ``[]`` to remove it.

    Returns
    -------
    dict
        The updated plot configuration.
    """
    if plot_type is not None and plot_type.lower() not in XY_IMAGE_FORMATS:
        raise ValueError(f"plot_type must be one of: {', '.join(sorted(XY_IMAGE_FORMATS))}.")

    return _update_config(
        PLOT_CONFIG,
        plot_width=plot_width,
        plot_height=plot_height,
        plot_type=plot_type.lower() if plot_type else None,
        font_size=font_size,
        title=title,
        x_range=x_range,
        y_range=y_range,
    )


@xy_tool()
def update_xy_axis_config(
    showgrid_x: bool | None = None,
    showgrid_y: bool | None = None,
    n_x_axis_ticks: int | None = None,
    n_y_axis_ticks: int | None = None,
    axis_linewidth: float | None = None,
    axis_tickwidth: float | None = None,
    axis_gridwidth: float | None = None,
    tick_length: float | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    x_scale: str | None = None,
    y_scale: str | None = None,
    reverse_x: bool | None = None,
    reverse_y: bool | None = None,
    x_bounds: list[float] | str | None = None,
    y_bounds: list[float] | str | None = None,
) -> dict[str, Any]:
    """
    Edit the axis settings of the XY plots.

    Only the provided parameters are changed; the others keep their current
    value.

    Parameters
    ----------
    showgrid_x : bool | None
        If True, show the x-axis grid lines.
    showgrid_y : bool | None
        If True, show the y-axis grid lines.
    n_x_axis_ticks : int | None
        Approximate number of ticks on the x-axis.
    n_y_axis_ticks : int | None
        Approximate number of ticks on the y-axis.
    axis_linewidth : float | None
        Width of the axis lines in pixels.
    axis_tickwidth : float | None
        Width of the axis ticks in pixels.
    axis_gridwidth : float | None
        Width of the grid lines in pixels.
    tick_length : float | None
        Length of the axis ticks in pixels.
    x_label : str | None
        Label of the x-axis.
    y_label : str | None
        Label of the y-axis.
    x_scale : str | None
        Scale of the x-axis: ``'linear'``, ``'log'``, ``'symlog'`` or ``'time'``.
    y_scale : str | None
        Scale of the y-axis: ``'linear'``, ``'log'``, ``'symlog'`` or ``'time'``.
    reverse_x : bool | None
        If True, reverse the x-axis.
    reverse_y : bool | None
        If True, reverse the y-axis.
    x_bounds : list[float] | str | None
        Limits for panning/zooming the x-axis in the interactive HTML, as
        ``[min, max]`` or ``'data'`` to stay within the observations.
        Pass ``[]`` to remove them.
    y_bounds : list[float] | str | None
        Limits for panning/zooming the y-axis, as ``[min, max]`` or ``'data'``.
        Pass ``[]`` to remove them.

    Returns
    -------
    dict
        The updated axis configuration.
    """
    return _update_config(
        AXIS_CONFIG,
        showgrid_x=showgrid_x,
        showgrid_y=showgrid_y,
        n_x_axis_ticks=n_x_axis_ticks,
        n_y_axis_ticks=n_y_axis_ticks,
        axis_linewidth=axis_linewidth,
        axis_tickwidth=axis_tickwidth,
        axis_gridwidth=axis_gridwidth,
        tick_length=tick_length,
        x_label=x_label,
        y_label=y_label,
        x_scale=x_scale,
        y_scale=y_scale,
        reverse_x=reverse_x,
        reverse_y=reverse_y,
        x_bounds=x_bounds,
        y_bounds=y_bounds,
    )


@xy_tool()
def update_xy_layout_config(
    stacked: bool | None = None,
    ncols: int | None = None,
    vertical_spacing: float | None = None,
    gap: int | None = None,
    shared_xaxes: bool | None = None,
    shared_yaxes: bool | None = None,
    show_subplot_titles: bool | None = None,
    outer_labels: bool | None = None,
    extra_padding_y_label: float | None = None,
    split_by_smax_id: bool | None = None,
) -> dict[str, Any]:
    """
    Edit the subplot layout of the XY plots with several panels.

    Applies to ``plot_traces_with_all_steps_xy``, ``plot_steady_state_xy``
    and ``plot_kinetic_traces_xy``. Only the provided parameters are changed.

    Parameters
    ----------
    stacked : bool | None
        If True, place all panels in a single column.
    ncols : int | None
        Number of panel columns.
    vertical_spacing : float | None
        Spacing between panel rows as a fraction of the plot height (0 to 1).
    gap : int | None
        Spacing between panels in pixels. Overrides ``vertical_spacing``.
    shared_xaxes : bool | None
        If True, all panels start with the same x-axis range.
    shared_yaxes : bool | None
        If True, all panels start with the same y-axis range.
    show_subplot_titles : bool | None
        If True, show the title of each panel.
    outer_labels : bool | None
        If True, only show axis labels on the outer panels.
    extra_padding_y_label : float | None
        Extra space for the y-axis label in pixels.
    split_by_smax_id : bool | None
        If True, the kinetic traces plot uses one panel per Smax ID.

    Returns
    -------
    dict
        The updated layout configuration.
    """
    return _update_config(
        LAYOUT_CONFIG,
        stacked=stacked,
        ncols=ncols,
        vertical_spacing=vertical_spacing,
        gap=gap,
        shared_xaxes=shared_xaxes,
        shared_yaxes=shared_yaxes,
        show_subplot_titles=show_subplot_titles,
        outer_labels=outer_labels,
        extra_padding_y_label=extra_padding_y_label,
        split_by_smax_id=split_by_smax_id,
    )


@xy_tool()
def update_xy_legend_config(
    show: bool | None = None,
    loc: str | None = None,
    ncols: int | None = None,
    title: str | None = None,
    font_size: float | None = None,
    toggle: bool | None = None,
    highlight: bool | None = None,
) -> dict[str, Any]:
    """
    Edit the legend settings of the XY plots.

    Only the provided parameters are changed; the others keep their current
    value.

    Parameters
    ----------
    show : bool | None
        If True, show the legend.
    loc : str | None
        Legend position, for example ``'upper right'`` or ``'lower left'``.
    ncols : int | None
        Number of legend columns.
    title : str | None
        Legend title.
    font_size : float | None
        Font size of the legend labels.
    toggle : bool | None
        If True, clicking a legend entry hides/shows it in the interactive HTML.
    highlight : bool | None
        If True, hovering a legend entry highlights it in the interactive HTML.

    Returns
    -------
    dict
        The updated legend configuration.
    """
    return _update_config(
        LEGEND_CONFIG,
        show=show,
        loc=loc,
        ncols=ncols,
        title=title,
        font_size=font_size,
        toggle=toggle,
        highlight=highlight,
    )


@xy_tool()
def update_xy_trace_config(
    marker_size: float | None = None,
    line_width: float | None = None,
    opacity: float | None = None,
    fit_color: str | None = None,
    fit_line_width: float | None = None,
    exact_lines: bool | None = None,
    max_points: int | None = None,
    show_fit: bool | None = None,
    smooth_curves: bool | None = None,
    rolling_window: float | None = None,
) -> dict[str, Any]:
    """
    Edit how data points and fitted curves are drawn in the XY plots.

    Only the provided parameters are changed; the others keep their current
    value.

    Parameters
    ----------
    marker_size : float | None
        Size of the markers. Use 0 to hide them.
    line_width : float | None
        Width of the data lines. Use 0 to hide them.
    opacity : float | None
        Opacity of the data, between 0 and 1.
    fit_color : str | None
        Color of the fitted curves, e.g. ``'black'`` or ``'#FF5733'``.
    fit_line_width : float | None
        Width of the fitted curves.
    exact_lines : bool | None
        If True, the sensor traces connect every displayed sample instead of
        using the faster automatic line simplification.
    max_points : int | None
        Sampling budget for raw traces: total points for the sensor traces
        plot, or points per Smax group for the kinetic traces plot.
    show_fit : bool | None
        If True, overlay fitted curves on the steady-state and kinetic plots.
    smooth_curves : bool | None
        If True, median-smooth the kinetic observations (display only).
    rolling_window : float | None
        Smoothing window in seconds, used when ``smooth_curves`` is True.

    Returns
    -------
    dict
        The updated trace configuration.
    """
    return _update_config(
        TRACE_CONFIG,
        marker_size=marker_size,
        line_width=line_width,
        opacity=opacity,
        fit_color=fit_color,
        fit_line_width=fit_line_width,
        exact_lines=exact_lines,
        max_points=max_points,
        show_fit=show_fit,
        smooth_curves=smooth_curves,
        rolling_window=rolling_window,
    )


@xy_tool()
def plot_sample_plate_info_xy(experiment_id: str = '1', save_html: bool = False) -> str:
    """
    Save an XY sample-plate layout plot for one experiment.

    The plot is produced by :func:`pykingenie.utils.plotting_xy.plot_plate_info`
    with the shared XY configurations, and saved in ``DATA_DIR`` using the
    format set in the plot configuration (``'png'`` by default).

    Parameters
    ----------
    experiment_id : str
        The name or 1-based index of the experiment to plot.
    save_html : bool
        If True, also saves an interactive HTML file.

    Returns
    -------
    str
        Message containing the saved image path.
    """
    experiment_name = kg.resolve_experiment_name(experiment_id)
    if experiment_name is None:
        return f"Experiment with index {experiment_id} not found in kingenie."

    fig = plotting_xy.plot_plate_info(
        kg.PY_KINETICS,
        experiment_name,
        plot_config=PLOT_CONFIG,
        axis_config=AXIS_CONFIG,
        legend_config=LEGEND_CONFIG,
        trace_config=TRACE_CONFIG,
    )

    return _save_xy_figure(fig, f"sample_plate_info_xy_{experiment_name}", save_html)


@xy_tool()
async def plot_traces_with_all_steps_xy(
    legends_df: list[dict[str, Any]] | str | None = None,
    save_html: bool = False,
) -> str:
    """
    Save an XY plot with all loaded trace steps, one panel per experiment.

    The plot is produced by :func:`pykingenie.utils.plotting_xy.plot_traces_all`
    with the shared XY configurations. It includes baseline, loading,
    association, dissociation, and regeneration segments.

    Parameters
    ----------
    legends_df : list[dict[str, Any]] | str | None
        Legend table records from ``get_legends_table``, with the columns
        ``Internal_ID``, ``Color``, ``Legend`` and ``Show``. Use ``Show`` to
        select the sensors to plot. If None, the default table is used.
    save_html : bool
        If True, also saves an interactive HTML file.

    Returns
    -------
    str
        Message containing the saved image path.
    """
    if not legends_df:
        legends_df = kg.get_legends_table()

    if isinstance(legends_df, str):
        legends_df = json.loads(legends_df)

    legends_df = pd.DataFrame(legends_df)

    fig = plotting_xy.plot_traces_all(
        kg.PY_KINETICS,
        legends_df,
        plot_config=PLOT_CONFIG,
        axis_config=AXIS_CONFIG,
        layout_config=LAYOUT_CONFIG,
        legend_config=LEGEND_CONFIG,
        trace_config=TRACE_CONFIG,
    )

    return _save_xy_figure(fig, "kingenie_traces_xy", save_html)


@xy_tool()
async def plot_steady_state_xy(save_html: bool = False) -> str:
    """
    Save an XY steady-state plot for the generated fitting datasets.

    The plot is produced by :func:`pykingenie.utils.plotting_xy.plot_steady_state`
    with the shared XY configurations. Requires ``initiate_fitting_datasets``.
    Fitted curves are shown unless ``show_fit`` was set to False with
    ``update_xy_trace_config``.

    Parameters
    ----------
    save_html : bool
        If True, also saves an interactive HTML file.

    Returns
    -------
    str
        Message containing the saved image path.
    """
    trace_config = TRACE_CONFIG
    if trace_config.show_fit is None:
        trace_config = replace(trace_config, show_fit=True)

    fig = plotting_xy.plot_steady_state(
        kg.PY_KINETICS,
        plot_config=PLOT_CONFIG,
        axis_config=AXIS_CONFIG,
        layout_config=LAYOUT_CONFIG,
        legend_config=LEGEND_CONFIG,
        trace_config=trace_config,
    )

    return _save_xy_figure(fig, "kingenie_steady_state_xy", save_html)


@xy_tool()
async def plot_kinetic_traces_xy(save_html: bool = False) -> str:
    """
    Save an XY association/dissociation plot for the fitting datasets.

    The plot is produced by
    :func:`pykingenie.utils.plotting_xy.plot_association_dissociation` with the
    shared XY configurations. Requires ``initiate_fitting_datasets``. Traces are
    colored by ligand concentration, and fitted curves are included when
    fitting results are present.

    Parameters
    ----------
    save_html : bool
        If True, also saves an interactive HTML file.

    Returns
    -------
    str
        Message containing the saved image path.
    """
    fig = plotting_xy.plot_association_dissociation(
        kg.PY_KINETICS,
        plot_config=PLOT_CONFIG,
        axis_config=AXIS_CONFIG,
        layout_config=LAYOUT_CONFIG,
        legend_config=LEGEND_CONFIG,
        trace_config=TRACE_CONFIG,
    )

    return _save_xy_figure(fig, "kingenie_kinetic_traces_xy", save_html)
