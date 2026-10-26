import pykingenie
from pykingenie.utils import plotting_xy

from .config import DATA_DIR, DATA_DIR_NO_DATE, EXAMPLE_DATA_DIR


PY_KINETICS = pykingenie.KineticsAnalyzer()

# Reusable settings for the XY plotting tools. Unset fields (None) keep the
# defaults of each pykingenie.utils.plotting_xy helper.
PLOT_CONFIG = plotting_xy.PlotConfig()
AXIS_CONFIG = plotting_xy.AxisConfig()
LAYOUT_CONFIG = plotting_xy.LayoutConfig()
LEGEND_CONFIG = plotting_xy.LegendConfig()
TRACE_CONFIG = plotting_xy.TraceConfig()
