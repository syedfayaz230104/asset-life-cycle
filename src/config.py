"""Configuration and scale settings for the YottaFlex Reusable Asset Lifecycle Engine."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScaleConfig:
    """Scale parameters for data generation."""
    name: str
    num_asset_types: int
    num_owners: int
    num_locations: int
    num_assets: int
    num_shipments: int
    num_custody_events: int
    num_anomalies: int  # count of injected edge cases per type


SCALE_STARTER = ScaleConfig(
    name="starter",
    num_asset_types=5,
    num_owners=8,
    num_locations=15,
    num_assets=500,
    num_shipments=250,
    num_custody_events=2500,
    num_anomalies=5,
)

SCALE_FULL = ScaleConfig(
    name="full",
    num_asset_types=10,
    num_owners=25,
    num_locations=50,
    num_assets=20000,
    num_shipments=10000,
    num_custody_events=100000,
    num_anomalies=25,
)

SCALES = {
    "starter": SCALE_STARTER,
    "full": SCALE_FULL,
}

DEFAULT_SEED = 20261022
BASE_DIR = Path(__file__).resolve().parent.parent
EXPORTS_DIR = BASE_DIR / "exports"
CSV_DIR = EXPORTS_DIR / "csv"
JSON_DIR = EXPORTS_DIR / "json"
SQL_DIR = EXPORTS_DIR / "sql"
SQLITE_DIR = EXPORTS_DIR / "sqlite"
