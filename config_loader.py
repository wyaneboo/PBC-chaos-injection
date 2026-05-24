"""Compatibility import for the Phase 7 chaos config loader."""

from pbc_chaos.config_loader import (
    ChaosProbabilities,
    ChaosWorkbookConfig,
    config_from_mapping,
    load_config,
)

__all__ = [
    "ChaosProbabilities",
    "ChaosWorkbookConfig",
    "config_from_mapping",
    "load_config",
]

