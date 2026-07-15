"""Excel ingestion / ETL pipeline.

Reads the Berkeley Carbon Trading Project 'Voluntary Registry Offsets Database'
PROJECTS tab and loads it into PostgreSQL.

Layout of the PROJECTS sheet (verified against v2026-04):
  * Row 4 holds the column headers.
  * Data starts on row 5.
  * Columns 1..23 are the identity / totals block.
  * Column 23 = "First Year of Project (Vintage)".
  * Columns 24.. are per-vintage-year credits issued, starting at year 1996
    (col 24 = 1996, so year = 1996 + (col - 24)).

Two entry points:
  ingest_from_excel(db, path)  -> full ingest from the .xlsx (uses pandas/openpyxl)
  ingest_from_csv(db, path)    -> fast ingest from the pre-extracted seed CSV
"""
from __future__ import annotations

import csv
import logging

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.constants import is_project_eligible, parse_year
from app.db.models import Project

log = logging.getLogger("etl")

HEADER_ROW = 4          # 1-indexed
FIRST_DATA_ROW = 5      # 1-indexed
VINTAGE_FIRST_COL = 24  # 1-indexed -> year 1996
VINTAGE_FIRST_YEAR = 1996


def _to_float(v) -> float:
    try:
        if v is None or (isinstance(v, str) and not v.strip()):
            return 0.0
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _clean(v) -> str:
    if v is None:
        return ""
    return str(v).replace("\n", " ").replace("\r", " ").strip()


def _row_to_project(rec: dict, vintage_issuance: dict[str, float] | None = None) -> Project:
    first_vintage = parse_year(rec.get("first_vintage_year"))
    status = _clean(rec.get("voluntary_status"))
    return Project(
        project_id=_clean(rec.get("project_id")),
        project_name=_clean(rec.get("project_name")),
        registry=_clean(rec.get("registry")),
        arb_wa_project=_clean(rec.get("arb_wa_project")),
        voluntary_status=status,
        scope=_clean(rec.get("scope")),
        type=_clean(rec.get("type")),
        reduction_removal=_clean(rec.get("reduction_removal")),
        methodology=_clean(rec.get("methodology")),
        methodology_version=_clean(rec.get("methodology_version")),
        region=_clean(rec.get("region")),
        country=_clean(rec.get("country")),
        state=_clean(rec.get("state")),
        location=_clean(rec.get("location")),
        developer=_clean(rec.get("developer")),
        credits_issued=_to_float(rec.get("credits_issued")),
        credits_retired=_to_float(rec.get("credits_retired")),
        credits_remaining=_to_float(rec.get("credits_remaining")),
        buffer_deposits=_to_float(rec.get("buffer_deposits")),
        reversals_covered=_to_float(rec.get("reversals_covered")),
        reversals_not_covered=_to_float(rec.get("reversals_not_covered")),
        buffer_released=_to_float(rec.get("buffer_released")),
        first_vintage_year=first_vintage,
        vintage_issuance=vintage_issuance or {},
        is_eligible=is_project_eligible(status, first_vintage),
    )


def ingest_from_csv(db: Session, csv_path: str) -> int:
    """Fast path: load the pre-extracted 23-column seed CSV."""
    log.info("Ingesting projects from seed CSV: %s", csv_path)
    db.execute(delete(Project))
    db.commit()

    count = 0
    batch: list[Project] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for rec in reader:
            if not rec.get("project_id"):
                continue
            batch.append(_row_to_project(rec))
            count += 1
            if len(batch) >= 1000:
                db.add_all(batch)
                db.commit()
                batch = []
    if batch:
        db.add_all(batch)
        db.commit()
    log.info("Ingested %d projects from CSV", count)
    return count


def ingest_from_excel(db: Session, xlsx_path: str, sheet: str = "PROJECTS") -> int:
    """Full path: parse the master workbook including per-vintage issuance columns."""
    log.info("Ingesting projects from workbook: %s [%s]", xlsx_path, sheet)
    # header=HEADER_ROW-1 makes row 4 the header row; data then begins at row 5.
    raw = pd.read_excel(xlsx_path, sheet_name=sheet, header=HEADER_ROW - 1, engine="openpyxl")

    # The first 23 logical columns, mapped positionally (headers in the file are verbose/multiline).
    cols = list(raw.columns)
    id_map = {
        "project_id": 0, "project_name": 1, "registry": 2, "arb_wa_project": 3,
        "voluntary_status": 4, "scope": 5, "type": 6, "reduction_removal": 7,
        "methodology": 8, "methodology_version": 9, "region": 10, "country": 11,
        "state": 12, "location": 13, "developer": 14, "credits_issued": 15,
        "credits_retired": 16, "credits_remaining": 17, "buffer_deposits": 18,
        "reversals_covered": 19, "reversals_not_covered": 20, "buffer_released": 21,
        "first_vintage_year": 22,
    }

    db.execute(delete(Project))
    db.commit()

    count = 0
    batch: list[Project] = []
    for _, row in raw.iterrows():
        pid = row.iloc[id_map["project_id"]] if len(cols) > id_map["project_id"] else None
        if pid is None or str(pid).strip() == "" or str(pid).strip().lower() == "nan":
            continue
        rec = {k: (row.iloc[idx] if idx < len(cols) else None) for k, idx in id_map.items()}

        # per-vintage issuance from column 24 onward
        vintage: dict[str, float] = {}
        for col_idx in range(VINTAGE_FIRST_COL - 1, len(cols)):
            year = VINTAGE_FIRST_YEAR + (col_idx - (VINTAGE_FIRST_COL - 1))
            if year < 1990 or year > 2100:
                continue
            val = _to_float(row.iloc[col_idx])
            if val:
                vintage[str(year)] = val

        batch.append(_row_to_project(rec, vintage))
        count += 1
        if len(batch) >= 1000:
            db.add_all(batch)
            db.commit()
            batch = []
    if batch:
        db.add_all(batch)
        db.commit()
    log.info("Ingested %d projects from workbook", count)
    return count
