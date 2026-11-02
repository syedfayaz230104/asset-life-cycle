"""
Tests for lifecycle state machines, date ordering, and ledger arithmetic.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from datetime import datetime
from src.config import SCALES, DEFAULT_SEED
from src.generator.orchestrator import run_generation
from src.models.enums import (
    LifecycleState, ConditionStatus, ShipmentStatus,
    CustodyEventType, ActorRole, RmaStatus, InspectionResult,
    RepairStatus, LedgerTransactionType, AnomalyType,
)


@pytest.fixture(scope="module")
def bundle():
    return run_generation(SCALES["starter"], seed=DEFAULT_SEED)


# ─────────────────────────────────────────────
# Date Ordering
# ─────────────────────────────────────────────

def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", ""))


def test_shipment_dispatch_before_delivery(bundle):
    errors = []
    for s in bundle.shipments:
        if s.delivered_at:
            if _parse(s.dispatched_at) > _parse(s.delivered_at):
                errors.append(s.shipment_id)
    assert not errors, f"Shipments delivered before dispatch: {errors[:5]}"


def test_repair_start_before_completion(bundle):
    errors = []
    for r in bundle.repairs:
        if r.completed_at:
            if _parse(r.started_at) > _parse(r.completed_at):
                errors.append(r.repair_id)
    assert not errors, f"Repairs completed before starting: {errors[:5]}"


def test_rma_authorized_after_requested(bundle):
    # Exclude anomalous RMAs (RETURN_BEFORE_DISPATCH)
    anom_rma_ids = {
        gt.target_record_id for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.RETURN_BEFORE_DISPATCH.value
    }
    errors = []
    for r in bundle.return_authorizations:
        if r.rma_id in anom_rma_ids:
            continue
        if _parse(r.requested_at) > _parse(r.authorized_at):
            errors.append(r.rma_id)
    assert not errors, f"RMAs authorized before requested: {errors[:5]}"


# ─────────────────────────────────────────────
# Lifecycle State Constraints
# ─────────────────────────────────────────────

def test_lost_assets_flagged_correctly(bundle):
    """Assets with lifecycle_state=LOST must also have is_lost=True."""
    errors = [
        a.asset_id for a in bundle.reusable_assets
        if a.lifecycle_state == LifecycleState.LOST.value and not a.is_lost
    ]
    assert not errors, f"LOST assets without is_lost flag: {errors[:5]}"


def test_no_negative_total_trips(bundle):
    """Every asset should have at least 0 trips."""
    bad = [a.asset_id for a in bundle.reusable_assets if a.total_trips < 0]
    assert not bad, f"Assets with negative total_trips: {bad[:5]}"


def test_structural_inspection_score_range(bundle):
    """Inspection structural score must be 0–100."""
    bad = [
        i.inspection_id for i in bundle.inspections
        if not (0 <= i.structural_score <= 100)
    ]
    assert not bad, f"Inspections with out-of-range structural_score: {bad[:5]}"


def test_cleanliness_inspection_score_range(bundle):
    """Inspection cleanliness score must be 0–100."""
    bad = [
        i.inspection_id for i in bundle.inspections
        if not (0 <= i.cleanliness_score <= 100)
    ]
    assert not bad, f"Inspections with out-of-range cleanliness_score: {bad[:5]}"


# ─────────────────────────────────────────────
# Ledger Arithmetic Reconciliation
# ─────────────────────────────────────────────

def test_initial_charges_are_positive(bundle):
    """All INITIAL_CHARGE transactions must have positive amounts."""
    bad = [
        d.ledger_id for d in bundle.deposit_ledger
        if d.transaction_type == LedgerTransactionType.INITIAL_CHARGE.value and d.amount <= 0
    ]
    assert not bad, f"INITIAL_CHARGE entries with non-positive amounts: {bad[:5]}"


def test_refunds_are_negative(bundle):
    """All REFUND transactions must have negative amounts (money going back)."""
    # Exclude anomalous double-refunds (they are still negative, but let's confirm direction)
    anom_dep_ids = {
        gt.target_record_id for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.DEPOSIT_REFUNDED_TWICE.value
    }
    bad = [
        d.ledger_id for d in bundle.deposit_ledger
        if d.transaction_type == LedgerTransactionType.REFUND.value
        and d.ledger_id not in anom_dep_ids
        and d.amount >= 0
    ]
    assert not bad, f"REFUND entries with non-negative amounts: {bad[:5]}"


def test_repair_cost_is_non_negative(bundle):
    """Repair costs must be >= 0."""
    bad = [r.repair_id for r in bundle.repairs if r.cost < 0]
    assert not bad, f"Repairs with negative cost: {bad[:5]}"


# ─────────────────────────────────────────────
# Anomaly Coverage
# ─────────────────────────────────────────────

def test_all_5_anomaly_types_present(bundle):
    """All 5 required edge-case types must be in the ground truth table."""
    required = {e.value for e in AnomalyType}
    present = {gt.issue_type for gt in bundle.ground_truth}
    missing = required - present
    assert not missing, f"Missing required anomaly types: {missing}"


def test_simultaneous_location_anomalies_count(bundle):
    count = sum(
        1 for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.SIMULTANEOUS_LOCATIONS.value
    )
    assert count >= 1, "No SIMULTANEOUS_LOCATIONS anomalies injected"


def test_custody_lacks_actor_anomalies_count(bundle):
    count = sum(
        1 for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.CUSTODY_LACKS_ACTOR.value
    )
    assert count >= 1, "No CUSTODY_LACKS_ACTOR anomalies injected"


def test_repair_without_inspection_anomalies_count(bundle):
    count = sum(
        1 for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.REPAIR_WITHOUT_INSPECTION.value
    )
    assert count >= 1, "No REPAIR_WITHOUT_INSPECTION anomalies injected"


def test_deposit_refunded_twice_anomalies_count(bundle):
    count = sum(
        1 for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.DEPOSIT_REFUNDED_TWICE.value
    )
    assert count >= 1, "No DEPOSIT_REFUNDED_TWICE anomalies injected"


def test_return_before_dispatch_anomalies_count(bundle):
    count = sum(
        1 for gt in bundle.ground_truth
        if gt.issue_type == AnomalyType.RETURN_BEFORE_DISPATCH.value
    )
    assert count >= 1, "No RETURN_BEFORE_DISPATCH anomalies injected"
