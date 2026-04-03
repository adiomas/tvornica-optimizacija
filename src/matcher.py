import pandas as pd


def validate_periods(
    excel_meta: dict, pdf_meta: dict
) -> tuple[bool, str]:
    ex_start = excel_meta.get("period_start")
    ex_end = excel_meta.get("period_end")
    pdf_start = pdf_meta.get("period_start")
    pdf_end = pdf_meta.get("period_end")

    if not all([ex_start, ex_end, pdf_start, pdf_end]):
        return False, "Nije moguće utvrditi periode iz oba fajla."

    tolerance = pd.Timedelta(days=3)
    start_ok = abs(ex_start - pdf_start) <= tolerance
    end_ok = abs(ex_end - pdf_end) <= tolerance

    if start_ok and end_ok:
        return True, (
            f"Periodi se podudaraju: "
            f"Promet {ex_start.strftime('%d.%m.%Y')} - {ex_end.strftime('%d.%m.%Y')}, "
            f"Banka {pdf_start.strftime('%d.%m.%Y')} - {pdf_end.strftime('%d.%m.%Y')}"
        )
    return False, (
        f"Periodi se NE podudaraju!\n"
        f"Promet: {ex_start.strftime('%d.%m.%Y')} - {ex_end.strftime('%d.%m.%Y')}\n"
        f"Banka: {pdf_start.strftime('%d.%m.%Y')} - {pdf_end.strftime('%d.%m.%Y')}"
    )


def _filter_bank_to_excel_dates(
    excel_df: pd.DataFrame, pdf_df: pd.DataFrame
) -> pd.DataFrame:
    """Filter bank transactions to only include sale dates present in Excel."""
    excel_dates = set(excel_df["date"].dt.date.unique())
    pdf_resolved = pdf_df[pdf_df["pj_code"].notna()].copy()
    return pdf_resolved[pdf_resolved["sale_date"].dt.date.isin(excel_dates)]


def _fuzzy_match_by_amount(
    excel_row: pd.Series,
    pdf_df: pd.DataFrame,
    already_matched_rows: set,
) -> tuple[float, str, str]:
    """Try to find a bank entry with same PJ and same amount that wasn't matched.

    Returns (banka_amount, status, napomena).
    """
    pj = excel_row["pj_code"] if "pj_code" in excel_row.index else None
    amount = excel_row.get("promet", excel_row.get("amount", 0))
    ex_date = excel_row.get("date")

    if pj is None or amount == 0:
        return 0, "GREŠKA", "Nema bankovne uplate za ovaj datum"

    amt_rounded = round(amount, 2)
    unused = ~pdf_df["row_num"].isin(already_matched_rows)
    same_amount = pdf_df["amount"].round(2) == amt_rounded

    # Pass A: Same PJ + same amount (different date or outside range)
    candidates = pdf_df[unused & same_amount & (pdf_df["pj_code"] == pj)]
    if not candidates.empty:
        best = candidates.iloc[0]
        already_matched_rows.add(best["row_num"])
        pnb = best["pnb"]
        bank_date = best["sale_date"]
        if pd.notna(bank_date) and pd.notna(ex_date) and bank_date.date() != ex_date.date():
            return amount, "OK*", f"Cifra OK. PNB: {pnb} — datum u izvodu {bank_date.strftime('%d.%m.%Y')} umjesto {ex_date.strftime('%d.%m.%Y')}"
        return amount, "OK*", f"Cifra OK. PNB: {pnb} — spareno po iznosu"

    # Pass B: Same amount + any PJ (including None) — handles wrong PJ or unresolved PJ
    candidates2 = pdf_df[unused & same_amount].copy()
    if not candidates2.empty and pd.notna(ex_date):
        # Score by: prefer same PJ > nearby date > any
        candidates2["_pj_match"] = (candidates2["pj_code"] == pj).astype(int)
        candidates2["_date_diff"] = candidates2["sale_date"].apply(
            lambda d: abs((d - ex_date).days) if pd.notna(d) else 999
        )
        candidates2 = candidates2.sort_values(["_pj_match", "_date_diff"], ascending=[False, True])
        best = candidates2.iloc[0]
        if best["_date_diff"] <= 14:
            already_matched_rows.add(best["row_num"])
            bank_pj = best["pj_code"] if pd.notna(best["pj_code"]) else "?"
            bank_branch = best["branch_name"] or ""
            bank_date = best["sale_date"]
            date_info = f"datum {bank_date.strftime('%d.%m.%Y')}" if pd.notna(bank_date) else "datum nepoznat"
            return amount, "OK*", (
                f"Cifra OK. PNB: {best['pnb']} — "
                f"u izvodu: {bank_pj} {bank_branch} {date_info}"
            )

    return 0, "GREŠKA", "Nema bankovne uplate za ovaj datum"


def match_summary(
    excel_df: pd.DataFrame, pdf_df: pd.DataFrame
) -> pd.DataFrame:
    """Compare total amounts per branch. Uses fuzzy matching for totals."""
    ex_summary = (
        excel_df.groupby("pj_code")
        .agg(pj_name=("pj_name", "first"), promet_total=("amount", "sum"))
        .reset_index()
    )

    # Get banka totals from detail matching (which includes fuzzy matches)
    banka_totals = {}
    for pj_code in ex_summary["pj_code"]:
        details = match_details(excel_df, pdf_df, pj_code)
        banka_totals[pj_code] = details["banka"].sum()

    ex_summary["banka_total"] = ex_summary["pj_code"].map(banka_totals).fillna(0).round(2)
    ex_summary["promet_total"] = ex_summary["promet_total"].round(2)
    ex_summary["razlika"] = (ex_summary["banka_total"] - ex_summary["promet_total"]).round(2)
    ex_summary["razlika_pct"] = ex_summary.apply(
        lambda r: round(r["razlika"] / r["promet_total"] * 100, 1) if r["promet_total"] != 0 else 0,
        axis=1,
    )

    def status(row):
        diff = abs(row["razlika"])
        if diff == 0:
            return "OK"
        if diff < 5:
            return "UPOZORENJE"
        return "GREŠKA"

    ex_summary["status"] = ex_summary.apply(status, axis=1)
    ex_summary = ex_summary.sort_values("pj_code").reset_index(drop=True)
    return ex_summary


def match_details(
    excel_df: pd.DataFrame, pdf_df: pd.DataFrame, pj_code: str
) -> pd.DataFrame:
    """Day-by-day comparison with fuzzy matching and napomena.

    Pass 1: Match by PJ + date (exact)
    Pass 2: For unmatched, try matching by PJ + amount (fuzzy)

    Returns DataFrame with columns:
    [date, promet, banka, razlika, status, napomena]
    """
    ex = excel_df[excel_df["pj_code"] == pj_code][["date", "amount"]].copy()
    ex = ex.rename(columns={"amount": "promet"})
    ex["pj_code"] = pj_code

    # Pass 1: exact match by PJ + date
    bank_filtered = _filter_bank_to_excel_dates(excel_df, pdf_df)
    bank_pj = bank_filtered[bank_filtered["pj_code"] == pj_code].copy()

    # Track which bank rows are used
    matched_bank_rows = set()
    if not bank_pj.empty:
        matched_bank_rows = set(bank_pj["row_num"].values)

    bank = (
        bank_pj.groupby("sale_date")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"sale_date": "date", "amount": "banka"})
    )

    merged = pd.merge(ex, bank, on="date", how="left")
    merged["promet"] = merged["promet"].fillna(0).round(2)
    merged["banka"] = merged["banka"].fillna(0).round(2)
    merged["razlika"] = (merged["banka"] - merged["promet"]).round(2)
    merged["napomena"] = ""

    # Pass 1 status + napomena for exact matches with PNB issues
    for idx, row in merged.iterrows():
        diff = abs(row["razlika"])
        if diff == 0:
            merged.at[idx, "status"] = "OK"
            # Check if original PNB had issues (date correction, etc.)
            bank_entries = bank_pj[bank_pj["sale_date"] == row["date"]]
            for _, be in bank_entries.iterrows():
                pnb = be.get("pnb", "")
                desc = be.get("description", "")
                # Check if PNB date doesn't match sale_date (was corrected by description)
                if pnb and "-" in str(pnb):
                    import re
                    m = re.match(r"^(\d{8})-(\d{1,2})$", str(pnb))
                    if m:
                        from datetime import datetime
                        try:
                            pnb_date = datetime.strptime(m.group(1), "%d%m%Y")
                            if pnb_date.date() != row["date"].date():
                                merged.at[idx, "napomena"] = f"PNB: {pnb} — datum korigiran iz opisa"
                        except ValueError:
                            merged.at[idx, "napomena"] = f"PNB: {pnb} — neispravan format"
        elif diff < 1:
            merged.at[idx, "status"] = "UPOZORENJE"
            merged.at[idx, "napomena"] = f"Mala razlika: {row['razlika']:+.2f} €"
        else:
            merged.at[idx, "status"] = "GREŠKA"

    # Pass 2: fuzzy match unmatched rows by amount
    unmatched_mask = (merged["status"] == "GREŠKA") & (merged["banka"] == 0)
    if unmatched_mask.any():
        for idx in merged[unmatched_mask].index:
            row = merged.loc[idx]
            banka_val, new_status, napomena = _fuzzy_match_by_amount(
                row, pdf_df, matched_bank_rows,
            )
            if banka_val > 0:
                merged.at[idx, "banka"] = round(banka_val, 2)
                merged.at[idx, "razlika"] = round(banka_val - row["promet"], 2)
                merged.at[idx, "status"] = new_status
                merged.at[idx, "napomena"] = napomena

    # Final pass: add note for remaining GREŠKA rows
    for idx, row in merged.iterrows():
        if row["status"] == "GREŠKA" and not row["napomena"]:
            if row["banka"] == 0:
                merged.at[idx, "napomena"] = "Nema bankovne uplate za ovaj datum"
            else:
                merged.at[idx, "napomena"] = f"Razlika iznosa: {row['razlika']:+.2f} €"

    merged = merged.drop(columns=["pj_code"], errors="ignore")
    merged = merged.sort_values("date").reset_index(drop=True)
    return merged


def get_unmatched_bank(pdf_df: pd.DataFrame) -> pd.DataFrame:
    unmatched = pdf_df[pdf_df["pj_code"].isna()].copy()
    if unmatched.empty:
        return unmatched
    return unmatched[
        ["row_num", "booking_date", "amount", "pnb", "description"]
    ].reset_index(drop=True)


def get_unmatched_by_date(
    excel_df: pd.DataFrame, pdf_df: pd.DataFrame
) -> pd.DataFrame:
    """Find Excel entries with no corresponding bank entry (even after fuzzy matching)."""
    results = []
    for pj_code in excel_df["pj_code"].unique():
        details = match_details(excel_df, pdf_df, pj_code)
        missing = details[details["banka"] == 0]
        for _, row in missing.iterrows():
            pj_name = excel_df[excel_df["pj_code"] == pj_code]["pj_name"].iloc[0]
            results.append({
                "pj_code": pj_code,
                "pj_name": pj_name,
                "date": row["date"],
                "amount": row["promet"],
            })
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).reset_index(drop=True)
