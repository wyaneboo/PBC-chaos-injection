"""Human workflow residue chaos placeholders."""

from pbc_chaos.chaos.base import BaseChaosInjector


class HumanResidueInjector(BaseChaosInjector):
    name = "human_residue"
    category = "human_residue"
    order = 400
