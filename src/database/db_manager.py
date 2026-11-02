"""Database manager for SQLite storage, schema initialization, and bulk insertion."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.models.entities import (
    AssetType,
    Owner,
    Location,
    ReusableAsset,
    Shipment,
    CustodyEvent,
    ReturnAuthorization,
    Inspection,
    Repair,
    DepositLedger,
    GroundTruthAnomaly,
)


class DatabaseManager:
    """Manages SQLite database connections, schema migrations, and queries."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        # Ensure SQLite enforces foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def init_schema(self, schema_path: Optional[Path] = None):
        """Execute DDL script to create tables and indexes."""
        if schema_path is None:
            schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()
        self.conn.executescript(ddl)
        self.conn.commit()

    def insert_asset_types(self, items: List[AssetType]):
        sql = """
        INSERT INTO asset_types (
            asset_type_id, name, category, material, tare_weight_kg,
            max_load_kg, standard_deposit_amount, expected_lifespan_days, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.asset_type_id, x.name, x.category, x.material, x.tare_weight_kg,
                x.max_load_kg, x.standard_deposit_amount, x.expected_lifespan_days, x.description
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_owners(self, items: List[Owner]):
        sql = """
        INSERT INTO owners (
            owner_id, name, owner_type, contact_email, billing_currency,
            deposit_rate_multiplier, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.owner_id, x.name, x.owner_type, x.contact_email, x.billing_currency,
                x.deposit_rate_multiplier, int(x.is_active), x.created_at
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_locations(self, items: List[Location]):
        sql = """
        INSERT INTO locations (
            location_id, name, location_type, address, city, state, postal_code,
            capacity_units, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.location_id, x.name, x.location_type, x.address, x.city, x.state,
                x.postal_code, x.capacity_units, int(x.is_active)
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_reusable_assets(self, items: List[ReusableAsset]):
        sql = """
        INSERT INTO reusable_assets (
            asset_id, asset_type_id, owner_id, home_location_id, current_location_id,
            lifecycle_state, condition_status, total_trips, days_outstanding,
            manufacture_date, commissioned_at, last_event_at, is_lost, is_damaged
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.asset_id, x.asset_type_id, x.owner_id, x.home_location_id,
                x.current_location_id, x.lifecycle_state, x.condition_status,
                x.total_trips, x.days_outstanding, x.manufacture_date,
                x.commissioned_at, x.last_event_at, int(x.is_lost), int(x.is_damaged)
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_shipments(self, items: List[Shipment]):
        sql = """
        INSERT INTO shipments (
            shipment_id, origin_location_id, destination_location_id, carrier_name,
            shipment_status, dispatched_at, estimated_delivery_at, delivered_at, total_asset_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.shipment_id, x.origin_location_id, x.destination_location_id,
                x.carrier_name, x.shipment_status, x.dispatched_at,
                x.estimated_delivery_at, x.delivered_at, x.total_asset_count
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_custody_events(self, items: List[CustodyEvent]):
        sql = """
        INSERT INTO custody_events (
            event_id, asset_id, shipment_id, from_location_id, to_location_id,
            event_type, actor_id, actor_role, timestamp, condition_status,
            is_disputed, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.event_id, x.asset_id, x.shipment_id, x.from_location_id,
                x.to_location_id, x.event_type, x.actor_id, x.actor_role,
                x.timestamp, x.condition_status, int(x.is_disputed), x.notes
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_return_authorizations(self, items: List[ReturnAuthorization]):
        sql = """
        INSERT INTO return_authorizations (
            rma_id, asset_id, owner_id, initiator_location_id, target_destination_id,
            rma_status, requested_at, authorized_at, received_at, return_reason,
            deposit_reconciled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.rma_id, x.asset_id, x.owner_id, x.initiator_location_id,
                x.target_destination_id, x.rma_status, x.requested_at,
                x.authorized_at, x.received_at, x.return_reason, int(x.deposit_reconciled)
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_inspections(self, items: List[Inspection]):
        sql = """
        INSERT INTO inspections (
            inspection_id, asset_id, rma_id, location_id, inspector_id,
            inspected_at, condition_result, structural_score, cleanliness_score,
            repair_recommended, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.inspection_id, x.asset_id, x.rma_id, x.location_id,
                x.inspector_id, x.inspected_at, x.condition_result,
                x.structural_score, x.cleanliness_score, int(x.repair_recommended), x.notes
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_repairs(self, items: List[Repair]):
        sql = """
        INSERT INTO repairs (
            repair_id, asset_id, inspection_id, repair_facility_id, technician_id,
            repair_type, cost, status, started_at, completed_at, parts_replaced
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.repair_id, x.asset_id, x.inspection_id, x.repair_facility_id,
                x.technician_id, x.repair_type, x.cost, x.status,
                x.started_at, x.completed_at, x.parts_replaced
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_deposit_ledger(self, items: List[DepositLedger]):
        sql = """
        INSERT INTO deposit_ledger (
            ledger_id, asset_id, owner_id, rma_id, transaction_type,
            amount, balance_after, timestamp, currency, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.ledger_id, x.asset_id, x.owner_id, x.rma_id,
                x.transaction_type, x.amount, x.balance_after,
                x.timestamp, x.currency, x.description
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def insert_ground_truth(self, items: List[GroundTruthAnomaly]):
        sql = """
        INSERT INTO ground_truth_anomalies (
            anomaly_id, issue_type, target_entity, target_record_id,
            related_record_id, description, injected_at, detection_rule, expected_decision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                x.anomaly_id, x.issue_type, x.target_entity, x.target_record_id,
                x.related_record_id, x.description, x.injected_at,
                x.detection_rule, x.expected_decision
            )
            for x in items
        ]
        self.conn.executemany(sql, data)
        self.conn.commit()

    def get_table_counts(self) -> Dict[str, int]:
        """Return row counts for all tables."""
        tables = [
            "asset_types",
            "owners",
            "locations",
            "reusable_assets",
            "shipments",
            "custody_events",
            "return_authorizations",
            "inspections",
            "repairs",
            "deposit_ledger",
            "ground_truth_anomalies",
        ]
        counts = {}
        for t in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {t}")
            counts[t] = cursor.fetchone()["cnt"]
        return counts

    def close(self):
        self.conn.close()
