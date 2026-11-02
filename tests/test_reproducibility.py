"""
Tests for Step 10 reproducibility: same seed must produce identical data.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import csv, json, hashlib, tempfile
from pathlib import Path
import pytest

from src.config import SCALES, DEFAULT_SEED
from src.generator.orchestrator import run_generation
from src.validation.validator import DataValidator
from src.export.exporter import DataExporter


def _sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle_checksum(bundle) -> dict:
    """Compute deterministic checksums of all entity lists."""
    return {
        "asset_types":           _sha256_str(str(sorted(x.to_dict().items()) for x in bundle.asset_types)),
        "owners":                _sha256_str(str(sorted(x.to_dict().items()) for x in bundle.owners)),
        "locations":             _sha256_str(str(sorted(x.to_dict().items()) for x in bundle.locations)),
        "reusable_assets_count": len(bundle.reusable_assets),
        "custody_events_count":  len(bundle.custody_events),
        "rma_count":             len(bundle.return_authorizations),
        "inspection_count":      len(bundle.inspections),
        "repair_count":          len(bundle.repairs),
        "deposit_count":         len(bundle.deposit_ledger),
        "ground_truth_count":    len(bundle.ground_truth),
    }


@pytest.fixture(scope="module")
def run_a():
    return run_generation(SCALES["starter"], seed=DEFAULT_SEED)


@pytest.fixture(scope="module")
def run_b():
    return run_generation(SCALES["starter"], seed=DEFAULT_SEED)


def test_row_counts_identical(run_a, run_b):
    assert len(run_a.reusable_assets) == len(run_b.reusable_assets)
    assert len(run_a.custody_events) == len(run_b.custody_events)
    assert len(run_a.return_authorizations) == len(run_b.return_authorizations)
    assert len(run_a.inspections) == len(run_b.inspections)
    assert len(run_a.repairs) == len(run_b.repairs)
    assert len(run_a.deposit_ledger) == len(run_b.deposit_ledger)
    assert len(run_a.ground_truth) == len(run_b.ground_truth)


def test_asset_ids_identical(run_a, run_b):
    ids_a = sorted(x.asset_id for x in run_a.reusable_assets)
    ids_b = sorted(x.asset_id for x in run_b.reusable_assets)
    assert ids_a == ids_b, "Asset IDs differ across runs with same seed"


def test_custody_event_ids_identical(run_a, run_b):
    ids_a = sorted(x.event_id for x in run_a.custody_events)
    ids_b = sorted(x.event_id for x in run_b.custody_events)
    assert ids_a == ids_b, "CustodyEvent IDs differ across runs with same seed"


def test_validation_results_identical(run_a, run_b):
    val_a = DataValidator(run_a).run_all()
    val_b = DataValidator(run_b).run_all()
    assert val_a["overall_status"] == val_b["overall_status"] == "PASS"


def test_deposit_amounts_identical(run_a, run_b):
    amounts_a = sorted(d.amount for d in run_a.deposit_ledger)
    amounts_b = sorted(d.amount for d in run_b.deposit_ledger)
    assert amounts_a == amounts_b, "Deposit amounts differ across seeded runs"


def test_different_seed_gives_different_data():
    """Different seed must produce different results."""
    bundle_x = run_generation(SCALES["starter"], seed=12345)
    bundle_y = run_generation(SCALES["starter"], seed=99999)
    ids_x = sorted(x.asset_id for x in bundle_x.reusable_assets)
    ids_y = sorted(x.asset_id for x in bundle_y.reusable_assets)
    # Asset IDs should be the same (sequential), but owner/location assignments differ
    owners_x = sorted(x.owner_id for x in bundle_x.reusable_assets)
    owners_y = sorted(x.owner_id for x in bundle_y.reusable_assets)
    assert owners_x != owners_y, "Different seeds produced identical owner assignments!"
