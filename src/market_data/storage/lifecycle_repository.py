"""SQLite persistence for Treasury-instrument operational lifecycle records."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Protocol, Sequence, Tuple, runtime_checkable

from market_data.models.enums import (
    AuctionValueUnit,
    CandidateOrigin,
    InstrumentLifecycleStatus,
    InstrumentMatchMethod,
    ProviderName,
    TreasuryInstrumentFamily,
)
from market_data.models.exceptions import RepositoryIntegrityError, StorageError
from market_data.models.instrument_lifecycle import (
    ActivationEvidence,
    InstrumentLifecycleDecision,
    SourceField,
    TreasuryInstrumentCandidate,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS instrument_lifecycle (
    source_id                  TEXT PRIMARY KEY,
    origin                     TEXT NOT NULL,
    description                TEXT NOT NULL,
    official_ticker            TEXT,
    instrument_family          TEXT,
    currency                   TEXT,
    maturity_date              TEXT,
    auction_date               TEXT NOT NULL,
    issue_action               TEXT,
    source_url                 TEXT,
    source_title               TEXT NOT NULL,
    source_fields_json         TEXT NOT NULL,
    discovered_at              TEXT NOT NULL,
    manual_reference           TEXT,
    lifecycle_status           TEXT NOT NULL,
    match_method               TEXT NOT NULL,
    matched_ticker             TEXT,
    activation_provider        TEXT,
    activation_market_date     TEXT,
    activation_retrieved_at    TEXT,
    evaluated_at               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lifecycle_status
    ON instrument_lifecycle (lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_lifecycle_matched_ticker
    ON instrument_lifecycle (matched_ticker);
"""


@runtime_checkable
class InstrumentLifecycleRepository(Protocol):
    """Persistence contract for idempotent lifecycle synchronization."""

    def initialize(self) -> None:
        ...

    def save_decisions(
        self, decisions: Sequence[InstrumentLifecycleDecision]
    ) -> int:
        ...

    def get_all(self) -> Tuple[InstrumentLifecycleDecision, ...]:
        ...

    def get_by_source_id(
        self, source_id: str
    ) -> Optional[InstrumentLifecycleDecision]:
        ...


def _fields_to_json(fields: Tuple[SourceField, ...]) -> str:
    data = [
        {
            "header": field.header,
            "raw_value": field.raw_value,
            "decimal_value": (
                None if field.decimal_value is None else str(field.decimal_value)
            ),
            "unit": None if field.unit is None else field.unit.value,
        }
        for field in fields
    ]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _fields_from_json(raw: str) -> Tuple[SourceField, ...]:
    try:
        data = json.loads(raw)
        return tuple(
            SourceField(
                header=item["header"],
                raw_value=item["raw_value"],
                decimal_value=(
                    None
                    if item["decimal_value"] is None
                    else Decimal(item["decimal_value"])
                ),
                unit=(
                    None
                    if item["unit"] is None
                    else AuctionValueUnit(item["unit"])
                ),
            )
            for item in data
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RepositoryIntegrityError(
            "Stored lifecycle source_fields_json is invalid"
        ) from exc


class SqliteLifecycleRepository:
    """Store lifecycle records separately from quote history in SQLite."""

    def __init__(self, database_path: str):
        try:
            self._conn = sqlite3.connect(database_path)
            self._conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:
            raise StorageError("Cannot open lifecycle database: {}".format(exc)) from exc

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SqliteLifecycleRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def initialize(self) -> None:
        try:
            with self._conn:
                self._conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise StorageError(
                "Cannot initialize lifecycle schema: {}".format(exc)
            ) from exc

    def _values(self, decision: InstrumentLifecycleDecision) -> Tuple:
        candidate = decision.candidate
        evidence = decision.activation_evidence
        return (
            candidate.source_id,
            candidate.origin.value,
            candidate.description,
            candidate.ticker,
            (
                None
                if candidate.instrument_family is None
                else candidate.instrument_family.value
            ),
            candidate.currency,
            None if candidate.maturity_date is None else candidate.maturity_date.isoformat(),
            candidate.auction_date.isoformat(),
            candidate.issue_action,
            candidate.source_url,
            candidate.source_title,
            _fields_to_json(candidate.source_fields),
            candidate.discovered_at.isoformat(),
            candidate.manual_reference,
            decision.status.value,
            decision.match_method.value,
            decision.matched_ticker,
            None if evidence is None else evidence.provider.value,
            None if evidence is None else evidence.market_date.isoformat(),
            None if evidence is None else evidence.retrieved_at.isoformat(),
            decision.evaluated_at.isoformat(),
        )

    def save_decisions(
        self, decisions: Sequence[InstrumentLifecycleDecision]
    ) -> int:
        if not decisions:
            return 0
        columns = (
            "source_id", "origin", "description", "official_ticker",
            "instrument_family", "currency", "maturity_date", "auction_date",
            "issue_action", "source_url", "source_title", "source_fields_json",
            "discovered_at", "manual_reference", "lifecycle_status",
            "match_method", "matched_ticker", "activation_provider",
            "activation_market_date", "activation_retrieved_at", "evaluated_at",
        )
        placeholders = ", ".join(["?"] * len(columns))
        sql = "INSERT OR REPLACE INTO instrument_lifecycle ({}) VALUES ({})".format(
            ", ".join(columns), placeholders
        )
        try:
            with self._conn:
                self._conn.executemany(sql, [self._values(item) for item in decisions])
            return len(decisions)
        except sqlite3.Error as exc:
            raise RepositoryIntegrityError(
                "Failed to persist lifecycle records: {}".format(exc)
            ) from exc

    def _row_to_decision(self, row: sqlite3.Row) -> InstrumentLifecycleDecision:
        data = dict(row)
        candidate = TreasuryInstrumentCandidate(
            source_id=data["source_id"],
            origin=CandidateOrigin(data["origin"]),
            description=data["description"],
            ticker=data["official_ticker"],
            instrument_family=(
                None
                if data["instrument_family"] is None
                else TreasuryInstrumentFamily(data["instrument_family"])
            ),
            currency=data["currency"],
            maturity_date=(
                None
                if data["maturity_date"] is None
                else date.fromisoformat(data["maturity_date"])
            ),
            auction_date=date.fromisoformat(data["auction_date"]),
            issue_action=data["issue_action"],
            source_url=data["source_url"],
            source_title=data["source_title"],
            source_fields=_fields_from_json(data["source_fields_json"]),
            discovered_at=datetime.fromisoformat(data["discovered_at"]),
            manual_reference=data["manual_reference"],
        )
        evidence = None
        if data["activation_provider"] is not None:
            evidence = ActivationEvidence(
                ticker=data["matched_ticker"],
                provider=ProviderName(data["activation_provider"]),
                market_date=date.fromisoformat(data["activation_market_date"]),
                retrieved_at=datetime.fromisoformat(data["activation_retrieved_at"]),
            )
        return InstrumentLifecycleDecision(
            candidate=candidate,
            status=InstrumentLifecycleStatus(data["lifecycle_status"]),
            match_method=InstrumentMatchMethod(data["match_method"]),
            matched_ticker=data["matched_ticker"],
            activation_evidence=evidence,
            evaluated_at=datetime.fromisoformat(data["evaluated_at"]),
        )

    def get_all(self) -> Tuple[InstrumentLifecycleDecision, ...]:
        try:
            rows = self._conn.execute(
                "SELECT * FROM instrument_lifecycle ORDER BY auction_date, source_id"
            ).fetchall()
            return tuple(self._row_to_decision(row) for row in rows)
        except sqlite3.Error as exc:
            raise StorageError("Lifecycle query failed: {}".format(exc)) from exc

    def get_by_source_id(
        self, source_id: str
    ) -> Optional[InstrumentLifecycleDecision]:
        try:
            row = self._conn.execute(
                "SELECT * FROM instrument_lifecycle WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            return None if row is None else self._row_to_decision(row)
        except sqlite3.Error as exc:
            raise StorageError("Lifecycle query failed: {}".format(exc)) from exc
