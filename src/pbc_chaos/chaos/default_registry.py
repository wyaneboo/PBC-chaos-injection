"""Factory for default chaos injector registry."""

from pbc_chaos.chaos.data_quality import DataQualityChaosInjector
from pbc_chaos.chaos.file_naming import FileNamingChaosInjector
from pbc_chaos.chaos.formatting import FormattingChaosInjector
from pbc_chaos.chaos.formula import FormulaChaosInjector
from pbc_chaos.chaos.human_residue import HumanResidueInjector
from pbc_chaos.chaos.registry import ChaosInjectorRegistry
from pbc_chaos.chaos.semantic import SemanticChaosInjector
from pbc_chaos.chaos.structural import StructuralChaosInjector
from pbc_chaos.chaos.versioning import VersioningChaosInjector


def build_default_chaos_registry() -> ChaosInjectorRegistry:
    registry = ChaosInjectorRegistry()
    for injector in (
        StructuralChaosInjector(),
        SemanticChaosInjector(),
        FormattingChaosInjector(),
        HumanResidueInjector(),
        DataQualityChaosInjector(),
        FormulaChaosInjector(),
        VersioningChaosInjector(),
        FileNamingChaosInjector(),
    ):
        registry.register(injector)
    return registry

