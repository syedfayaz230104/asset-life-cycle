"""Step 5 Anomaly Injector: Injects labeled negative edge cases and produces separate ground truth."""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta

from src.models.entities import (
    ReusableAsset,
    CustodyEvent,
    ReturnAuthorization,
    Inspection,
    Repair,
    DepositLedger,
    GroundTruthAnomaly,
    Location,
)
from src.models.enums import (
    AnomalyType,
    CustodyEventType,
    LedgerTransactionType,
    RepairStatus,
)
from src.generator.base import GeneratorContext


class AnomalyInjector:
    """Injects exactly the 5 required negative scenarios and tracks them in Ground Truth."""

    def __init__(self, ctx: GeneratorContext, locations: List[Location]):
        self.ctx = ctx
        self.locations = locations
        self.location_ids = [l.location_id for l in locations]

    def inject_all(
        self,
        count_per_type: int,
        assets: List[ReusableAsset],
        events: List[CustodyEvent],
        rmas: List[ReturnAuthorization],
        inspections: List[Inspection],
        repairs: List[Repair],
        deposits: List[DepositLedger],
    ) -> List[GroundTruthAnomaly]:
        """Inject edge cases across the datasets and return isolated ground truth records."""
        ground_truth: List[GroundTruthAnomaly] = []

        # 1. Edge Case: Asset has two simultaneous locations
        anom1 = self._inject_simultaneous_locations(count_per_type, events)
        ground_truth.extend(anom1)

        # 2. Edge Case: Return processed before dispatch
        anom2 = self._inject_return_before_dispatch(count_per_type, rmas, events)
        ground_truth.extend(anom2)

        # 3. Edge Case: Deposit refunded twice
        anom3 = self._inject_deposit_refunded_twice(count_per_type, deposits)
        ground_truth.extend(anom3)

        # 4. Edge Case: Repair closes without inspection
        anom4 = self._inject_repair_without_inspection(count_per_type, repairs, assets)
        ground_truth.extend(anom4)

        # 5. Edge Case: Custody event lacks actor
        anom5 = self._inject_custody_lacks_actor(count_per_type, events)
        ground_truth.extend(anom5)

        return ground_truth

    def _inject_simultaneous_locations(
        self,
        count: int,
        events: List[CustodyEvent],
    ) -> List[GroundTruthAnomaly]:
        """Inject conflicting custody event at the identical timestamp at a second location."""
        anomalies: List[GroundTruthAnomaly] = []
        if not events:
            return anomalies

        # Select candidate events with existing assets
        step = max(1, len(events) // (count + 1))
        chosen_indices = [i * step for i in range(1, count + 1) if i * step < len(events)]

        for idx in chosen_indices:
            base_ev = events[idx]
            # Pick a conflicting location
            conflict_loc = self.ctx.rng.choice(self.location_ids)
            while conflict_loc == base_ev.to_location_id:
                conflict_loc = self.ctx.rng.choice(self.location_ids)

            conflicting_event_id = f"CUST-SIMUL-{self.ctx.rng.randint(100000, 999999)}"
            conflicting_ev = CustodyEvent(
                event_id=conflicting_event_id,
                asset_id=base_ev.asset_id,
                shipment_id=None,
                from_location_id=base_ev.from_location_id,
                to_location_id=conflict_loc,
                event_type=CustodyEventType.ARRIVAL.value,
                actor_id=base_ev.actor_id,
                actor_role=base_ev.actor_role,
                timestamp=base_ev.timestamp,  # EXACT identical timestamp!
                condition_status=base_ev.condition_status,
                is_disputed=True,
                notes="Conflicting duplicate handoff registered at disparate facility",
            )
            events.append(conflicting_ev)

            anom_id = self.ctx.anom_seq.next_id()
            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=anom_id,
                    issue_type=AnomalyType.SIMULTANEOUS_LOCATIONS.value,
                    target_entity="CustodyEvent",
                    target_record_id=conflicting_event_id,
                    related_record_id=base_ev.event_id,
                    description=f"Asset {base_ev.asset_id} recorded at two distinct locations ({base_ev.to_location_id} and {conflict_loc}) at identical timestamp {base_ev.timestamp}",
                    injected_at=base_ev.timestamp,
                    detection_rule="SELECT asset_id, timestamp, COUNT(DISTINCT to_location_id) FROM custody_events GROUP BY asset_id, timestamp HAVING COUNT > 1",
                    expected_decision="Trigger custody integrity quarantine; alert dispatch supervisor to resolve physical possession.",
                )
            )

        return anomalies

    def _inject_return_before_dispatch(
        self,
        count: int,
        rmas: List[ReturnAuthorization],
        events: List[CustodyEvent],
    ) -> List[GroundTruthAnomaly]:
        """Corrupt RMA requested/received dates to precede earliest dispatch event."""
        anomalies: List[GroundTruthAnomaly] = []
        if not rmas:
            return anomalies

        step = max(1, len(rmas) // (count + 1))
        chosen_indices = [i * step for i in range(1, count + 1) if i * step < len(rmas)]

        for idx in chosen_indices:
            rma = rmas[idx]
            # Find earliest event for this asset
            asset_events = [e for e in events if e.asset_id == rma.asset_id]
            if not asset_events:
                continue

            earliest_dt = min(datetime.fromisoformat(e.timestamp.replace("Z", "")) for e in asset_events)
            corrupt_dt = earliest_dt - timedelta(days=self.ctx.rng.randint(5, 30))
            corrupt_iso = self.ctx.format_iso(corrupt_dt)

            rma.requested_at = corrupt_iso
            rma.authorized_at = corrupt_iso
            if rma.received_at:
                rma.received_at = corrupt_iso

            anom_id = self.ctx.anom_seq.next_id()
            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=anom_id,
                    issue_type=AnomalyType.RETURN_BEFORE_DISPATCH.value,
                    target_entity="ReturnAuthorization",
                    target_record_id=rma.rma_id,
                    related_record_id=rma.asset_id,
                    description=f"RMA {rma.rma_id} timestamp {corrupt_iso} precedes earliest custody dispatch timestamp {self.ctx.format_iso(earliest_dt)}",
                    injected_at=corrupt_iso,
                    detection_rule="RMA.requested_at < MIN(custody_events.timestamp WHERE asset_id = RMA.asset_id)",
                    expected_decision="Reject return processing; flag RMA for timestamp synchronization and invoice verification.",
                )
            )

        return anomalies

    def _inject_deposit_refunded_twice(
        self,
        count: int,
        deposits: List[DepositLedger],
    ) -> List[GroundTruthAnomaly]:
        """Inject duplicate refund transaction in deposit ledger, causing negative balance."""
        anomalies: List[GroundTruthAnomaly] = []
        refunds = [d for d in deposits if d.transaction_type == LedgerTransactionType.REFUND.value]
        if not refunds:
            return anomalies

        step = max(1, len(refunds) // (count + 1))
        chosen = [refunds[i * step] for i in range(1, count + 1) if i * step < len(refunds)]

        for ref in chosen:
            dup_id = self.ctx.dep_seq.next_id()
            ref_dt = datetime.fromisoformat(ref.timestamp.replace("Z", "")) + timedelta(hours=1)
            corrupt_balance = round(ref.balance_after + ref.amount, 2)  # ref.amount is negative

            dup_entry = DepositLedger(
                ledger_id=dup_id,
                asset_id=ref.asset_id,
                owner_id=ref.owner_id,
                rma_id=ref.rma_id,
                transaction_type=LedgerTransactionType.REFUND.value,
                amount=ref.amount,
                balance_after=corrupt_balance,
                timestamp=self.ctx.format_iso(ref_dt),
                currency="USD",
                description=f"DUPLICATE REFUND ERROR: Double settlement applied for RMA {ref.rma_id}",
            )
            deposits.append(dup_entry)

            anom_id = self.ctx.anom_seq.next_id()
            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=anom_id,
                    issue_type=AnomalyType.DEPOSIT_REFUNDED_TWICE.value,
                    target_entity="DepositLedger",
                    target_record_id=dup_id,
                    related_record_id=ref.ledger_id,
                    description=f"Deposit ledger entry {dup_id} is a redundant second refund for RMA {ref.rma_id}, balance went negative ({corrupt_balance})",
                    injected_at=self.ctx.format_iso(ref_dt),
                    detection_rule="SELECT asset_id, rma_id, COUNT(*) FROM deposit_ledger WHERE transaction_type = 'REFUND' GROUP BY asset_id, rma_id HAVING COUNT > 1",
                    expected_decision="Freeze automated disbursement; initiate financial ledger reversal and journal correction.",
                )
            )

        return anomalies

    def _inject_repair_without_inspection(
        self,
        count: int,
        repairs: List[Repair],
        assets: List[ReusableAsset],
    ) -> List[GroundTruthAnomaly]:
        """Create or alter repair records that close without preceding inspection."""
        anomalies: List[GroundTruthAnomaly] = []
        if not repairs:
            return anomalies

        step = max(1, len(repairs) // (count + 1))
        chosen = [repairs[i * step] for i in range(1, count + 1) if i * step < len(repairs)]

        for rep in chosen:
            old_insp_id = rep.inspection_id
            rep.inspection_id = None  # Remove foreign key to inspection
            rep.status = RepairStatus.COMPLETED.value
            rep.parts_replaced = "UNAUTHORIZED REPAIR: Completed without certified inspection sign-off"

            anom_id = self.ctx.anom_seq.next_id()
            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=anom_id,
                    issue_type=AnomalyType.REPAIR_WITHOUT_INSPECTION.value,
                    target_entity="Repair",
                    target_record_id=rep.repair_id,
                    related_record_id=old_insp_id,
                    description=f"Repair order {rep.repair_id} closed as COMPLETED without a valid mandatory inspection reference",
                    injected_at=rep.started_at,
                    detection_rule="SELECT repair_id FROM repairs WHERE status = 'COMPLETED' AND inspection_id IS NULL",
                    expected_decision="Quarantine repaired asset; mandate secondary physical quality audit before release into active pool.",
                )
            )

        return anomalies

    def _inject_custody_lacks_actor(
        self,
        count: int,
        events: List[CustodyEvent],
    ) -> List[GroundTruthAnomaly]:
        """Nullify actor_id and actor_role on selected custody events to simulate audit breach."""
        anomalies: List[GroundTruthAnomaly] = []
        if not events:
            return anomalies

        step = max(1, len(events) // (count + 1))
        chosen_indices = [i * step for i in range(1, count + 1) if i * step < len(events)]

        for idx in chosen_indices:
            ev = events[idx]
            ev.actor_id = None
            ev.actor_role = None
            ev.notes = "UNVERIFIED HANDOFF: Missing driver/operator biometric or digital signature"

            anom_id = self.ctx.anom_seq.next_id()
            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=anom_id,
                    issue_type=AnomalyType.CUSTODY_LACKS_ACTOR.value,
                    target_entity="CustodyEvent",
                    target_record_id=ev.event_id,
                    related_record_id=ev.asset_id,
                    description=f"Custody event {ev.event_id} lacks authenticated actor credentials (actor_id and actor_role are NULL)",
                    injected_at=ev.timestamp,
                    detection_rule="SELECT event_id FROM custody_events WHERE actor_id IS NULL OR actor_role IS NULL",
                    expected_decision="Trigger security compliance incident; request carrier driver manifest and facility CCTV log audit.",
                )
            )

        return anomalies
