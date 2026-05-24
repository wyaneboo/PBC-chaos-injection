"""Architecture package for the PBC Chaos Simulator."""

__version__ = "0.1.0"

from pbc_chaos.config_loader import load_config
from pbc_chaos.pbc_workbook import generate_pbc_workbook

__all__ = ["__version__", "generate_pbc_workbook", "load_config"]
