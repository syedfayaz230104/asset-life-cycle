"""Generator for Master Data: AssetType, Owner, and Location."""

from typing import List, Tuple
from datetime import datetime, timedelta

from src.models.entities import AssetType, Owner, Location
from src.models.enums import (
    AssetCategory,
    MaterialType,
    OwnerType,
    LocationType,
)
from src.generator.base import GeneratorContext, US_CITIES, ENTERPRISE_NAMES


def generate_asset_types(ctx: GeneratorContext, count: int) -> List[AssetType]:
    """Generate deterministic master AssetType catalog."""
    templates = [
        ("Euro Standard Plastic Pallet 1200x800", AssetCategory.PALLET, MaterialType.PLASTIC, 18.5, 1200.0, 45.0, 1825, "Standard reusable returnable heavy plastic pallet"),
        ("North American GMA Heavy Wood Pallet 48x40", AssetCategory.PALLET, MaterialType.WOOD, 22.0, 1500.0, 25.0, 730, "Treated multi-trip hardwood GMA specification pallet"),
        ("Collapsible Bulk Container Tote 45x48x34", AssetCategory.TOTE, MaterialType.PLASTIC, 52.0, 900.0, 150.0, 2190, "Collapsible structural foam industrial shipping tote"),
        ("Insulated Pharma Cold-Chain Shipper 60L", AssetCategory.CONTAINER, MaterialType.COMPOSITE, 14.0, 120.0, 280.0, 1095, "Vacuum insulated temperature-controlled pharmaceutical container"),
        ("Security Roll Cage Container with Wire Mesh", AssetCategory.ROLL_CAGE, MaterialType.STEEL, 48.0, 600.0, 180.0, 2555, "Anti-theft nesting 4-sided steel mesh distribution roll cage"),
        ("Automotive Foldable Steel Stillage Crate", AssetCategory.CRATE, MaterialType.STEEL, 85.0, 2000.0, 320.0, 3650, "Heavy-gauge stackable steel stillage for powertrain components"),
        ("ESD Conductive Electronics Tote Container", AssetCategory.TOTE, MaterialType.PLASTIC, 4.5, 50.0, 35.0, 1460, "Electrostatic discharge protective reusable tote with divider lid"),
        ("Aerospace Aluminum High-Value Avionics Box", AssetCategory.CONTAINER, MaterialType.ALUMINUM, 26.0, 350.0, 450.0, 3650, "Hermetically sealed aluminum container for avionics flight spares"),
        ("Retail Distribution Nestable Attached-Lid Tote", AssetCategory.TOTE, MaterialType.PLASTIC, 3.2, 40.0, 20.0, 1825, "High-density polyethylene nestable distribution tote container"),
        ("Refrigerated Dairy & Beverage Crating Unit", AssetCategory.CRATE, MaterialType.PLASTIC, 2.8, 30.0, 15.0, 1460, "Interlocking reusable crate for fresh dairy and beverage logistics"),
    ]

    asset_types: List[AssetType] = []
    for i in range(count):
        tmpl = templates[i % len(templates)]
        t_id = ctx.asset_type_seq.next_id()
        name = tmpl[0] if i < len(templates) else f"{tmpl[0]} Mk-{i // len(templates) + 1}"
        asset_types.append(
            AssetType(
                asset_type_id=t_id,
                name=name,
                category=tmpl[1].value,
                material=tmpl[2].value,
                tare_weight_kg=tmpl[3],
                max_load_kg=tmpl[4],
                standard_deposit_amount=tmpl[5],
                expected_lifespan_days=tmpl[6],
                description=tmpl[7],
            )
        )
    return asset_types


def generate_owners(ctx: GeneratorContext, count: int) -> List[Owner]:
    """Generate deterministic master Owner records."""
    owner_types = [
        OwnerType.POOL_OPERATOR.value,
        OwnerType.ENTERPRISE.value,
        OwnerType.SUPPLIER.value,
        OwnerType.RETAILER.value,
    ]
    multipliers = [0.85, 1.0, 1.0, 1.15, 1.25]

    owners: List[Owner] = []
    for i in range(count):
        o_id = ctx.owner_seq.next_id()
        base_name = ENTERPRISE_NAMES[i % len(ENTERPRISE_NAMES)]
        suffix = f" Group {i + 1}" if i >= len(ENTERPRISE_NAMES) else ""
        name = f"{base_name}{suffix}"
        clean_slug = name.lower().replace(" ", "-").replace(",", "")
        email = f"logistics-ops@{clean_slug[:20]}.com"
        created_dt = ctx.sim_start_time - timedelta(days=ctx.rng.randint(180, 730))

        owners.append(
            Owner(
                owner_id=o_id,
                name=name,
                owner_type=ctx.rng.choice(owner_types),
                contact_email=email,
                billing_currency="USD",
                deposit_rate_multiplier=ctx.rng.choice(multipliers),
                is_active=True,
                created_at=ctx.format_iso(created_dt),
            )
        )
    return owners


def generate_locations(ctx: GeneratorContext, count: int) -> List[Location]:
    """Generate deterministic physical Locations across the network."""
    loc_types = [
        (LocationType.DISTRIBUTION_CENTER.value, "Regional Distribution Center", 25000),
        (LocationType.WAREHOUSE.value, "Fulfillment Warehouse", 15000),
        (LocationType.SUPPLIER_PLANT.value, "Manufacturing Plant", 10000),
        (LocationType.RETAIL_STORE.value, "Commercial Retail Hub", 3500),
        (LocationType.REPAIR_HUB.value, "Central Maintenance & Refurb Depot", 8000),
        (LocationType.TRANSIT_PORT.value, "Intermodal Port Gateway", 30000),
    ]

    locations: List[Location] = []
    for i in range(count):
        loc_id = ctx.loc_seq.next_id()
        city_info = US_CITIES[i % len(US_CITIES)]
        type_tpl = loc_types[i % len(loc_types)]
        
        name = f"{city_info[0]} {type_tpl[1]} #{i + 1}"
        address = f"{1000 + (i * 123) % 8900} Logistics Blvd, Suite {100 + (i * 10) % 500}"
        
        locations.append(
            Location(
                location_id=loc_id,
                name=name,
                location_type=type_tpl[0],
                address=address,
                city=city_info[0],
                state=city_info[1],
                postal_code=city_info[2],
                capacity_units=type_tpl[2],
                is_active=True,
            )
        )
    return locations
