"""Data models for all 10 core entities plus GroundTruth anomalies."""

from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict


@dataclass
class AssetType:
    """Master definition of a reusable packaging or equipment type."""
    asset_type_id: str             # PK: e.g. AT-001
    name: str                      # Descriptive name
    category: str                  # AssetCategory enum
    material: str                  # MaterialType enum
    tare_weight_kg: float          # Weight empty
    max_load_kg: float             # Load capacity
    standard_deposit_amount: float # Standard deposit charged per cycle in USD
    expected_lifespan_days: int    # Typical operational lifecycle in days
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Owner:
    """Owner/Enterprise entity that retains legal ownership of reusable assets."""
    owner_id: str                  # PK: e.g. OWN-0001
    name: str                      # Organization name
    owner_type: str                # OwnerType enum
    contact_email: str             # Contact email
    billing_currency: str          # e.g. USD
    deposit_rate_multiplier: float # Multiplier on standard deposit
    is_active: bool
    created_at: str                # ISO 8601 timestamp

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Location:
    """Physical facility or node in the supply chain network."""
    location_id: str               # PK: e.g. LOC-0001
    name: str                      # Facility name
    location_type: str             # LocationType enum
    address: str
    city: str
    state: str
    postal_code: str
    capacity_units: int            # Storage capacity in asset units
    is_active: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReusableAsset:
    """Individual serialized asset unit tracked throughout its lifecycle."""
    asset_id: str                  # PK: ASSET-0000001
    asset_type_id: str             # FK -> AssetType
    owner_id: str                  # FK -> Owner
    home_location_id: str          # FK -> Location (Origin Depot)
    current_location_id: str       # FK -> Location (Derived from latest CustodyEvent)
    lifecycle_state: str           # LifecycleState enum
    condition_status: str          # ConditionStatus enum
    total_trips: int               # Cumulative trip counter
    days_outstanding: int          # Derived days since latest dispatch or arrival
    manufacture_date: str          # ISO 8601 date (YYYY-MM-DD)
    commissioned_at: str           # ISO 8601 timestamp
    last_event_at: str             # ISO 8601 timestamp
    is_lost: bool                  # True if exceeded loss threshold or declared lost
    is_damaged: bool               # True if marked damaged pending inspection/repair

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Shipment:
    """Carrier movement connecting origin and destination locations."""
    shipment_id: str               # PK: SHP-2026-000001
    origin_location_id: str        # FK -> Location
    destination_location_id: str   # FK -> Location
    carrier_name: str
    shipment_status: str           # ShipmentStatus enum
    dispatched_at: str             # ISO 8601 timestamp
    estimated_delivery_at: str     # ISO 8601 timestamp
    delivered_at: Optional[str]    # ISO 8601 timestamp (None if in transit)
    total_asset_count: int         # Total items carried

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CustodyEvent:
    """Append-only audit trail recording custody handoffs and location changes."""
    event_id: str                  # PK: CUST-<asset-id>-000001
    asset_id: str                  # FK -> ReusableAsset
    shipment_id: Optional[str]     # FK -> Shipment (optional for local events)
    from_location_id: str          # FK -> Location
    to_location_id: str            # FK -> Location
    event_type: str                # CustodyEventType enum
    actor_id: Optional[str]        # Operator / user identifier (None in injected anomaly)
    actor_role: Optional[str]      # ActorRole enum (None in injected anomaly)
    timestamp: str                 # ISO 8601 timestamp
    condition_status: str          # ConditionStatus enum recorded at handoff
    is_disputed: bool              # True if recipient flagged discrepancy
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReturnAuthorization:
    """Return Merchandise / Packaging Authorization (RMA) tracking asset return workflow."""
    rma_id: str                    # PK: RMA-2026-000001
    asset_id: str                  # FK -> ReusableAsset
    owner_id: str                  # FK -> Owner
    initiator_location_id: str     # FK -> Location (where return originated)
    target_destination_id: str     # FK -> Location (target return hub)
    rma_status: str                # RmaStatus enum
    requested_at: str              # ISO 8601 timestamp
    authorized_at: str             # ISO 8601 timestamp
    received_at: Optional[str]     # ISO 8601 timestamp
    return_reason: str             # ReturnReason enum
    deposit_reconciled: bool       # True if deposit refunded or settled

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Inspection:
    """Formal physical condition assessment upon return or before repair."""
    inspection_id: str             # PK: INSP-2026-000001
    asset_id: str                  # FK -> ReusableAsset
    rma_id: Optional[str]          # FK -> ReturnAuthorization
    location_id: str               # FK -> Location (Inspection Hub)
    inspector_id: str              # User ID of certified inspector
    inspected_at: str              # ISO 8601 timestamp
    condition_result: str          # InspectionResult enum
    structural_score: int          # 0 - 100 rating
    cleanliness_score: int         # 0 - 100 rating
    repair_recommended: bool
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Repair:
    """Work order tracking maintenance, component refurbishment, or repair."""
    repair_id: str                 # PK: REP-2026-000001
    asset_id: str                  # FK -> ReusableAsset
    inspection_id: Optional[str]   # FK -> Inspection (None in injected anomaly)
    repair_facility_id: str        # FK -> Location (Repair Hub)
    technician_id: str
    repair_type: str               # RepairType enum
    cost: float                    # Cost in USD
    status: str                    # RepairStatus enum
    started_at: str                # ISO 8601 timestamp
    completed_at: Optional[str]    # ISO 8601 timestamp
    parts_replaced: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DepositLedger:
    """Financial tracking of asset deposits, refunds, damage deductions, and forfeits."""
    ledger_id: str                 # PK: DEP-2026-000001
    asset_id: str                  # FK -> ReusableAsset
    owner_id: str                  # FK -> Owner
    rma_id: Optional[str]          # FK -> ReturnAuthorization
    transaction_type: str          # LedgerTransactionType enum
    amount: float                  # Signed transaction amount (charge positive, refund negative)
    balance_after: float           # Reconciled running balance for this asset cycle
    timestamp: str                 # ISO 8601 timestamp
    currency: str                  # USD
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GroundTruthAnomaly:
    """Separate ground truth record for injected negative scenarios / anomalies.
    CRITICAL: Kept strictly isolated from core feature sets as per requirement.
    """
    anomaly_id: str                # PK: ANOM-000001
    issue_type: str                # AnomalyType enum
    target_entity: str             # e.g. CustodyEvent, ReturnAuthorization, DepositLedger, Repair
    target_record_id: str          # ID of the anomalous record
    related_record_id: Optional[str] # Secondary record if multi-row conflict
    description: str
    injected_at: str               # ISO 8601 timestamp
    detection_rule: str            # Validation rule that catches this anomaly
    expected_decision: str         # Expected automated action / operational remediation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
