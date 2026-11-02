"""Core Lifecycle Engine: Simulates asset trips, custody handoffs, RMAs, inspections, repairs, and financial ledger."""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta

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
)
from src.models.enums import (
    LifecycleState,
    ConditionStatus,
    CustodyEventType,
    ActorRole,
    RmaStatus,
    ReturnReason,
    InspectionResult,
    RepairType,
    RepairStatus,
    LedgerTransactionType,
)
from src.generator.base import GeneratorContext


class LifecycleEngine:
    """Simulates realistic operational lifecycles and creates all dependent entities."""

    def __init__(
        self,
        ctx: GeneratorContext,
        asset_types: List[AssetType],
        owners: List[Owner],
        locations: List[Location],
        shipments: List[Shipment],
    ):
        self.ctx = ctx
        self.asset_types = {at.asset_type_id: at for at in asset_types}
        self.asset_type_list = asset_types
        self.owners = {o.owner_id: o for o in owners}
        self.owner_list = owners
        self.locations = {loc.location_id: loc for loc in locations}
        self.location_list = locations
        self.shipments = shipments

        # Pools of actor identifiers
        self.actors = {
            ActorRole.WAREHOUSE_OPERATOR.value: [f"ACT-WH-{i:03d}" for i in range(1, 21)],
            ActorRole.CARRIER.value: [f"ACT-DRV-{i:03d}" for i in range(1, 31)],
            ActorRole.INSPECTOR.value: [f"ACT-QC-{i:03d}" for i in range(1, 15)],
            ActorRole.TECHNICIAN.value: [f"ACT-TECH-{i:03d}" for i in range(1, 15)],
            ActorRole.LOGISTICS_ANALYST.value: [f"ACT-ANA-{i:03d}" for i in range(1, 10)],
            ActorRole.OPERATIONS_MANAGER.value: [f"ACT-MGR-{i:03d}" for i in range(1, 8)],
        }

    def run(
        self,
        num_assets: int,
        target_custody_events: int,
    ) -> Tuple[
        List[ReusableAsset],
        List[CustodyEvent],
        List[ReturnAuthorization],
        List[Inspection],
        List[Repair],
        List[DepositLedger],
    ]:
        """Generate all assets and their simulated operational history."""
        assets: List[ReusableAsset] = []
        custody_events: List[CustodyEvent] = []
        rmas: List[ReturnAuthorization] = []
        inspections: List[Inspection] = []
        repairs: List[Repair] = []
        deposits: List[DepositLedger] = []

        # Calculate average trips per asset to hit the custody target
        avg_events_per_asset = max(2, target_custody_events // num_assets)

        for i in range(num_assets):
            asset_id = self.ctx.asset_seq.next_id()
            a_type = self.ctx.rng.choice(self.asset_type_list)
            owner = self.ctx.rng.choice(self.owner_list)
            home_loc = self.ctx.rng.choice(self.location_list)

            # Asset manufacture date: 6 months to 4 years before sim start
            mfg_days_ago = self.ctx.rng.randint(180, 1460)
            mfg_date = self.ctx.sim_start_time - timedelta(days=mfg_days_ago)
            comm_dt = mfg_date + timedelta(days=self.ctx.rng.randint(7, 30))

            # Simulate trips & events for this asset
            n_events_for_asset = self.ctx.rng.randint(
                max(1, avg_events_per_asset - 2),
                avg_events_per_asset + 2,
            )

            (
                asset_obj,
                asset_events,
                asset_rmas,
                asset_insps,
                asset_reps,
                asset_deps,
            ) = self._simulate_asset_lifecycle(
                asset_id=asset_id,
                a_type=a_type,
                owner=owner,
                home_loc=home_loc,
                mfg_date=mfg_date,
                comm_dt=comm_dt,
                target_events=n_events_for_asset,
            )

            assets.append(asset_obj)
            custody_events.extend(asset_events)
            rmas.extend(asset_rmas)
            inspections.extend(asset_insps)
            repairs.extend(asset_reps)
            deposits.extend(asset_deps)

        return assets, custody_events, rmas, inspections, repairs, deposits

    def _simulate_asset_lifecycle(
        self,
        asset_id: str,
        a_type: AssetType,
        owner: Owner,
        home_loc: Location,
        mfg_date: datetime,
        comm_dt: datetime,
        target_events: int,
    ) -> Tuple[
        ReusableAsset,
        List[CustodyEvent],
        List[ReturnAuthorization],
        List[Inspection],
        List[Repair],
        List[DepositLedger],
    ]:
        events: List[CustodyEvent] = []
        rmas: List[ReturnAuthorization] = []
        inspections: List[Inspection] = []
        repairs: List[Repair] = []
        deposits: List[DepositLedger] = []

        current_loc_id = home_loc.location_id
        current_state = LifecycleState.AT_LOCATION
        condition = ConditionStatus.GOOD
        is_lost = False
        is_damaged = False
        total_trips = 0
        current_balance = 0.0

        current_time = max(comm_dt, self.ctx.sim_start_time)
        event_counter = 1

        standard_deposit = a_type.standard_deposit_amount * owner.deposit_rate_multiplier
        last_dispatch_time = current_time

        while len(events) < target_events and current_time < self.ctx.sim_end_time:
            # Plan a trip
            total_trips += 1
            dest_loc = self.ctx.rng.choice(self.location_list)
            while dest_loc.location_id == current_loc_id:
                dest_loc = self.ctx.rng.choice(self.location_list)

            # Pick a shipment or use local carrier
            shipment = self.ctx.rng.choice(self.shipments)

            # 1. DISPATCH
            dispatch_time = current_time + timedelta(hours=self.ctx.rng.randint(6, 48))
            if dispatch_time >= self.ctx.sim_end_time:
                break
            last_dispatch_time = dispatch_time

            # Deposit initial charge
            current_balance += standard_deposit
            deposits.append(
                DepositLedger(
                    ledger_id=self.ctx.dep_seq.next_id(),
                    asset_id=asset_id,
                    owner_id=owner.owner_id,
                    rma_id=None,
                    transaction_type=LedgerTransactionType.INITIAL_CHARGE.value,
                    amount=round(standard_deposit, 2),
                    balance_after=round(current_balance, 2),
                    timestamp=self.ctx.format_iso(dispatch_time),
                    currency="USD",
                    description=f"Initial custody security deposit for {a_type.name}",
                )
            )

            events.append(
                CustodyEvent(
                    event_id=self.ctx.custody_event_id(asset_id, event_counter),
                    asset_id=asset_id,
                    shipment_id=shipment.shipment_id,
                    from_location_id=current_loc_id,
                    to_location_id=dest_loc.location_id,
                    event_type=CustodyEventType.DISPATCH.value,
                    actor_id=self.ctx.rng.choice(self.actors[ActorRole.WAREHOUSE_OPERATOR.value]),
                    actor_role=ActorRole.WAREHOUSE_OPERATOR.value,
                    timestamp=self.ctx.format_iso(dispatch_time),
                    condition_status=condition.value,
                    is_disputed=False,
                    notes=f"Dispatched via carrier {shipment.carrier_name}",
                )
            )
            event_counter += 1
            current_state = LifecycleState.IN_TRANSIT

            # 2. ARRIVAL (or In-transit/Lost scenario)
            transit_hours = self.ctx.rng.randint(12, 96)
            arrival_time = dispatch_time + timedelta(hours=transit_hours)

            # Check if asset gets lost (approx 1.5% chance)
            if self.ctx.rng.random() < 0.015:
                is_lost = True
                current_state = LifecycleState.LOST
                # Deposit forfeit
                forfeit_amount = -current_balance
                current_balance = 0.0
                deposits.append(
                    DepositLedger(
                        ledger_id=self.ctx.dep_seq.next_id(),
                        asset_id=asset_id,
                        owner_id=owner.owner_id,
                        rma_id=None,
                        transaction_type=LedgerTransactionType.LOSS_FORFEIT.value,
                        amount=round(forfeit_amount, 2),
                        balance_after=0.0,
                        timestamp=self.ctx.format_iso(arrival_time + timedelta(days=90)),
                        currency="USD",
                        description="Security deposit forfeited due to lost asset declaration",
                    )
                )
                break

            if arrival_time >= self.ctx.sim_end_time:
                # Still in transit at end of simulation
                current_state = LifecycleState.IN_TRANSIT
                break

            # Disputed custody handoff (approx 4% chance)
            is_disputed = self.ctx.rng.random() < 0.04
            notes = "Delivered and verified at destination dock"
            if is_disputed:
                notes = "Discrepancy reported: seal intact but package barcode partially scratched"

            events.append(
                CustodyEvent(
                    event_id=self.ctx.custody_event_id(asset_id, event_counter),
                    asset_id=asset_id,
                    shipment_id=shipment.shipment_id,
                    from_location_id=current_loc_id,
                    to_location_id=dest_loc.location_id,
                    event_type=CustodyEventType.ARRIVAL.value if not is_disputed else CustodyEventType.DISPUTED_TRANSFER.value,
                    actor_id=self.ctx.rng.choice(self.actors[ActorRole.CARRIER.value]),
                    actor_role=ActorRole.CARRIER.value,
                    timestamp=self.ctx.format_iso(arrival_time),
                    condition_status=condition.value,
                    is_disputed=is_disputed,
                    notes=notes,
                )
            )
            event_counter += 1
            current_loc_id = dest_loc.location_id
            current_state = LifecycleState.AT_LOCATION
            current_time = arrival_time

            # 3. RETURN WORKFLOW (RMA)
            # Dwell time at customer / recipient (delayed return scenario: 5 to 60 days)
            dwell_days = self.ctx.rng.choices(
                [self.ctx.rng.randint(3, 15), self.ctx.rng.randint(30, 75)],
                weights=[0.85, 0.15],
            )[0]
            rma_request_time = arrival_time + timedelta(days=dwell_days)
            if rma_request_time >= self.ctx.sim_end_time:
                # Still with recipient, pending return
                current_state = LifecycleState.PENDING_RETURN
                break

            rma_id = self.ctx.rma_seq.next_id()
            rma_auth_time = rma_request_time + timedelta(hours=self.ctx.rng.randint(2, 24))
            rma_received_time = rma_auth_time + timedelta(hours=self.ctx.rng.randint(24, 96))

            rma_closed = rma_received_time < self.ctx.sim_end_time
            rma_status = RmaStatus.RECEIVED.value if rma_closed else RmaStatus.IN_TRANSIT.value

            rma_obj = ReturnAuthorization(
                rma_id=rma_id,
                asset_id=asset_id,
                owner_id=owner.owner_id,
                initiator_location_id=current_loc_id,
                target_destination_id=home_loc.location_id,
                rma_status=rma_status,
                requested_at=self.ctx.format_iso(rma_request_time),
                authorized_at=self.ctx.format_iso(rma_auth_time),
                received_at=self.ctx.format_iso(rma_received_time) if rma_closed else None,
                return_reason=self.ctx.rng.choice([
                    ReturnReason.ROUTINE_CYCLE.value,
                    ReturnReason.ROUTINE_CYCLE.value,
                    ReturnReason.END_OF_LEASE.value,
                    ReturnReason.SURPLUS.value,
                    ReturnReason.SUSPECTED_DAMAGE.value,
                ]),
                deposit_reconciled=rma_closed,
            )
            rmas.append(rma_obj)

            if not rma_closed:
                current_state = LifecycleState.IN_TRANSIT
                break

            # Custody Event for Return Receipt
            events.append(
                CustodyEvent(
                    event_id=self.ctx.custody_event_id(asset_id, event_counter),
                    asset_id=asset_id,
                    shipment_id=None,
                    from_location_id=current_loc_id,
                    to_location_id=home_loc.location_id,
                    event_type=CustodyEventType.RETURN_RECEIVED.value,
                    actor_id=self.ctx.rng.choice(self.actors[ActorRole.WAREHOUSE_OPERATOR.value]),
                    actor_role=ActorRole.WAREHOUSE_OPERATOR.value,
                    timestamp=self.ctx.format_iso(rma_received_time),
                    condition_status=condition.value,
                    is_disputed=False,
                    notes=f"Return received at hub under RMA {rma_id}",
                )
            )
            event_counter += 1
            current_loc_id = home_loc.location_id
            current_time = rma_received_time

            # 4. INSPECTION
            insp_time = current_time + timedelta(hours=self.ctx.rng.randint(2, 18))
            if insp_time >= self.ctx.sim_end_time:
                current_state = LifecycleState.UNDER_INSPECTION
                break

            insp_id = self.ctx.insp_seq.next_id()
            insp_roll = self.ctx.rng.random()
            if insp_roll < 0.78:
                cond_result = InspectionResult.PASS.value
                struct_score = self.ctx.rng.randint(85, 100)
                clean_score = self.ctx.rng.randint(80, 100)
                repair_needed = False
                condition = ConditionStatus.GOOD
            elif insp_roll < 0.94:
                cond_result = InspectionResult.MINOR_DAMAGE.value
                struct_score = self.ctx.rng.randint(60, 84)
                clean_score = self.ctx.rng.randint(50, 79)
                repair_needed = True
                condition = ConditionStatus.DAMAGED
                is_damaged = True
            else:
                cond_result = InspectionResult.MAJOR_DAMAGE.value
                struct_score = self.ctx.rng.randint(30, 59)
                clean_score = self.ctx.rng.randint(30, 60)
                repair_needed = True
                condition = ConditionStatus.DAMAGED
                is_damaged = True

            inspections.append(
                Inspection(
                    inspection_id=insp_id,
                    asset_id=asset_id,
                    rma_id=rma_id,
                    location_id=home_loc.location_id,
                    inspector_id=self.ctx.rng.choice(self.actors[ActorRole.INSPECTOR.value]),
                    inspected_at=self.ctx.format_iso(insp_time),
                    condition_result=cond_result,
                    structural_score=struct_score,
                    cleanliness_score=clean_score,
                    repair_recommended=repair_needed,
                    notes=f"Inspection completed with condition {cond_result}",
                )
            )
            current_time = insp_time

            # 5. REPAIR (if repair needed)
            if repair_needed:
                repair_start_time = current_time + timedelta(hours=self.ctx.rng.randint(4, 24))
                if repair_start_time >= self.ctx.sim_end_time:
                    current_state = LifecycleState.UNDER_REPAIR
                    break

                rep_id = self.ctx.repair_seq.next_id()
                rep_duration = timedelta(hours=self.ctx.rng.randint(8, 48))
                rep_complete_time = repair_start_time + rep_duration
                is_rep_done = rep_complete_time < self.ctx.sim_end_time
                rep_cost = round(self.ctx.rng.uniform(25.0, 120.0), 2)

                repairs.append(
                    Repair(
                        repair_id=rep_id,
                        asset_id=asset_id,
                        inspection_id=insp_id,
                        repair_facility_id=home_loc.location_id,
                        technician_id=self.ctx.rng.choice(self.actors[ActorRole.TECHNICIAN.value]),
                        repair_type=self.ctx.rng.choice([
                            RepairType.STRUCTURAL_WELD.value,
                            RepairType.COMPONENT_REPLACEMENT.value,
                            RepairType.SURFACE_CLEAN_REFURBISH.value,
                            RepairType.HARDWARE_FASTENER.value,
                        ]),
                        cost=rep_cost,
                        status=RepairStatus.COMPLETED.value if is_rep_done else RepairStatus.IN_PROGRESS.value,
                        started_at=self.ctx.format_iso(repair_start_time),
                        completed_at=self.ctx.format_iso(rep_complete_time) if is_rep_done else None,
                        parts_replaced="Modular runner base and corner brackets replaced",
                    )
                )

                if is_rep_done:
                    current_time = rep_complete_time
                    condition = ConditionStatus.GOOD
                    is_damaged = False
                    # Deduct partial damage cost from deposit
                    deduction = min(rep_cost, current_balance)
                    current_balance -= deduction
                    deposits.append(
                        DepositLedger(
                            ledger_id=self.ctx.dep_seq.next_id(),
                            asset_id=asset_id,
                            owner_id=owner.owner_id,
                            rma_id=rma_id,
                            transaction_type=LedgerTransactionType.DAMAGE_DEDUCTION.value,
                            amount=round(-deduction, 2),
                            balance_after=round(current_balance, 2),
                            timestamp=self.ctx.format_iso(current_time),
                            currency="USD",
                            description=f"Repair deduction for inspection {insp_id}",
                        )
                    )
                else:
                    current_state = LifecycleState.UNDER_REPAIR
                    break

            # 6. REFUND remaining deposit balance for this cycle
            if current_balance > 0:
                refund_amount = current_balance
                current_balance = 0.0
                deposits.append(
                    DepositLedger(
                        ledger_id=self.ctx.dep_seq.next_id(),
                        asset_id=asset_id,
                        owner_id=owner.owner_id,
                        rma_id=rma_id,
                        transaction_type=LedgerTransactionType.REFUND.value,
                        amount=round(-refund_amount, 2),
                        balance_after=0.0,
                        timestamp=self.ctx.format_iso(current_time + timedelta(hours=2)),
                        currency="USD",
                        description=f"Security deposit fully reconciled and refunded for RMA {rma_id}",
                    )
                )

            current_state = LifecycleState.AT_LOCATION

        # Step 6: Compute Derived Values explicitly from source records
        # 1. Derived current location from latest custody event (or home location if no events)
        if events:
            derived_curr_loc = events[-1].to_location_id
            last_event_time_str = events[-1].timestamp
        else:
            derived_curr_loc = home_loc.location_id
            last_event_time_str = self.ctx.format_iso(comm_dt)

        # 2. Derived days outstanding
        if current_state in (LifecycleState.IN_TRANSIT, LifecycleState.PENDING_RETURN):
            days_out = max(1, (self.ctx.sim_end_time - last_dispatch_time).days)
        elif is_lost:
            days_out = 95
        else:
            days_out = 0

        asset_obj = ReusableAsset(
            asset_id=asset_id,
            asset_type_id=a_type.asset_type_id,
            owner_id=owner.owner_id,
            home_location_id=home_loc.location_id,
            current_location_id=derived_curr_loc,
            lifecycle_state=current_state.value,
            condition_status=condition.value,
            total_trips=total_trips,
            days_outstanding=days_out,
            manufacture_date=self.ctx.format_date_only(mfg_date),
            commissioned_at=self.ctx.format_iso(comm_dt),
            last_event_at=last_event_time_str,
            is_lost=is_lost,
            is_damaged=is_damaged,
        )

        return asset_obj, events, rmas, inspections, repairs, deposits
