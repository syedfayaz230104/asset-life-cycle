"""Deterministic random helpers, deterministic sequence generators, and date utilities."""

import random
from datetime import datetime, timedelta
from typing import List, Tuple


class DeterministicSequence:
    """Zero-padded deterministic ID generator."""

    def __init__(self, prefix: str, start: int = 1, pad: int = 7):
        self.prefix = prefix
        self.counter = start
        self.pad = pad

    def next_id(self) -> str:
        val = f"{self.prefix}{str(self.counter).zfill(self.pad)}"
        self.counter += 1
        return val


class GeneratorContext:
    """Encapsulates fixed-seed RNG and deterministic ID sequences."""

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

        # Sequences matching exact prompt specifications
        # ASSET-0000001
        self.asset_seq = DeterministicSequence("ASSET-", 1, 7)
        # RMA-2026-000001
        self.rma_seq = DeterministicSequence("RMA-2026-", 1, 6)
        # SHP-2026-000001
        self.shipment_seq = DeterministicSequence("SHP-2026-", 1, 6)
        # REP-2026-000001
        self.repair_seq = DeterministicSequence("REP-2026-", 1, 6)
        # INSP-2026-000001
        self.insp_seq = DeterministicSequence("INSP-2026-", 1, 6)
        # DEP-2026-000001
        self.dep_seq = DeterministicSequence("DEP-2026-", 1, 6)
        # ANOM-000001
        self.anom_seq = DeterministicSequence("ANOM-", 1, 6)
        # Master IDs
        self.asset_type_seq = DeterministicSequence("AT-", 1, 3)
        self.owner_seq = DeterministicSequence("OWN-", 1, 4)
        self.loc_seq = DeterministicSequence("LOC-", 1, 4)

        # Baseline timeline reference: 2026-01-01 to 2026-10-31
        self.sim_start_time = datetime(2026, 1, 1, 8, 0, 0)
        self.sim_end_time = datetime(2026, 10, 31, 23, 59, 59)

    def custody_event_id(self, asset_id: str, seq_num: int) -> str:
        """CUST-<asset-id>-000001 specification."""
        return f"CUST-{asset_id}-{str(seq_num).zfill(6)}"

    def random_date_between(self, start: datetime, end: datetime) -> datetime:
        """Generate a deterministic datetime between two bounds."""
        if start >= end:
            return start
        delta = (end - start).total_seconds()
        offset = self.rng.randint(0, int(delta))
        return start + timedelta(seconds=offset)

    def format_iso(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def format_date_only(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")


# Realistic reference data pools for deterministic assignment
CARRIER_NAMES = [
    "Maersk Intermodal",
    "Apex Global Freight",
    "SwiftTrack Logistics",
    "FedEx Freight Direct",
    "DHL Supply Chain",
    "Echo Global Hub",
    "Schneider National",
    "J.B. Hunt Intermodal",
    "XPO Logistics Express",
    "Penske Dedicated Fleet",
]

US_CITIES: List[Tuple[str, str, str]] = [
    ("Atlanta", "GA", "30301"),
    ("Dallas", "TX", "75201"),
    ("Chicago", "IL", "60601"),
    ("Memphis", "TN", "38101"),
    ("Los Angeles", "CA", "90001"),
    ("Newark", "NJ", "07101"),
    ("Indianapolis", "IN", "46201"),
    ("Columbus", "OH", "43201"),
    ("Seattle", "WA", "98101"),
    ("Kansas City", "MO", "64101"),
    ("Phoenix", "AZ", "85001"),
    ("Charlotte", "NC", "28201"),
    ("Denver", "CO", "80201"),
    ("Savannah", "GA", "31401"),
    ("Houston", "TX", "77001"),
]

ENTERPRISE_NAMES = [
    "OmniRetail Global",
    "GreenPack Logistics Pool",
    "AeroTech Components",
    "FreshField ColdChain",
    "Apex Beverage Distribution",
    "Titan Heavy Equipment",
    "BioPharma ColdBox",
    "EcoPallet Circular Systems",
    "Global Automotive Systems",
    "Vanguard Consumer Goods",
    "Premier Produce Alliance",
    "Pinnacle Industrial Hardware",
]
