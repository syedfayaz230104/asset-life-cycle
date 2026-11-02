# YottaFlex Reusable Asset Lifecycle Engine

A **100% Python, zero-dependency** synthetic data generator and validation suite for the YottaFlex 72-Hour Code Challenge (Application #7192, Round 2).

It models the end-to-end lifecycle of **reusable packaging, pallets, and equipment** across locations and custody transitions — including full **anomaly injection**, **financial ledger reconciliation**, and **bit-for-bit reproducible generation**.

---

## What This Project Does

| Step | What Happens |
|------|-------------|
| **1** | Defines a data dictionary for all 10 core entities |
| **2** | Generates master data (AssetType, Owner, Location) |
| **3** | Assigns deterministic IDs (`ASSET-0000001`, `RMA-2026-000001`, etc.) |
| **4** | Simulates 20,000 reusable assets and 100,000+ custody events |
| **5** | Injects all 5 required labeled edge cases with isolated Ground Truth |
| **6** | Derives location, outstanding days, and balances from source records |
| **7** | Exports a separate `ground_truth.csv` / `.json` — never mixed into inputs |
| **8** | Runs automated validation: PKs, FKs, enums, dates, lifecycle, ledger |
| **9** | Exports CSV + JSON + SQLite DB + SQL seed script + manifest |
| **10** | Verifies bit-for-bit reproducibility by regenerating with the same seed |

---

## Project Structure

```
yottaflex-asset-lifecycle/
│
├── main.py                        # CLI entry point (generate / verify / stats)
├── requirements.txt               # Only pytest needed (no other dependencies!)
├── pyproject.toml                 # Pytest configuration
│
├── src/
│   ├── config.py                  # Scale profiles and directory paths
│   │
│   ├── models/
│   │   ├── enums.py               # All domain enumerations (16 enums)
│   │   └── entities.py            # All 10 entity dataclasses + GroundTruthAnomaly
│   │
│   ├── database/
│   │   ├── schema.sql             # Full relational DDL with FK constraints & indexes
│   │   └── db_manager.py         # SQLite connection, bulk insert helpers
│   │
│   ├── generator/
│   │   ├── base.py                # Deterministic RNG, ID sequences, reference pools
│   │   ├── master_data.py         # AssetType, Owner, Location generators
│   │   ├── shipment_generator.py  # Shipment transaction generator
│   │   ├── lifecycle_engine.py    # Asset simulation (dispatch → arrival → RMA → inspect → repair → refund)
│   │   ├── anomaly_injector.py    # All 5 edge-case injectors + Ground Truth records
│   │   └── orchestrator.py        # Coordinates all generators into one GenerationBundle
│   │
│   ├── validation/
│   │   └── validator.py           # 7-category automated validation suite
│   │
│   └── export/
│       └── exporter.py            # CSV, JSON, SQLite, SQL dump, manifest, checksums
│
├── tests/
│   ├── test_primary_keys.py       # 11 PK uniqueness tests
│   ├── test_foreign_keys.py       # 15 FK referential integrity tests
│   ├── test_lifecycle_and_ledger.py  # 16 lifecycle, date-order, ledger, anomaly tests
│   └── test_reproducibility.py   # 6 seed reproducibility tests
│
└── exports/                       # Auto-created on first run
    ├── csv/                       # 11 CSV files (one per entity)
    ├── json/                      # 11 JSON files
    ├── sqlite/reusable_assets.db  # Full SQLite database with FK enforcement
    ├── sql/seed_data.sql          # Complete SQL INSERT dump
    ├── validation_summary.json    # Detailed validation results
    └── source_manifest.json       # SHA-256 checksums + provenance metadata
```

---

## Requirements

- **Python 3.10 or higher** (uses standard library only)
- **pytest** (for running tests only)

> No Pandas, no Faker, no SQLAlchemy, no Docker — zero external runtime dependencies.

---

## How to Run

### Step 1 — Clone / Open the Project

```bash
cd yottaflex-asset-lifecycle
```

### Step 2 — Install pytest (only dev dependency)

```bash
pip install pytest
```

### Step 3 — Generate Data (Starter Scale — fast, ~500 assets)

```bash
python main.py generate --scale starter --seed 20261022
```

**Output:**
```
[*] Starting Generation Pipeline...
    - Scale Profile:  STARTER
    - Seed:           20261022
    - Assets Target:  500
    - Events Target:  2,500
[+] Generation completed in 0.08s
[*] Running Step 8 Multi-Entity Validation Suite...
    -> Overall Validation Status: PASS
    -> PK Uniqueness:             PASS
    -> FK Referential Integrity:  PASS
    -> Enum Constraints:          PASS
    -> Date Ordering:             PASS
    -> Location Reconstruction:   PASS
    -> Injected Anomalies:        25 tracked in Ground Truth
```

### Step 4 — Generate Full Scale (20,000 assets, 100,000+ events)

```bash
python main.py generate --scale full --seed 20261022
```

> Takes ~4 seconds. Produces all exports in `exports/`.

### Step 5 — View Operational Metrics

```bash
python main.py stats
```

Shows asset lifecycle states, condition distribution, financial ledger totals,
and all injected anomaly counts by type.

### Step 6 — Run Tests (48 automated tests)

```bash
python -m pytest tests/ -v
```

Expected result: **48 passed**

### Step 7 — Verify Step 10 Reproducibility (bit-for-bit SHA-256 check)

```bash
python main.py verify-reproducibility --scale starter --seed 20261022
```

**Output:**
```
[+] STEP 10 REPRODUCIBILITY VERIFICATION: 100% BIT-FOR-BIT MATCH (PASS)
```

---

## The 10 Core Entities

| # | Entity | ID Format | Description |
|---|--------|-----------|-------------|
| 1 | `AssetType` | `AT-001` | Master catalog of reusable packaging types |
| 2 | `Owner` | `OWN-0001` | Enterprise or pool operator with financial responsibility |
| 3 | `Location` | `LOC-0001` | Physical facility (warehouse, depot, repair hub, port) |
| 4 | `ReusableAsset` | `ASSET-0000001` | Serialized individual asset with lifecycle state |
| 5 | `Shipment` | `SHP-2026-000001` | Carrier movement between origin and destination |
| 6 | `CustodyEvent` | `CUST-<asset-id>-000001` | Append-only audit trail of all handoffs |
| 7 | `ReturnAuthorization` | `RMA-2026-000001` | Return workflow authorization and tracking |
| 8 | `Inspection` | `INSP-2026-000001` | Physical condition assessment on return |
| 9 | `Repair` | `REP-2026-000001` | Maintenance work order for damaged assets |
| 10 | `DepositLedger` | `DEP-2026-000001` | Security deposit charges, refunds, and forfeitures |

---

## The 5 Injected Edge Cases (Ground Truth)

All anomalies are written only to `ground_truth.csv` / `ground_truth.json`.
They are **never leaked into the main entity tables as "correct" data**.

| Anomaly | What Was Injected | Detection Rule |
|---------|-------------------|----------------|
| `SIMULTANEOUS_LOCATIONS` | Asset recorded at two different locations at the same timestamp | Duplicate `(asset_id, timestamp)` with distinct `to_location_id` |
| `RETURN_BEFORE_DISPATCH` | RMA timestamp precedes the earliest dispatch event for that asset | `RMA.requested_at < MIN(custody_events.timestamp)` |
| `DEPOSIT_REFUNDED_TWICE` | Duplicate refund entry causes negative ledger balance | `COUNT(REFUND per asset per RMA) > 1` |
| `REPAIR_WITHOUT_INSPECTION` | Repair closed as COMPLETED without an inspection sign-off | `repairs WHERE status='COMPLETED' AND inspection_id IS NULL` |
| `CUSTODY_LACKS_ACTOR` | Custody handoff missing operator credentials | `custody_events WHERE actor_id IS NULL OR actor_role IS NULL` |

---

## Exported Files

After running `generate`, the `exports/` directory contains:

| File / Directory | Contents |
|---|---|
| `csv/*.csv` | 11 CSV files, one per entity (ready to load into any BI tool) |
| `json/*.json` | 11 JSON files (identical data in JSON format) |
| `sqlite/reusable_assets.db` | SQLite database with FK enforcement (`PRAGMA foreign_keys = ON`) |
| `sql/seed_data.sql` | Full `CREATE TABLE` + `INSERT` dump (portable SQL) |
| `validation_summary.json` | Complete automated validation results with counts |
| `source_manifest.json` | SHA-256 checksums, row counts, seed, provenance statement |

---

## Validation Checks (Step 8)

| Check | What Is Validated |
|-------|------------------|
| **Primary Key Uniqueness** | Every ID is unique across all 11 tables |
| **Foreign Key Integrity** | All child records reference valid parent IDs |
| **Enum Constraints** | All enum fields match their strict domain value set |
| **Date Ordering** | Dispatched < Delivered; Repair start < Repair end |
| **Location Reconstruction** | `current_location_id` derived correctly from event stream |
| **Ledger Reconciliation** | Negative balances traced only to known injected anomalies |
| **Anomaly Coverage** | All 5 required edge-case types present in Ground Truth |

---

## Scale Profiles

| Profile | Assets | Shipments | Custody Events | Runtime |
|---------|--------|-----------|----------------|---------|
| `starter` | 500 | 250 | ~2,500 | < 1 second |
| `full` | 20,000 | 10,000 | ~100,000+ | ~4 seconds |

---

## Design Decisions

- **Zero third-party runtime dependencies** — evaluators can run immediately after `pip install pytest`.
- **Deterministic by design** — Python's `random.Random(seed)` produces identical sequences on any OS.
- **Append-only event ledger** — `CustodyEvent` never overwrites previous state; location and balance are always derived from event history.
- **Ground Truth isolation** — Anomaly records never contaminate main feature tables.
- **SQLite with FK enforcement** — `PRAGMA foreign_keys = ON` ensures relational integrity at the database layer too.

---

## Legal / Data Provenance

This dataset is **100% synthetically generated**. No real company names, personal data,
or confidential information is used. All enterprise names, addresses, and identifiers
are fictional constructs for the purpose of this challenge.

---

## Contact / Questions

As per YottaFlex submission guidelines, contact: **contactus@yottaflex.ai**
