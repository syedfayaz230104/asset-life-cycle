"""
Tests for Primary Key uniqueness across all 10 entities.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.config import SCALES, DEFAULT_SEED
from src.generator.orchestrator import run_generation


@pytest.fixture(scope="module")
def bundle():
    return run_generation(SCALES["starter"], seed=DEFAULT_SEED)


def test_asset_type_pk_unique(bundle):
    ids = [x.asset_type_id for x in bundle.asset_types]
    assert len(ids) == len(set(ids)), "Duplicate AssetType IDs found!"


def test_owner_pk_unique(bundle):
    ids = [x.owner_id for x in bundle.owners]
    assert len(ids) == len(set(ids)), "Duplicate Owner IDs found!"


def test_location_pk_unique(bundle):
    ids = [x.location_id for x in bundle.locations]
    assert len(ids) == len(set(ids)), "Duplicate Location IDs found!"


def test_reusable_asset_pk_unique(bundle):
    ids = [x.asset_id for x in bundle.reusable_assets]
    assert len(ids) == len(set(ids)), "Duplicate ReusableAsset IDs found!"


def test_shipment_pk_unique(bundle):
    ids = [x.shipment_id for x in bundle.shipments]
    assert len(ids) == len(set(ids)), "Duplicate Shipment IDs found!"


def test_custody_event_pk_unique(bundle):
    ids = [x.event_id for x in bundle.custody_events]
    assert len(ids) == len(set(ids)), "Duplicate CustodyEvent IDs found!"


def test_rma_pk_unique(bundle):
    ids = [x.rma_id for x in bundle.return_authorizations]
    assert len(ids) == len(set(ids)), "Duplicate ReturnAuthorization IDs found!"


def test_inspection_pk_unique(bundle):
    ids = [x.inspection_id for x in bundle.inspections]
    assert len(ids) == len(set(ids)), "Duplicate Inspection IDs found!"


def test_repair_pk_unique(bundle):
    ids = [x.repair_id for x in bundle.repairs]
    assert len(ids) == len(set(ids)), "Duplicate Repair IDs found!"


def test_deposit_ledger_pk_unique(bundle):
    ids = [x.ledger_id for x in bundle.deposit_ledger]
    assert len(ids) == len(set(ids)), "Duplicate DepositLedger IDs found!"


def test_ground_truth_pk_unique(bundle):
    ids = [x.anomaly_id for x in bundle.ground_truth]
    assert len(ids) == len(set(ids)), "Duplicate GroundTruthAnomaly IDs found!"
