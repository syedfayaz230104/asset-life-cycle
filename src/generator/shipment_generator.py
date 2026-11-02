"""Generator for Shipment transactions."""

from typing import List
from datetime import datetime, timedelta

from src.models.entities import Shipment, Location
from src.models.enums import ShipmentStatus
from src.generator.base import GeneratorContext, CARRIER_NAMES


def generate_shipments(
    ctx: GeneratorContext,
    count: int,
    locations: List[Location],
) -> List[Shipment]:
    """Generate deterministic Shipment master records."""
    shipments: List[Shipment] = []
    loc_ids = [loc.location_id for loc in locations]
    n_locs = len(loc_ids)

    for _ in range(count):
        shp_id = ctx.shipment_seq.next_id()
        orig_idx = ctx.rng.randint(0, n_locs - 1)
        dest_idx = ctx.rng.randint(0, n_locs - 1)
        while dest_idx == orig_idx:
            dest_idx = ctx.rng.randint(0, n_locs - 1)

        orig_id = loc_ids[orig_idx]
        dest_id = loc_ids[dest_idx]
        carrier = ctx.rng.choice(CARRIER_NAMES)

        # Dispatch date during simulation timeline
        dispatch_dt = ctx.random_date_between(
            ctx.sim_start_time,
            ctx.sim_end_time - timedelta(days=5),
        )
        transit_hours = ctx.rng.randint(12, 120)  # 0.5 to 5 days
        est_delivery_dt = dispatch_dt + timedelta(hours=transit_hours)

        # Determine delivery outcome
        # 92% delivered, 8% in-transit
        is_delivered = (est_delivery_dt <= ctx.sim_end_time) and (ctx.rng.random() < 0.92)
        if is_delivered:
            # Delivered with slight jitter (-4h to +24h delay)
            delay_hours = ctx.rng.randint(-4, 24)
            actual_deliv_dt = est_delivery_dt + timedelta(hours=delay_hours)
            if actual_deliv_dt < dispatch_dt + timedelta(hours=4):
                actual_deliv_dt = dispatch_dt + timedelta(hours=6)
            delivered_str = ctx.format_iso(actual_deliv_dt)
            status = ShipmentStatus.DELIVERED.value
        else:
            delivered_str = None
            status = ShipmentStatus.IN_TRANSIT.value

        shipments.append(
            Shipment(
                shipment_id=shp_id,
                origin_location_id=orig_id,
                destination_location_id=dest_id,
                carrier_name=carrier,
                shipment_status=status,
                dispatched_at=ctx.format_iso(dispatch_dt),
                estimated_delivery_at=ctx.format_iso(est_delivery_dt),
                delivered_at=delivered_str,
                total_asset_count=ctx.rng.randint(10, 250),
            )
        )

    return shipments
