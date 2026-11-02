"""Generation Orchestrator: Coordinates master data generation, lifecycle simulation, and anomaly injection."""

from dataclasses import dataclass
from typing import List

from src.config import ScaleConfig, DEFAULT_SEED
from src.generator.base import GeneratorContext
from src.generator.master_data import generate_asset_types, generate_owners, generate_locations
from src.generator.shipment_generator import generate_shipments
from src.generator.lifecycle_engine import LifecycleEngine
from src.generator.anomaly_injector import AnomalyInjector
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


@dataclass
class GenerationBundle:
    """Container holding all generated entities across the system."""
    asset_types: List[AssetType]
    owners: List[Owner]
    locations: List[Location]
    reusable_assets: List[ReusableAsset]
    shipments: List[Shipment]
    custody_events: List[CustodyEvent]
    return_authorizations: List[ReturnAuthorization]
    inspections: List[Inspection]
    repairs: List[Repair]
    deposit_ledger: List[DepositLedger]
    ground_truth: List[GroundTruthAnomaly]
    seed: int
    scale_name: str


def run_generation(scale_cfg: ScaleConfig, seed: int = DEFAULT_SEED) -> GenerationBundle:
    """Execute end-to-end deterministic data generation workflow."""
    ctx = GeneratorContext(seed=seed)

    # 1. Master Data
    asset_types = generate_asset_types(ctx, scale_cfg.num_asset_types)
    owners = generate_owners(ctx, scale_cfg.num_owners)
    locations = generate_locations(ctx, scale_cfg.num_locations)

    # 2. Shipments
    shipments = generate_shipments(ctx, scale_cfg.num_shipments, locations)

    # 3. Assets and Lifecycle Simulation
    engine = LifecycleEngine(
        ctx=ctx,
        asset_types=asset_types,
        owners=owners,
        locations=locations,
        shipments=shipments,
    )
    (
        assets,
        custody_events,
        rmas,
        inspections,
        repairs,
        deposits,
    ) = engine.run(
        num_assets=scale_cfg.num_assets,
        target_custody_events=scale_cfg.num_custody_events,
    )

    # 4. Inject Labeled Anomalies / Negative Scenarios
    injector = AnomalyInjector(ctx=ctx, locations=locations)
    ground_truth = injector.inject_all(
        count_per_type=scale_cfg.num_anomalies,
        assets=assets,
        events=custody_events,
        rmas=rmas,
        inspections=inspections,
        repairs=repairs,
        deposits=deposits,
    )

    return GenerationBundle(
        asset_types=asset_types,
        owners=owners,
        locations=locations,
        reusable_assets=assets,
        shipments=shipments,
        custody_events=custody_events,
        return_authorizations=rmas,
        inspections=inspections,
        repairs=repairs,
        deposit_ledger=deposits,
        ground_truth=ground_truth,
        seed=seed,
        scale_name=scale_cfg.name,
    )
