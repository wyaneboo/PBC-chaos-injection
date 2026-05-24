"""Filename chaos placeholders."""

from pbc_chaos.chaos.base import BaseChaosInjector


class FileNamingChaosInjector(BaseChaosInjector):
    name = "file_naming"
    category = "file_naming"
    order = 800
