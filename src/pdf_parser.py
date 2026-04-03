import re
from datetime import datetime

import pandas as pd
import pdfplumber

# Mapping: description keyword → PJ code (fallback when PNB parsing fails)
BRANCH_KEYWORDS = {
    "CENTAR SPLIT": "PJ12",
    "MALL OF SPLIT": "PJ07",
    "RIJEKA RIVA": "PJ08",
    "RIVA RIJEKA": "PJ08",
    "RIVA RKA": "PJ08",
    "RIJEKA TOWER": "PJ23",
    "OSIJEK": "PJ22",
    "ZADAR": "PJ19",
    "SUPERNOVA": "PJ19",
    "PULA": "PJ14",
    "VARAŽDIN": "PJ24",
    "VARAZDIN": "PJ24",
    "VŽ-CENTAR": "PJ24",
    "VZ-CENTAR": "PJ24",
    "VŽ CENTAR": "PJ24",
    "MALEŠNICA": "PJ02",
    "MALESNICA": "PJ02",
    "MALEŠENICA": "PJ02",
    "LANIŠTE": "PJ25",
    "LANSTE": "PJ25",
    "LANŠTE": "PJ25",
    "MARTINOVKA": "PJ15",
    "BUNDEK": "PJ21",
    "DUBRAVA": "PJ11",
    "KVATRIĆ": "PJ13",
    "KVATRIC": "PJ13",
    "KVARTIĆ": "PJ13",
    "VLAŠKA": "PJ06",
    "VLASKA": "PJ06",
    "Z CENTAR": "PJ17",
    "Z-CENTAR": "PJ17",
    "ZAGREBAČKA": "PJ10",
    "ZAGREBACKA": "PJ10",
    "ILICA": "PJ16",
    "TRAVNO": "PJ26",
    "POINT": "PJ03",
    "VRBANI": "PJ03",
    "MIMARA": "PJ02",
}

# Bank PNB suffix → Excel PJ code remapping
# (bank uses different numbering for some branches)
PNB_PJ_REMAP = {
    "PJ01": "PJ02",  # Bank -01 (Malešnica) = Excel PJ02 (Maloprodaja Mimara)
}


def _validate_sale_date(dt: datetime | None) -> bool:
    """Check if parsed date is reasonable (within expected range)."""
    if dt is None:
        return False
    return 2026 <= dt.year <= 2027 and 1 <= dt.month <= 12


def _parse_pnb_standard(pnb: str) -> tuple[str | None, datetime | None]:
    """Parse standard PNB format: DDMMYYYY-PJ → (pj_code, sale_date)."""
    m = re.match(r"^(\d{8})-(\d{1,2})$", pnb)
    if not m:
        return None, None
    date_str, pj_num = m.group(1), m.group(2)
    try:
        dt = datetime.strptime(date_str, "%d%m%Y")
    except ValueError:
        return None, None
    return f"PJ{pj_num.zfill(2)}", dt


def _parse_pnb_relaxed(pnb: str) -> tuple[str | None, datetime | None]:
    """Try relaxed patterns for non-standard PNB entries."""
    # Pattern: DDMMYYYY + PJ concatenated (no dash), e.g. "1803202611"
    m = re.match(r"^(\d{8})(\d{1,2})$", pnb)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%d%m%Y")
            return f"PJ{m.group(2).zfill(2)}", dt
        except ValueError:
            pass

    # Pattern: shortened date with dash, e.g. "200326-21"
    m = re.match(r"^(\d{6})-(\d{1,2})$", pnb)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%d%m%y")
            return f"PJ{m.group(2).zfill(2)}", dt
        except ValueError:
            pass

    # Pattern: very short date (3-5 digits) with dash + PJ, e.g. "30126-24"
    # Missing digits in date — extract PJ code, let description handle date
    m = re.match(r"^(\d{3,5})-(\d{1,2})$", pnb)
    if m:
        return f"PJ{m.group(2).zfill(2)}", None

    # Pattern: 7-digit date (missing digit) with dash, e.g. "1803226-24"
    m = re.match(r"^(\d{7})-(\d{1,2})$", pnb)
    if m:
        date_part = m.group(1)
        # Try inserting a digit to make 8 digits
        for i in range(len(date_part) + 1):
            for d in "0123456789":
                candidate = date_part[:i] + d + date_part[i:]
                try:
                    dt = datetime.strptime(candidate, "%d%m%Y")
                    if 2020 <= dt.year <= 2030:
                        return f"PJ{m.group(2).zfill(2)}", dt
                except ValueError:
                    continue

    # Pattern: typo with extra digits, e.g. "210320226-17"
    m = re.match(r"^(\d{9,})-(\d{1,2})$", pnb)
    if m:
        date_part = m.group(1)
        # Try removing one digit at various positions
        for i in range(len(date_part)):
            trimmed = date_part[:i] + date_part[i + 1:]
            if len(trimmed) == 8:
                try:
                    dt = datetime.strptime(trimmed, "%d%m%Y")
                    return f"PJ{m.group(2).zfill(2)}", dt
                except ValueError:
                    continue

    # Pattern: DD-M-YYYY format, e.g. "13-3-2026"
    m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", pnb)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return None, dt  # No PJ code in this format
        except ValueError:
            pass

    # Pattern: just DDMMYYYY (no PJ code), e.g. "16032026"
    m = re.match(r"^(\d{8})$", pnb)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%d%m%Y")
            return None, dt
        except ValueError:
            pass

    return None, None


def _extract_pj_from_description(desc: str) -> str | None:
    """Extract PJ code from transaction description using keyword matching."""
    upper = desc.upper()
    # Try longer keywords first (more specific)
    for keyword in sorted(BRANCH_KEYWORDS, key=len, reverse=True):
        if keyword in upper:
            return BRANCH_KEYWORDS[keyword]
    return None


def _extract_date_from_description(desc: str) -> datetime | None:
    """Try to extract a date from the description text."""
    # Match patterns like "12.03.2026", "16.3.2026", "12.03.26"
    patterns = [
        (r"(\d{1,2})\.(\d{1,2})\.(\d{4})", "%d.%m.%Y"),
        (r"(\d{1,2})\.(\d{1,2})\.(\d{2})\b", "%d.%m.%y"),
    ]
    for pattern, fmt in patterns:
        m = re.search(pattern, desc)
        if m:
            try:
                date_str = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    return None


def _parse_amount(amount_str: str) -> float:
    """Parse European-format amount string (e.g., '1.763,35' → 1763.35)."""
    if not amount_str:
        return 0.0
    s = str(amount_str).strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


def _parse_booking_date(date_str: str) -> datetime | None:
    """Parse booking date from '16.03.2026.\\n16.03.2026.' format."""
    if not date_str:
        return None
    first_line = str(date_str).split("\n")[0].strip().rstrip(".")
    try:
        return datetime.strptime(first_line, "%d.%m.%Y")
    except ValueError:
        return None


def parse_pdf(file) -> tuple[pd.DataFrame, dict]:
    """Parse bank statement PDF into a DataFrame.

    Args:
        file: file path (str) or file-like object (Streamlit UploadedFile)

    Returns:
        (df, meta) where df has columns
        [booking_date, sale_date, pj_code, branch_name, amount, pnb, row_num]
        and meta has keys: period_start, period_end, total_amount, transaction_count, iban
    """
    pdf = pdfplumber.open(file)

    # Extract period and IBAN from first page text
    first_text = pdf.pages[0].extract_text() or ""
    period_match = re.search(
        r"Razdoblje:\s*(\d{1,2}\.\d{2}\.\d{4})\.\s*-\s*(\d{1,2}\.\d{2}\.\d{4})\.",
        first_text,
    )
    period_start = period_end = None
    if period_match:
        try:
            period_start = datetime.strptime(period_match.group(1), "%d.%m.%Y")
            period_end = datetime.strptime(period_match.group(2), "%d.%m.%Y")
        except ValueError:
            pass

    iban_match = re.search(r"IBAN:\s*(HR\d{19})", first_text)
    iban = iban_match.group(1) if iban_match else None

    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                # Skip non-data rows
                if not row[0] or not str(row[0]).strip().replace(".", "").isdigit():
                    continue

                row_num = int(str(row[0]).strip())
                booking_date = _parse_booking_date(row[1])
                amount = _parse_amount(row[3])

                desc = str(row[5]).replace("\n", " ") if row[5] else ""
                pnb_col = str(row[6]) if len(row) > 6 and row[6] else ""
                pnb_first = pnb_col.split("\n")[0].strip()

                # Step 1: Try standard PNB parsing
                pj_code, sale_date = _parse_pnb_standard(pnb_first)

                # Step 2: Try relaxed PNB parsing
                if pj_code is None or sale_date is None:
                    pj_relaxed, date_relaxed = _parse_pnb_relaxed(pnb_first)
                    if pj_code is None and pj_relaxed:
                        pj_code = pj_relaxed
                    if sale_date is None and date_relaxed:
                        sale_date = date_relaxed

                # Step 3: Validate parsed date — if bad, use description date
                desc_date = _extract_date_from_description(desc)
                if not _validate_sale_date(sale_date):
                    if _validate_sale_date(desc_date):
                        sale_date = desc_date
                # Also: if PNB date and description date disagree by >7 days,
                # prefer description date (PNB typos can produce valid-but-wrong dates)
                elif desc_date and _validate_sale_date(desc_date) and sale_date:
                    if abs((sale_date - desc_date).days) > 7:
                        sale_date = desc_date

                # Step 4: Fallback to description for PJ code
                if pj_code is None:
                    pj_code = _extract_pj_from_description(desc)

                # Step 5: Fallback to description for sale date
                if sale_date is None:
                    sale_date = _extract_date_from_description(desc)

                # Step 6: For PNB without suffix, prefer description date
                # (PNB date can be booking date, description has actual sale date)
                if pj_code is not None and re.match(r"^\d{8}$", pnb_first):
                    desc_date = _extract_date_from_description(desc)
                    if desc_date and _validate_sale_date(desc_date):
                        sale_date = desc_date

                # Step 7: Remap bank PJ codes to Excel PJ codes
                if pj_code in PNB_PJ_REMAP:
                    pj_code = PNB_PJ_REMAP[pj_code]

                # Extract branch name from description for display
                branch_name = ""
                for keyword in sorted(BRANCH_KEYWORDS, key=len, reverse=True):
                    if keyword in desc.upper():
                        branch_name = keyword.title()
                        break

                rows.append({
                    "row_num": row_num,
                    "booking_date": booking_date,
                    "sale_date": sale_date,
                    "pj_code": pj_code,
                    "branch_name": branch_name,
                    "amount": amount,
                    "pnb": pnb_first,
                    "description": desc,
                })

    pdf.close()

    df = pd.DataFrame(rows)
    if not df.empty:
        df["booking_date"] = pd.to_datetime(df["booking_date"])
        df["sale_date"] = pd.to_datetime(df["sale_date"])

    meta = {
        "period_start": period_start,
        "period_end": period_end,
        "total_amount": df["amount"].sum() if not df.empty else 0,
        "transaction_count": len(df),
        "iban": iban,
    }
    return df, meta
