-- =====================================================================
-- YottaFlex Reusable Asset Orchestrator Relational Schema
-- Standard: SQLite3 with PRAGMA foreign_keys = ON
-- =====================================================================

DROP TABLE IF EXISTS ground_truth_anomalies;
DROP TABLE IF EXISTS deposit_ledger;
DROP TABLE IF EXISTS repairs;
DROP TABLE IF EXISTS inspections;
DROP TABLE IF EXISTS return_authorizations;
DROP TABLE IF EXISTS custody_events;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS reusable_assets;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS owners;
DROP TABLE IF EXISTS asset_types;

-- 1. AssetType (Master Data)
CREATE TABLE asset_types (
    asset_type_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    material TEXT NOT NULL,
    tare_weight_kg REAL NOT NULL,
    max_load_kg REAL NOT NULL,
    standard_deposit_amount REAL NOT NULL,
    expected_lifespan_days INTEGER NOT NULL,
    description TEXT NOT NULL
);

-- 2. Owner (Master Data)
CREATE TABLE owners (
    owner_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    billing_currency TEXT NOT NULL DEFAULT 'USD',
    deposit_rate_multiplier REAL NOT NULL DEFAULT 1.0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 3. Location (Master Data)
CREATE TABLE locations (
    location_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location_type TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    capacity_units INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- 4. ReusableAsset (Core Relational Entity)
CREATE TABLE reusable_assets (
    asset_id TEXT PRIMARY KEY,
    asset_type_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    home_location_id TEXT NOT NULL,
    current_location_id TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    condition_status TEXT NOT NULL,
    total_trips INTEGER NOT NULL DEFAULT 0,
    days_outstanding INTEGER NOT NULL DEFAULT 0,
    manufacture_date TEXT NOT NULL,
    commissioned_at TEXT NOT NULL,
    last_event_at TEXT NOT NULL,
    is_lost INTEGER NOT NULL DEFAULT 0,
    is_damaged INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (asset_type_id) REFERENCES asset_types(asset_type_id),
    FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
    FOREIGN KEY (home_location_id) REFERENCES locations(location_id),
    FOREIGN KEY (current_location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_assets_type ON reusable_assets(asset_type_id);
CREATE INDEX idx_assets_owner ON reusable_assets(owner_id);
CREATE INDEX idx_assets_location ON reusable_assets(current_location_id);
CREATE INDEX idx_assets_state ON reusable_assets(lifecycle_state);

-- 5. Shipment (Master / Transaction Movement)
CREATE TABLE shipments (
    shipment_id TEXT PRIMARY KEY,
    origin_location_id TEXT NOT NULL,
    destination_location_id TEXT NOT NULL,
    carrier_name TEXT NOT NULL,
    shipment_status TEXT NOT NULL,
    dispatched_at TEXT NOT NULL,
    estimated_delivery_at TEXT NOT NULL,
    delivered_at TEXT,
    total_asset_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (origin_location_id) REFERENCES locations(location_id),
    FOREIGN KEY (destination_location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_shipments_origin ON shipments(origin_location_id);
CREATE INDEX idx_shipments_destination ON shipments(destination_location_id);
CREATE INDEX idx_shipments_status ON shipments(shipment_status);

-- 6. CustodyEvent (Append-Only Event Ledger)
CREATE TABLE custody_events (
    event_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    shipment_id TEXT,
    from_location_id TEXT NOT NULL,
    to_location_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT,
    actor_role TEXT,
    timestamp TEXT NOT NULL,
    condition_status TEXT NOT NULL,
    is_disputed INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (from_location_id) REFERENCES locations(location_id),
    FOREIGN KEY (to_location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_custody_asset ON custody_events(asset_id);
CREATE INDEX idx_custody_shipment ON custody_events(shipment_id);
CREATE INDEX idx_custody_timestamp ON custody_events(timestamp);

-- 7. ReturnAuthorization (RMA Lifecycle)
CREATE TABLE return_authorizations (
    rma_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    initiator_location_id TEXT NOT NULL,
    target_destination_id TEXT NOT NULL,
    rma_status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    authorized_at TEXT NOT NULL,
    received_at TEXT,
    return_reason TEXT NOT NULL,
    deposit_reconciled INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id),
    FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
    FOREIGN KEY (initiator_location_id) REFERENCES locations(location_id),
    FOREIGN KEY (target_destination_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_rma_asset ON return_authorizations(asset_id);
CREATE INDEX idx_rma_owner ON return_authorizations(owner_id);

-- 8. Inspection (Quality & Condition Assessment)
CREATE TABLE inspections (
    inspection_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    rma_id TEXT,
    location_id TEXT NOT NULL,
    inspector_id TEXT NOT NULL,
    inspected_at TEXT NOT NULL,
    condition_result TEXT NOT NULL,
    structural_score INTEGER NOT NULL,
    cleanliness_score INTEGER NOT NULL,
    repair_recommended INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id),
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id),
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_insp_asset ON inspections(asset_id);
CREATE INDEX idx_insp_rma ON inspections(rma_id);

-- 9. Repair (Maintenance Work Orders)
CREATE TABLE repairs (
    repair_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    inspection_id TEXT,
    repair_facility_id TEXT NOT NULL,
    technician_id TEXT NOT NULL,
    repair_type TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    parts_replaced TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id),
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id),
    FOREIGN KEY (repair_facility_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_repair_asset ON repairs(asset_id);
CREATE INDEX idx_repair_inspection ON repairs(inspection_id);

-- 10. DepositLedger (Financial Reconciliation)
CREATE TABLE deposit_ledger (
    ledger_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    rma_id TEXT,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    timestamp TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    description TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id),
    FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
    FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id)
);

CREATE INDEX idx_deposit_asset ON deposit_ledger(asset_id);
CREATE INDEX idx_deposit_owner ON deposit_ledger(owner_id);
CREATE INDEX idx_deposit_rma ON deposit_ledger(rma_id);

-- 11. GroundTruthAnomalies (Separate Auditing Table - Isolated from Input Features)
CREATE TABLE ground_truth_anomalies (
    anomaly_id TEXT PRIMARY KEY,
    issue_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_record_id TEXT NOT NULL,
    related_record_id TEXT,
    description TEXT NOT NULL,
    injected_at TEXT NOT NULL,
    detection_rule TEXT NOT NULL,
    expected_decision TEXT NOT NULL
);
