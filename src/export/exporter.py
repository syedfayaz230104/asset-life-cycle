"""Step 9 Multi-Format Exporter: Exports CSV, JSON, SQL DDL/DML, SQLite DB, Source Manifest, and Validation Summary."""

import csv
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.generator.orchestrator import GenerationBundle
from src.database.db_manager import DatabaseManager
from src.config import CSV_DIR, JSON_DIR, SQL_DIR, SQLITE_DIR, EXPORTS_DIR


class DataExporter:
    """Manages serialization of entities to CSV, JSON, SQL seed script, and SQLite DB."""

    def __init__(self, bundle: GenerationBundle):
        self.bundle = bundle
        self._ensure_dirs()

    def _ensure_dirs(self):
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        JSON_DIR.mkdir(parents=True, exist_ok=True)
        SQL_DIR.mkdir(parents=True, exist_ok=True)
        SQLITE_DIR.mkdir(parents=True, exist_ok=True)

    def export_all(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all exports and generate source manifest."""
        entity_map = {
            "asset_types": [x.to_dict() for x in self.bundle.asset_types],
            "owners": [x.to_dict() for x in self.bundle.owners],
            "locations": [x.to_dict() for x in self.bundle.locations],
            "reusable_assets": [x.to_dict() for x in self.bundle.reusable_assets],
            "shipments": [x.to_dict() for x in self.bundle.shipments],
            "custody_events": [x.to_dict() for x in self.bundle.custody_events],
            "return_authorizations": [x.to_dict() for x in self.bundle.return_authorizations],
            "inspections": [x.to_dict() for x in self.bundle.inspections],
            "repairs": [x.to_dict() for x in self.bundle.repairs],
            "deposit_ledger": [x.to_dict() for x in self.bundle.deposit_ledger],
            "ground_truth": [x.to_dict() for x in self.bundle.ground_truth],
        }

        # 1. Export CSV
        csv_files = {}
        for name, records in entity_map.items():
            path = CSV_DIR / f"{name}.csv"
            self._write_csv(path, records)
            csv_files[name] = str(path)

        # 2. Export JSON
        json_files = {}
        for name, records in entity_map.items():
            path = JSON_DIR / f"{name}.json"
            self._write_json(path, records)
            json_files[name] = str(path)

        # 3. Export to SQLite and SQL seed script
        db_path = SQLITE_DIR / "reusable_assets.db"
        sql_seed_path = SQL_DIR / "seed_data.sql"
        self._populate_sqlite_and_sql_dump(db_path, sql_seed_path)

        # 4. Export Validation Summary
        val_path = EXPORTS_DIR / "validation_summary.json"
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(validation_results, f, indent=2)

        # 5. Generate Checksums and Source Manifest
        manifest = self._generate_manifest(entity_map, val_path)
        manifest_path = EXPORTS_DIR / "source_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {
            "csv_dir": str(CSV_DIR),
            "json_dir": str(JSON_DIR),
            "sqlite_db": str(db_path),
            "sql_seed": str(sql_seed_path),
            "validation_summary": str(val_path),
            "source_manifest": str(manifest_path),
        }

    def _write_csv(self, path: Path, records: List[Dict[str, Any]]):
        if not records:
            return
        fieldnames = list(records[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    def _write_json(self, path: Path, records: List[Dict[str, Any]]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def _populate_sqlite_and_sql_dump(self, db_path: Path, sql_seed_path: Path):
        # Remove old db if exists
        if db_path.exists():
            db_path.unlink()

        db = DatabaseManager(db_path)
        db.init_schema()

        db.insert_asset_types(self.bundle.asset_types)
        db.insert_owners(self.bundle.owners)
        db.insert_locations(self.bundle.locations)
        db.insert_reusable_assets(self.bundle.reusable_assets)
        db.insert_shipments(self.bundle.shipments)
        db.insert_custody_events(self.bundle.custody_events)
        db.insert_return_authorizations(self.bundle.return_authorizations)
        db.insert_inspections(self.bundle.inspections)
        db.insert_repairs(self.bundle.repairs)
        db.insert_deposit_ledger(self.bundle.deposit_ledger)
        db.insert_ground_truth(self.bundle.ground_truth)

        # Write SQL seed script
        with open(sql_seed_path, "w", encoding="utf-8") as f:
            f.write("-- ========================================================\n")
            f.write(f"-- YottaFlex Reusable Asset Seed Data\n")
            f.write(f"-- Generated: {datetime.utcnow().isoformat()}Z | Seed: {self.bundle.seed}\n")
            f.write("-- ========================================================\n\n")
            for line in db.conn.iterdump():
                f.write(f"{line}\n")

        db.close()

    def _generate_manifest(self, entity_map: Dict[str, Any], val_path: Path) -> Dict[str, Any]:
        """Compute SHA256 checksums and metadata manifest."""
        file_checksums = {}
        # Calculate checksums for all CSVs
        for p in CSV_DIR.glob("*.csv"):
            file_checksums[p.name] = self._sha256_file(p)

        row_counts = {name: len(records) for name, records in entity_map.items()}

        return {
            "project": "YottaFlex Reusable Asset Orchestrator",
            "generator_command": f"python main.py generate --scale {self.bundle.scale_name} --seed {self.bundle.seed}",
            "fixed_seed": self.bundle.seed,
            "scale_profile": self.bundle.scale_name,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "row_counts": row_counts,
            "file_checksums_sha256": file_checksums,
            "legal_provenance": "100% synthetically generated deterministic data. No confidential or PII data utilized.",
        }

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
