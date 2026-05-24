"""Shared normalized fields used across document schemas."""

from pbc_chaos.schemas.base import FieldRequirement as Req
from pbc_chaos.schemas.base import FieldType as Type
from pbc_chaos.schemas.base import NormalizedField, nf

CLIENT_ID = nf(
    "client_id",
    Type.IDENTIFIER,
    Req.REQUIRED,
    "Stable synthetic client identifier.",
    concept="client",
    nullable=False,
)

CLIENT_NAME = nf(
    "client_name",
    Type.STRING,
    Req.RECOMMENDED,
    "Client legal or trading name as represented in the workbook.",
    concept="client",
    aliases=("Company", "Co Name", "Entity", "Client"),
)

FINANCIAL_YEAR = nf(
    "financial_year",
    Type.INTEGER,
    Req.REQUIRED,
    "Financial year represented by the document.",
    concept="period",
    aliases=("FY", "Year", "FYE"),
    nullable=False,
)

PERIOD_START = nf(
    "period_start",
    Type.DATE,
    Req.RECOMMENDED,
    "Start date of the reporting period.",
    concept="period",
    aliases=("From", "Start Date", "Period From"),
)

PERIOD_END = nf(
    "period_end",
    Type.DATE,
    Req.REQUIRED,
    "End date or as-at date of the reporting period.",
    concept="period",
    aliases=("As At", "To", "End Date", "Period End", "Balance Date"),
    nullable=False,
)

CURRENCY = nf(
    "currency",
    Type.CURRENCY_CODE,
    Req.RECOMMENDED,
    "ISO currency code for monetary fields.",
    concept="currency",
    aliases=("Currency", "CCY", "Curr"),
)

SOURCE_FILE_NAME = nf(
    "source_file_name",
    Type.STRING,
    Req.SYSTEM,
    "Generated workbook filename containing the source row.",
    concept="lineage",
)

SOURCE_SHEET_NAME = nf(
    "source_sheet_name",
    Type.STRING,
    Req.SYSTEM,
    "Worksheet name containing the source row.",
    concept="lineage",
)

SOURCE_ROW_NUMBER = nf(
    "source_row_number",
    Type.INTEGER,
    Req.SYSTEM,
    "One-based worksheet row number for lineage.",
    concept="lineage",
)

RAW_ROW_HASH = nf(
    "raw_row_hash",
    Type.STRING,
    Req.SYSTEM,
    "Stable hash of the raw extracted row after workbook rendering.",
    concept="lineage",
)

EXTRACTION_CONFIDENCE = nf(
    "extraction_confidence",
    Type.PERCENTAGE,
    Req.SYSTEM,
    "Optional downstream extraction confidence score for AI testing.",
    concept="lineage",
)

REMARKS = nf(
    "remarks",
    Type.STRING,
    Req.OPTIONAL,
    "Free-text notes, comments, or operational remarks.",
    concept="annotation",
    aliases=("Notes", "Remark", "Comments", "Review Notes"),
)

COMMON_DOCUMENT_FIELDS: tuple[NormalizedField, ...] = (
    CLIENT_ID,
    CLIENT_NAME,
    FINANCIAL_YEAR,
    PERIOD_START,
    PERIOD_END,
    CURRENCY,
    SOURCE_FILE_NAME,
    SOURCE_SHEET_NAME,
    SOURCE_ROW_NUMBER,
    RAW_ROW_HASH,
    EXTRACTION_CONFIDENCE,
)

