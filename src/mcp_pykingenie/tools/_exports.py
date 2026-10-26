"""MCP tools that read fitting datasets and fitted curves as records.

These tools only read the fitting objects in ``PY_KINETICS``; they never run a
fit or create datasets.
"""

import math
from typing import Any

import numpy as np
from mcp.server.mcpserver.exceptions import ToolError

from mcp_pykingenie.mcp import mcp

from . import _pykingenie as kg

EXPORT_KINDS = ("datasets", "kinetic-curves", "steady-state-curves")


def _has_values(value) -> bool:
    return value is not None and len(value) > 0


def _python_value(value):
    """Convert NumPy scalars to Python and non-finite floats to None."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _trace_records(dataset: str, fit, kind: str) -> list[dict[str, Any]]:
    """Association and dissociation points of one fitting object."""
    raw = kind == "datasets"
    rows = []
    for phase, times_attr, signals_attr in (
        ("Association", "time_assoc_lst", "assoc_lst" if raw else "signal_assoc_fit"),
        ("Dissociation", "time_disso_lst", "disso_lst" if raw else "signal_disso_fit"),
    ):
        times, signals = getattr(fit, times_attr, None), getattr(fit, signals_attr, None)
        if not _has_values(signals):
            continue
        concentrations = getattr(fit, "lig_conc_lst", getattr(fit, "lig_conc", None))
        if times is None or concentrations is None or len(times) != len(signals) or len(concentrations) != len(signals):
            raise ValueError(f"{phase} data has inconsistent trace lengths.")
        groups = getattr(fit, "smax_id", [None] * len(signals))
        if len(groups) != len(signals):
            raise ValueError("Trace and Smax group counts do not match.")
        names = getattr(fit, "names", [])
        unique_groups = np.unique(groups) if any(group is not None for group in groups) else []
        # PyKinGenie usually stores one name per Smax group, not per trace.
        group_names = dict(zip(unique_groups, names, strict=True)) if len(names) == len(unique_groups) else {}
        for trace, (group, concentration, time, signal) in enumerate(
                zip(groups, concentrations, times, signals, strict=True)):
            if signal is None:
                continue  # A partially fitted dataset has no curve for this trace.
            if len(time) != len(signal):
                raise ValueError("Fitted curve time and signal lengths do not match.")
            if group_names:
                name = group_names.get(group)
            else:
                name = names[trace] if len(names) == len(signals) else None
            rows.extend({"Dataset": dataset, "Trace": trace + 1, "ID": name, "Smax_ID": group,
                         "Type": phase, "Time": t, "Signal": y,
                         "Analyte_concentration_micromolar": concentration}
                        for t, y in zip(time, signal, strict=True))
    return rows


def _steady_state_records(dataset: str, fit) -> list[dict[str, Any]]:
    """Fitted steady-state curves of one fitting object."""
    signals = getattr(fit, "signal_ss_fit", None)
    if not _has_values(signals):
        return []
    concentrations = getattr(fit, "lig_conc_lst_per_id", None)
    groups = np.unique(fit.smax_id)
    if concentrations is None or len(concentrations) != len(signals) or len(groups) != len(signals):
        raise ValueError("Steady-state curves have inconsistent group lengths.")
    rows = []
    for group, xs, ys in zip(groups, concentrations, signals, strict=True):
        if len(xs) != len(ys):
            raise ValueError("Steady-state concentrations and signals do not match.")
        rows.extend({"Dataset": dataset, "Smax_ID": group, "Type": "Steady-state",
                     "Analyte_concentration_micromolar": x, "Signal": y}
                    for x, y in zip(xs, ys, strict=True))
    return rows


@mcp.tool()
def get_export_availability() -> dict[str, bool]:
    """
    Report which kinds of data ``get_export_data`` can return.

    This only inspects the existing fitting objects; it never runs a fit.

    Returns
    -------
    dict
        ``datasets``, ``kinetic-curves`` and ``steady-state-curves`` flags.
    """
    fittings = [kg.PY_KINETICS.fittings[name] for name in kg.PY_KINETICS.fittings_names]
    return {
        "datasets": bool(fittings),
        "kinetic-curves": any(_has_values(getattr(fit, field, None)) for fit in fittings
                              for field in ("signal_assoc_fit", "signal_disso_fit")),
        "steady-state-curves": any(_has_values(getattr(fit, "signal_ss_fit", None)) for fit in fittings),
    }


@mcp.tool()
def get_export_data(kind: str) -> list[dict[str, Any]]:
    """
    Return fitting datasets or fitted curves as records, without fitting.

    Parameters
    ----------
    kind : str
        ``'datasets'`` for the measured association and dissociation traces of
        each fitting dataset, ``'kinetic-curves'`` for the fitted kinetic
        curves, or ``'steady-state-curves'`` for the fitted steady-state
        curves.

    Returns
    -------
    list of dict
        One record per point, labeled with ``Dataset`` and ``Smax_ID``. Trace
        records also have ``Trace``, ``ID`` and ``Time``. Values are not
        rounded; non-finite values are null. Empty when nothing is available.
    """
    if kind not in EXPORT_KINDS:
        raise ToolError(f"Unknown data export {kind!r}. Choose one of: {', '.join(EXPORT_KINDS)}.")

    rows = []
    try:
        for dataset in kg.PY_KINETICS.fittings_names:
            fit = kg.PY_KINETICS.fittings[dataset]
            if kind == "steady-state-curves":
                rows.extend(_steady_state_records(dataset, fit))
            else:
                rows.extend(_trace_records(dataset, fit, kind))
    except ValueError as exc:
        raise ToolError(str(exc)) from None

    return [{key: _python_value(value) for key, value in row.items()} for row in rows]
