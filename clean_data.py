from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from pandas.errors import EmptyDataError


DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d")
ORDER_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y")
STATUS_VOCAB = {"completed", "pending", "cancelled", "refunded"}
STATUS_MAP = {
    "complete": "completed",
    "completed": "completed",
    "done": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "refund": "refunded",
    "refunded": "refunded",
    "pending": "pending",
    "in progress": "pending",
    "processing": "pending",
    "on hold": "pending",
}


def parse_mixed_date(value: object, formats: Tuple[str, ...]) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()
    if not text:
        return pd.NaT

    for fmt in formats:
        try:
            return pd.to_datetime(text, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT


def normalize_status(value: object) -> str:
    if pd.isna(value):
        return "pending"

    normalized = str(value).strip().lower()
    mapped = STATUS_MAP.get(normalized, normalized)
    if mapped not in STATUS_VOCAB:
        return "pending"
    return mapped


def is_valid_email(value: object) -> bool:
    if pd.isna(value):
        return False

    text = str(value).strip().lower()
    if not text:
        return False
    return "@" in text and "." in text.split("@")[-1]


def load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"File not found: {path}") from exc
    except EmptyDataError as exc:
        raise EmptyDataError(f"File is empty: {path}") from exc


def clean_customers(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, object]]:
    rows_before = len(df)
    nulls_before = df.isna().sum().to_dict()

    df = df.copy()
    df["name"] = df["name"].astype("string").str.strip()
    df["region"] = df["region"].astype("string").str.strip()
    df["region"] = df["region"].replace("", pd.NA).fillna("Unknown")

    df["email"] = df["email"].astype("string").str.strip().str.lower()
    df["is_valid_email"] = df["email"].apply(is_valid_email)

    df["signup_date"] = df["signup_date"].apply(
        lambda val: parse_mixed_date(val, DATE_FORMATS)
    )
    unparsable_dates = int(df["signup_date"].isna().sum())
    if unparsable_dates:
        logging.warning(
            "customers.csv: %s signup_date values could not be parsed and were set to NaT.",
            unparsable_dates,
        )

    df["_row_order"] = range(len(df))
    df["_signup_sort"] = df["signup_date"].fillna(pd.Timestamp.min)
    df = df.sort_values(
        by=["customer_id", "_signup_sort", "_row_order"],
        ascending=[True, True, True],
    )
    df = df.drop_duplicates(subset=["customer_id"], keep="last")
    df = df.sort_values("_row_order").drop(columns=["_signup_sort", "_row_order"])

    rows_after = len(df)
    duplicates_removed = rows_before - rows_after
    nulls_after = df.isna().sum().to_dict()

    report = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "duplicates_removed": duplicates_removed,
        "nulls_before": nulls_before,
        "nulls_after": nulls_after,
    }
    return df, report


def clean_orders(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, object]]:
    rows_before = len(df)
    nulls_before = df.isna().sum().to_dict()

    df = df.copy()
    unrecoverable_mask = df["customer_id"].isna() & df["order_id"].isna()
    dropped_unrecoverable = int(unrecoverable_mask.sum())
    df = df.loc[~unrecoverable_mask].copy()

    df["order_date"] = df["order_date"].apply(
        lambda val: parse_mixed_date(val, ORDER_DATE_FORMATS)
    )
    unparsable_order_dates = int(df["order_date"].isna().sum())
    if unparsable_order_dates:
        logging.warning(
            "orders.csv: %s order_date values could not be parsed and were set to NaT.",
            unparsable_order_dates,
        )

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["product"] = df["product"].astype("string").str.strip()
    product_median = df.groupby("product")["amount"].transform("median")
    df["amount"] = df["amount"].fillna(product_median)
    global_median = df["amount"].median()
    if pd.notna(global_median):
        df["amount"] = df["amount"].fillna(global_median)

    df["status"] = df["status"].apply(normalize_status)
    df["order_year_month"] = df["order_date"].dt.strftime("%Y-%m")

    rows_after = len(df)
    nulls_after = df.isna().sum().to_dict()
    report = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "dropped_unrecoverable": dropped_unrecoverable,
        "nulls_before": nulls_before,
        "nulls_after": nulls_after,
    }
    return df, report


def print_report(section: str, report: Dict[str, object]) -> None:
    print(f"\n=== {section} ===")
    print(f"Rows before: {report['rows_before']}")
    print(f"Rows after: {report['rows_after']}")

    if "duplicates_removed" in report:
        print(f"Duplicate rows removed: {report['duplicates_removed']}")
    if "dropped_unrecoverable" in report:
        print(f"Unrecoverable rows dropped: {report['dropped_unrecoverable']}")

    print("\nNull counts before:")
    for column, count in report["nulls_before"].items():
        print(f"  {column}: {count}")

    print("\nNull counts after:")
    for column, count in report["nulls_after"].items():
        print(f"  {column}: {count}")


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Clean raw customer and order datasets.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=base_dir / "data" / "raw",
        help="Directory containing raw CSV files.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=base_dir / "data" / "processed",
        help="Directory where cleaned CSV files will be written.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    args.processed_dir.mkdir(parents=True, exist_ok=True)

    customers_path = args.raw_dir / "customers.csv"
    orders_path = args.raw_dir / "orders.csv"

    customers_raw = load_csv(customers_path)
    orders_raw = load_csv(orders_path)

    customers_clean, customers_report = clean_customers(customers_raw)
    orders_clean, orders_report = clean_orders(orders_raw)

    customers_clean.to_csv(
        args.processed_dir / "customers_clean.csv",
        index=False,
        date_format="%Y-%m-%d",
    )
    orders_clean.to_csv(
        args.processed_dir / "orders_clean.csv",
        index=False,
        date_format="%Y-%m-%d",
    )

    print_report("customers.csv cleaning report", customers_report)
    print_report("orders.csv cleaning report", orders_report)


if __name__ == "__main__":
    main()
