"""Unified CLI Entry Point for YottaFlex Reusable Asset Lifecycle Engine."""

import sys
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

from src.config import SCALES, DEFAULT_SEED, EXPORTS_DIR, CSV_DIR
from src.generator.orchestrator import run_generation
from src.validation.validator import DataValidator
from src.export.exporter import DataExporter


def print_banner():
    banner = """
======================================================================
  YottaFlex Reusable Asset Lifecycle & Custody Tracking Engine
  Autonomous Supply Chain Data Orchestrator & Validation Suite
======================================================================
    """
    print(banner)


def cmd_generate(args):
    """Generate synthetic lifecycle data, validate integrity, and export files."""
    scale_name = args.scale
    seed = args.seed

    if scale_name not in SCALES:
        print(f"Error: Unknown scale '{scale_name}'. Choose 'starter' or 'full'.")
        sys.exit(1)

    scale_cfg = SCALES[scale_name]
    print(f"[*] Starting Generation Pipeline...")
    print(f"    - Scale Profile:  {scale_cfg.name.upper()}")
    print(f"    - Seed:           {seed}")
    print(f"    - Assets Target:  {scale_cfg.num_assets:,}")
    print(f"    - Events Target:  {scale_cfg.num_custody_events:,}")

    start_time = datetime.now()
    bundle = run_generation(scale_cfg=scale_cfg, seed=seed)
    gen_duration = (datetime.now() - start_time).total_seconds()
    print(f"[+] Generation completed in {gen_duration:.2f}s")

    # Validation
    print(f"[*] Running Step 8 Multi-Entity Validation Suite...")
    validator = DataValidator(bundle)
    val_results = validator.run_all()
    print(f"    -> Overall Validation Status: {val_results['overall_status']}")
    print(f"    -> PK Uniqueness:             {'PASS' if val_results['checks']['primary_keys']['passed'] else 'FAIL'}")
    print(f"    -> FK Referential Integrity:  {'PASS' if val_results['checks']['foreign_keys']['passed'] else 'FAIL'}")
    print(f"    -> Enum Constraints:          {'PASS' if val_results['checks']['enum_constraints']['passed'] else 'FAIL'}")
    print(f"    -> Date Ordering:             {'PASS' if val_results['checks']['date_ordering']['baseline_passed'] else 'FAIL'}")
    print(f"    -> Location Reconstruction:   {'PASS' if val_results['checks']['location_reconstruction']['baseline_passed'] else 'FAIL'}")
    print(f"    -> Injected Anomalies:        {val_results['checks']['anomaly_ground_truth']['total_anomalies_injected']} tracked in Ground Truth")

    # Export
    print(f"[*] Exporting CSV, JSON, SQL seed, and SQLite Database...")
    exporter = DataExporter(bundle)
    export_paths = exporter.export_all(val_results)
    print(f"[+] All artifacts exported successfully:")
    print(f"    - CSV Directory:      {export_paths['csv_dir']}")
    print(f"    - JSON Directory:     {export_paths['json_dir']}")
    print(f"    - SQLite Database:    {export_paths['sqlite_db']}")
    print(f"    - SQL Seed Script:    {export_paths['sql_seed']}")
    print(f"    - Source Manifest:    {export_paths['source_manifest']}")
    print(f"    - Validation Summary: {export_paths['validation_summary']}")

    # Print summary row table
    print("\n" + "=" * 60)
    print(f"{'Entity Table':<25} | {'Row Count':>15}")
    print("-" * 60)
    summary_counts = [
        ("AssetType", len(bundle.asset_types)),
        ("Owner", len(bundle.owners)),
        ("Location", len(bundle.locations)),
        ("ReusableAsset", len(bundle.reusable_assets)),
        ("Shipment", len(bundle.shipments)),
        ("CustodyEvent", len(bundle.custody_events)),
        ("ReturnAuthorization", len(bundle.return_authorizations)),
        ("Inspection", len(bundle.inspections)),
        ("Repair", len(bundle.repairs)),
        ("DepositLedger", len(bundle.deposit_ledger)),
        ("GroundTruthAnomaly", len(bundle.ground_truth)),
    ]
    for name, cnt in summary_counts:
        print(f"{name:<25} | {cnt:>15,}")
    print("=" * 60)
    print(f"[SUCCESS] Dataset generation and verification complete!\n")


def cmd_verify_reproducibility(args):
    """Step 10: Regenerate twice with same seed and compare row counts and checksums."""
    scale_name = args.scale
    seed = args.seed
    scale_cfg = SCALES[scale_name]

    print(f"[*] Executing Step 10 Reproducibility Verification...")
    print(f"    Seed: {seed} | Scale: {scale_name}")

    print("    [1/2] Generating Run A...")
    bundle_a = run_generation(scale_cfg, seed)
    exp_a = DataExporter(bundle_a)
    val_a = DataValidator(bundle_a).run_all()
    exp_a.export_all(val_a)

    checksums_a = {}
    for p in sorted(CSV_DIR.glob("*.csv")):
        checksums_a[p.name] = exp_a._sha256_file(p)

    print("    [2/2] Generating Run B (identical seed)...")
    bundle_b = run_generation(scale_cfg, seed)
    exp_b = DataExporter(bundle_b)
    val_b = DataValidator(bundle_b).run_all()
    exp_b.export_all(val_b)

    checksums_b = {}
    for p in sorted(CSV_DIR.glob("*.csv")):
        checksums_b[p.name] = exp_b._sha256_file(p)

    print("\n" + "=" * 80)
    print(f"{'File Name':<30} | {'Run A SHA256 (Prefix)':<22} | {'Run B Match?':<12}")
    print("-" * 80)

    all_matched = True
    for fname, hash_a in checksums_a.items():
        hash_b = checksums_b.get(fname, "")
        match = (hash_a == hash_b)
        if not match:
            all_matched = False
        print(f"{fname:<30} | {hash_a[:20]}... | {'MATCH (PASS)' if match else 'FAIL':<12}")

    print("=" * 80)
    if all_matched:
        print("[+] STEP 10 REPRODUCIBILITY VERIFICATION: 100% BIT-FOR-BIT MATCH (PASS)")
    else:
        print("[-] REPRODUCIBILITY VERIFICATION FAILED: Hashes did not match!")
        sys.exit(1)


def cmd_stats(args):
    """Display domain metrics and operational insights from generated SQLite database."""
    import sqlite3
    db_path = EXPORTS_DIR / "sqlite" / "reusable_assets.db"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}. Run 'python main.py generate' first.")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print("\n" + "=" * 65)
    print("  OPERATIONAL METRICS & ASSET LIFECYCLE SUMMARY")
    print("=" * 65)

    # Asset state distribution
    print("\n[*] Asset Lifecycle States:")
    rows = conn.execute("SELECT lifecycle_state, COUNT(*) as cnt FROM reusable_assets GROUP BY lifecycle_state ORDER BY cnt DESC").fetchall()
    for r in rows:
        print(f"    - {r['lifecycle_state']:<20}: {r['cnt']:,}")

    # Condition
    print("\n[*] Asset Physical Condition:")
    rows = conn.execute("SELECT condition_status, COUNT(*) as cnt FROM reusable_assets GROUP BY condition_status ORDER BY cnt DESC").fetchall()
    for r in rows:
        print(f"    - {r['condition_status']:<20}: {r['cnt']:,}")

    # Ledger Financials
    print("\n[*] Deposit Ledger Financial Totals (USD):")
    rows = conn.execute("SELECT transaction_type, COUNT(*) as cnt, SUM(amount) as total_amt FROM deposit_ledger GROUP BY transaction_type").fetchall()
    for r in rows:
        print(f"    - {r['transaction_type']:<20}: {r['cnt']:,} txns | Total: ${r['total_amt']:,.2f}")

    # Injected Anomalies
    print("\n[*] Injected Labeled Anomalies (Isolated Ground Truth):")
    rows = conn.execute("SELECT issue_type, COUNT(*) as cnt FROM ground_truth_anomalies GROUP BY issue_type").fetchall()
    for r in rows:
        print(f"    - {r['issue_type']:<28}: {r['cnt']} records")

    conn.close()
    print("\n" + "=" * 65 + "\n")


def main():
    print_banner()
    parser = argparse.ArgumentParser(
        description="YottaFlex Reusable Asset Tracking & Lifecycle Generator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic data & export")
    gen_parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Scale profile: starter (fast, 500 assets) or full (20,000 assets, 100k events)",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic random seed (default: {DEFAULT_SEED})",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # verify-reproducibility
    rep_parser = subparsers.add_parser(
        "verify-reproducibility",
        help="Run Step 10 reproducibility check (regenerates twice & verifies SHA256 hashes)",
    )
    rep_parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Scale profile to use for reproducibility test",
    )
    rep_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Deterministic seed",
    )
    rep_parser.set_defaults(func=cmd_verify_reproducibility)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Display operational metrics from generated database")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
