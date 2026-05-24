"""Structural workbook chaos placeholders."""

from pbc_chaos.chaos.base import BaseChaosInjector


class StructuralChaosInjector(BaseChaosInjector):
    name = "structural"
    category = "structural"
    order = 100
