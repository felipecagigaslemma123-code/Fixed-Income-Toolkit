"""Normalize official Treasury result HTML without applying financial logic."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from market_data.instrument_identity import (
    canonical_text,
    infer_currency,
    infer_instrument_family,
    normalize_ticker,
    parse_explicit_maturity_date,
)
from market_data.models.enums import AuctionValueUnit, CandidateOrigin
from market_data.models.exceptions import NormalizationError
from market_data.models.instrument_lifecycle import (
    SourceField,
    TreasuryInstrumentCandidate,
    TreasuryResultNotice,
)

_NUMBER_RE = re.compile(r"(?<![A-Z0-9])[-+]?\d+(?:\.\d{3})*(?:,\d+)?(?![A-Z0-9])")
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{2,15}$")


def _attrs(values: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
    return {key: value or "" for key, value in values}


class _NewsListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.notices: List[Tuple[str, str, str]] = []
        self._anchor_depth = 0
        self._href: Optional[str] = None
        self._datetime: Optional[str] = None
        self._text: List[str] = []
        self._heading_depth = 0
        self._heading_text: List[str] = []

    def handle_starttag(
        self, tag: str, attrs: List[Tuple[str, Optional[str]]]
    ) -> None:
        values = _attrs(attrs)
        if tag == "a" and self._anchor_depth == 0:
            self._anchor_depth = 1
            self._href = values.get("href")
            self._datetime = None
            self._text = []
            self._heading_text = []
        elif self._anchor_depth:
            self._anchor_depth += 1
        if tag == "h3" and self._anchor_depth:
            self._heading_depth = 1
        elif self._heading_depth:
            self._heading_depth += 1
        if tag == "time" and self._anchor_depth:
            self._datetime = values.get("datetime")

    def handle_endtag(self, tag: str) -> None:
        if not self._anchor_depth:
            return
        if self._heading_depth:
            self._heading_depth -= 1
        self._anchor_depth -= 1
        if tag == "a" and self._anchor_depth == 0 and self._href:
            title_parts = self._heading_text or self._text
            text = " ".join(" ".join(title_parts).split())
            self.notices.append((self._href, self._datetime or "", text))
            self._href = None
            self._datetime = None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_depth:
            self._text.append(data)
        if self._heading_depth:
            self._heading_text.append(data)


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self.published_at: Optional[str] = None
        self.tables: List[Tuple[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]] = []
        self._in_table = False
        self._headers: List[str] = []
        self._rows: List[Tuple[str, ...]] = []
        self._row: Optional[List[str]] = None
        self._row_is_header = False
        self._cell: Optional[List[str]] = None

    def handle_starttag(
        self, tag: str, attrs: List[Tuple[str, Optional[str]]]
    ) -> None:
        values = _attrs(attrs)
        if tag == "meta":
            prop = values.get("property")
            if prop == "og:title":
                self.title = values.get("content") or self.title
            elif prop == "article:published_time":
                self.published_at = values.get("content") or self.published_at
        elif tag == "table":
            self._in_table = True
            self._headers = []
            self._rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
            self._row_is_header = False
        elif tag in {"th", "td"} and self._in_table and self._row is not None:
            self._cell = []
            if tag == "th":
                self._row_is_header = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            value = " ".join(" ".join(self._cell).split())
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row_is_header and not self._headers:
                self._headers = self._row
            elif not self._row_is_header and any(self._row):
                self._rows.append(tuple(self._row))
            self._row = None
        elif tag == "table" and self._in_table:
            self.tables.append((tuple(self._headers), tuple(self._rows)))
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_result_notices(raw_html: str, listing_url: str) -> Tuple[TreasuryResultNotice, ...]:
    """Return auction-result notices from the official finance-news listing."""
    parser = _NewsListingParser()
    parser.feed(raw_html)
    notices = []
    seen = set()
    for href, raw_date, title in parser.notices:
        normalized_title = canonical_text(title)
        if "RESULTADO" not in normalized_title or "LICITACI" not in normalized_title:
            continue
        try:
            publication_date = date.fromisoformat(raw_date[:10])
        except ValueError as exc:
            raise NormalizationError(
                "Treasury result notice is missing a valid publication date"
            ) from exc
        url = urljoin(listing_url, href)
        if url in seen:
            continue
        seen.add(url)
        notices.append(
            TreasuryResultNotice(
                title=title,
                publication_date=publication_date,
                url=url,
            )
        )
    return tuple(notices)


def _extract_ticker(description: str) -> Optional[str]:
    for group in re.findall(r"\(([^()]*)\)", canonical_text(description)):
        candidate = re.split(r"\s*[-–—]\s*", group, maxsplit=1)[0].strip()
        if candidate in {"NUEVA", "NUEVO", "REAPERTURA"}:
            continue
        normalized = normalize_ticker(candidate)
        if normalized and _TICKER_RE.fullmatch(normalized):
            return normalized
    return None


def _extract_issue_action(description: str) -> Optional[str]:
    value = canonical_text(description)
    if "REAPERTURA" in value:
        return "REAPERTURA"
    if "NUEVA" in value or "NUEVO" in value:
        return "NUEVA"
    return None


def _source_number(raw_value: str) -> Optional[Decimal]:
    """Parse one unambiguous localized source number, preserving its scale."""
    matches = _NUMBER_RE.findall(canonical_text(raw_value))
    if len(matches) != 1:
        return None
    token = matches[0]
    remainder = canonical_text(raw_value).replace(token, "", 1)
    remainder = re.sub(r"\b(?:USD|ARS)\b", "", remainder)
    remainder = remainder.replace("U$S", "").replace("US$", "").replace("$", "")
    remainder = re.sub(r"[\s%*()]+", "", remainder)
    if remainder:
        return None
    normalized = token.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _source_unit(header: str, raw_value: str) -> Optional[AuctionValueUnit]:
    value = canonical_text("{} {}".format(header, raw_value))
    if "%" in raw_value or any(label in value for label in ("TNA", "TIREA", "TEM", "TASA")):
        return AuctionValueUnit.PERCENT
    if "USD" in value or "U$S" in value or "US$" in value:
        return AuctionValueUnit.USD
    if "$" in raw_value or "ARS" in value:
        return AuctionValueUnit.ARS
    if _source_number(raw_value) is not None:
        return AuctionValueUnit.REPORTED_NUMBER
    return None


def parse_result_candidates(
    raw_html: str,
    source_url: str,
    retrieved_at: datetime,
) -> Tuple[TreasuryInstrumentCandidate, ...]:
    """Extract national-Treasury rows with complete source-table evidence."""
    parser = _ArticleParser()
    parser.feed(raw_html)
    if not parser.published_at:
        raise NormalizationError("Treasury result article has no publication timestamp")
    try:
        publication_date = date.fromisoformat(parser.published_at[:10])
    except ValueError as exc:
        raise NormalizationError(
            "Treasury result article has an invalid publication timestamp"
        ) from exc
    source_title = parser.title or "Treasury auction result"

    candidates = []
    for table_index, (headers, rows) in enumerate(parser.tables, start=1):
        for row_index, row in enumerate(rows, start=1):
            instrument_index = next(
                (
                    index
                    for index, cell in enumerate(row)
                    if any(
                        label in canonical_text(cell)
                        for label in (
                            "LETRA DEL TESORO NACIONAL",
                            "BONO DEL TESORO NACIONAL",
                        )
                    )
                ),
                None,
            )
            if instrument_index is None:
                continue
            description = row[instrument_index]
            source_fields = []
            for column_index, raw_value in enumerate(row):
                header = (
                    headers[column_index]
                    if column_index < len(headers) and headers[column_index]
                    else "column_{}".format(column_index + 1)
                )
                decimal_value = None
                unit = None
                if column_index != instrument_index:
                    decimal_value = _source_number(raw_value)
                    unit = _source_unit(header, raw_value)
                source_fields.append(
                    SourceField(
                        header=header,
                        raw_value=raw_value,
                        decimal_value=decimal_value,
                        unit=unit,
                    )
                )
            candidates.append(
                TreasuryInstrumentCandidate(
                    source_id="{}#table-{}-row-{}".format(
                        source_url, table_index, row_index
                    ),
                    origin=CandidateOrigin.TREASURY_OFFICIAL,
                    description=description,
                    ticker=_extract_ticker(description),
                    instrument_family=infer_instrument_family(description),
                    currency=infer_currency(description),
                    maturity_date=parse_explicit_maturity_date(description),
                    auction_date=publication_date,
                    issue_action=_extract_issue_action(description),
                    source_url=source_url,
                    source_title=source_title,
                    source_fields=tuple(source_fields),
                    discovered_at=retrieved_at,
                )
            )
    return tuple(candidates)
