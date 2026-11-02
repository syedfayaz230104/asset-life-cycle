"""
Tests for Foreign Key referential integrity across all related entities.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.config import SCALES, DEFAULT_SEED
from src.generator.orchestrator import run_generation


@pytest.fixture(scope="module")
def bundle():
    return run_generation(SCALES["starter"], seed=DEFAULT_SEED)


@pytest.fixture(scope="module")
def valid_ids(bundle):
    return {
        "asset_type_ids": {x.asset_type_id for x in bundle.asset_types},
        "owner_ids":       {x.owner_id for x in bundle.owners},
        "loc_ids":         {x.location_id for x in bundle.locations},
        "asset_ids":       {x.asset_id for x in bundle.reusable_assets},
        "shipment_ids":    {x.shipment_id for x in bundle.shipments},
        "rma_ids":         {x.rma_id for x in bundle.return_authorizations},
        "insp_ids":        {x.inspection_id for x in bundle.inspections},
    }


def test_asset_fk_asset_type(bundle, valid_ids):
    bad = [a.asset_id for a in bundle.reusable_assets if a.asset_type_id not in valid_ids["asset_type_ids"]]
    assert not bad, f"Assets referencing unknown AssetType: {bad[:5]}"


def test_asset_fk_owner(bundle, valid_ids):
    bad = [a.asset_id for a in bundle.reusable_assets if a.owner_id not in valid_ids["owner_ids"]]
    assert not bad, f"Assets referencing unknown Owner: {bad[:5]}"


def test_asset_fk_home_location(bundle, valid_ids):
    bad = [a.asset_id for a in bundle.reusable_assets if a.home_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"Assets referencing unknown home Location: {bad[:5]}"


def test_asset_fk_current_location(bundle, valid_ids):
    bad = [a.asset_id for a in bundle.reusable_assets if a.current_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"Assets referencing unknown current Location: {bad[:5]}"


def test_shipment_fk_origin(bundle, valid_ids):
    bad = [s.shipment_id for s in bundle.shipments if s.origin_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"Shipments referencing unknown origin Location: {bad[:5]}"


def test_shipment_fk_destination(bundle, valid_ids):
    bad = [s.shipment_id for s in bundle.shipments if s.destination_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"Shipments referencing unknown destination Location: {bad[:5]}"


def test_custody_event_fk_asset(bundle, valid_ids):
    bad = [e.event_id for e in bundle.custody_events if e.asset_id not in valid_ids["asset_ids"]]
    assert not bad, f"CustodyEvents referencing unknown Asset: {bad[:5]}"


def test_custody_event_fk_from_location(bundle, valid_ids):
    bad = [e.event_id for e in bundle.custody_events if e.from_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"CustodyEvents referencing unknown from_location: {bad[:5]}"


def test_custody_event_fk_to_location(bundle, valid_ids):
    bad = [e.event_id for e in bundle.custody_events if e.to_location_id not in valid_ids["loc_ids"]]
    assert not bad, f"CustodyEvents referencing unknown to_location: {bad[:5]}"


def test_rma_fk_asset(bundle, valid_ids):
    bad = [r.rma_id for r in bundle.return_authorizations if r.asset_id not in valid_ids["asset_ids"]]
    assert not bad, f"RMAs referencing unknown Asset: {bad[:5]}"


def test_rma_fk_owner(bundle, valid_ids):
    bad = [r.rma_id for r in bundle.return_authorizations if r.owner_id not in valid_ids["owner_ids"]]
    assert not bad, f"RMAs referencing unknown Owner: {bad[:5]}"


def test_inspection_fk_asset(bundle, valid_ids):
    bad = [i.inspection_id for i in bundle.inspections if i.asset_id not in valid_ids["asset_ids"]]
    assert not bad, f"Inspections referencing unknown Asset: {bad[:5]}"


def test_repair_fk_asset(bundle, valid_ids):
    bad = [r.repair_id for r in bundle.repairs if r.asset_id not in valid_ids["asset_ids"]]
    assert not bad, f"Repairs referencing unknown Asset: {bad[:5]}"


def test_deposit_ledger_fk_asset(bundle, valid_ids):
    bad = [d.ledger_id for d in bundle.deposit_ledger if d.asset_id not in valid_ids["asset_ids"]]
    assert not bad, f"DepositLedger referencing unknown Asset: {bad[:5]}"


def test_deposit_ledger_fk_owner(bundle, valid_ids):
    bad = [d.ledger_id for d in bundle.deposit_ledger if d.owner_id not in valid_ids["owner_ids"]]
    assert not bad, f"DepositLedger referencing unknown Owner: {bad[:5]}"
