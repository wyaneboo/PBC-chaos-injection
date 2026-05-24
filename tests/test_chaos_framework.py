from pathlib import Path

from pbc_chaos.chaos.base import BaseChaosInjector, ChaosResult
from pbc_chaos.chaos.default_registry import build_default_chaos_registry
from pbc_chaos.chaos.engine import ChaosEngine
from pbc_chaos.chaos.mutations import update_workbook_properties
from pbc_chaos.config.settings import settings_from_mapping
from pbc_chaos.core.context import ClientContext, RunContext
from pbc_chaos.core.types import DocumentType
from pbc_chaos.workbook.plan import SheetPlan, WorkbookPlan


class MarkingInjector(BaseChaosInjector):
    name = "marking"
    category = "test"
    order = 10

    def mutate(self, plan, context):
        roll = context.randint(1, 1_000_000)
        event = self.event(
            context,
            "Marked workbook for framework test.",
            details={"roll": roll},
        )
        return ChaosResult(
            plan=update_workbook_properties(plan, marking_roll=roll),
            events=(event,),
        )


class ArOnlyInjector(MarkingInjector):
    name = "ar_only"
    supported_document_types = (DocumentType.AR_AGING,)


def make_settings(*, injectors=None, probabilities=None):
    raw = {
        "run": {"seed": 123, "output_dir": "outputs", "run_name": None},
        "batch": {
            "client_count": 1,
            "financial_years": [2025],
            "locale": "en_MY",
            "currency": "MYR",
        },
        "documents": {"include": ["trial_balance"], "duplicate_versions": True},
        "chaos": {
            "severity": "medium",
            "injectors": injectors or {},
            "probabilities": probabilities or {},
        },
        "relationships": {
            "discrepancy_mode": "controlled",
            "max_trial_balance_gl_difference_pct": 0.02,
            "max_bank_recon_difference_amount": 500,
            "max_payroll_summary_difference_pct": 0.015,
            "max_inventory_summary_difference_pct": 0.03,
        },
        "metadata": {
            "write_manifest": True,
            "write_per_file_sidecars": True,
            "format": "json",
        },
        "validation": {
            "open_workbooks": True,
            "check_metadata_consistency": True,
            "check_controlled_relationships": True,
        },
    }
    return settings_from_mapping(raw)


def make_client_context(settings):
    run = RunContext(
        settings=settings,
        run_id="test-run",
        output_dir=Path("outputs/test-run"),
        seed=settings.run.seed,
    )
    return ClientContext(
        run=run,
        client_id="client_001",
        client_name="Example Sdn Bhd",
        financial_year=2025,
        locale="en_MY",
        currency="MYR",
        seed=456,
    )


def make_plan():
    return WorkbookPlan(
        document_type=DocumentType.TRIAL_BALANCE,
        client_id="client_001",
        financial_year=2025,
        suggested_filename="TB_FINAL.xlsx",
        sheets=(SheetPlan(name="TB"),),
    )


def test_default_chaos_registry_order():
    registry = build_default_chaos_registry()

    assert registry.names() == (
        "structural",
        "semantic",
        "formatting",
        "human_residue",
        "data_quality",
        "formula",
        "versioning",
        "file_naming",
    )


def test_chaos_engine_uses_deterministic_per_injector_randomness():
    settings = make_settings(probabilities={"marking": 1.0})
    context = make_client_context(settings)
    plan = make_plan()

    result_one = ChaosEngine(
        injectors=[MarkingInjector()],
        settings=settings.chaos,
        seed=999,
    ).apply(plan, context)
    result_two = ChaosEngine(
        injectors=[MarkingInjector()],
        settings=settings.chaos,
        seed=999,
    ).apply(plan, context)

    assert result_one.plan.properties == result_two.plan.properties
    assert result_one.events[0].details == result_two.events[0].details
    assert result_one.events[0].injector == "marking"
    assert result_one.events[0].document_type == "trial_balance"
    assert result_one.executions[0].status == "completed"


def test_chaos_engine_skips_disabled_injector():
    settings = make_settings(injectors={"marking": False})
    context = make_client_context(settings)
    plan = make_plan()

    result = ChaosEngine(
        injectors=[MarkingInjector()],
        settings=settings.chaos,
    ).apply(plan, context)

    assert result.plan is plan
    assert result.events == ()
    assert result.executions[0].status == "skipped_disabled"


def test_chaos_engine_skips_probability_gate():
    settings = make_settings(probabilities={"marking": 0.0})
    context = make_client_context(settings)
    plan = make_plan()

    result = ChaosEngine(
        injectors=[MarkingInjector()],
        settings=settings.chaos,
    ).apply(plan, context)

    assert result.plan is plan
    assert result.events == ()
    assert result.executions[0].status == "probability_gate"


def test_chaos_engine_skips_unsupported_document_type():
    settings = make_settings()
    context = make_client_context(settings)
    plan = make_plan()

    result = ChaosEngine(
        injectors=[ArOnlyInjector()],
        settings=settings.chaos,
    ).apply(plan, context)

    assert result.plan is plan
    assert result.events == ()
    assert result.executions[0].status == "skipped_unsupported"

