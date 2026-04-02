import pandas as pd

from clean_data import (
    ORDER_DATE_FORMATS,
    clean_customers,
    clean_orders,
    normalize_status,
    parse_mixed_date,
)


def test_parse_mixed_date_supports_required_formats():
    assert parse_mixed_date("2025-03-01", ORDER_DATE_FORMATS) == pd.Timestamp("2025-03-01")
    assert parse_mixed_date("01/03/2025", ORDER_DATE_FORMATS) == pd.Timestamp("2025-03-01")
    assert parse_mixed_date("03-01-2025", ORDER_DATE_FORMATS) == pd.Timestamp("2025-03-01")


def test_normalize_status_maps_variants_to_vocab():
    assert normalize_status("done") == "completed"
    assert normalize_status("canceled") == "cancelled"
    assert normalize_status("on hold") == "pending"
    assert normalize_status("unknown-state") == "pending"


def test_clean_customers_keeps_latest_signup_per_customer():
    raw = pd.DataFrame(
        {
            "customer_id": ["C1", "C1", "C2"],
            "name": [" Alice ", "Alice", "Bob"],
            "email": ["ALICE@EXAMPLE.COM", "alice@example.com", "bob.example.com"],
            "region": [" North ", "", None],
            "signup_date": ["2024-01-01", "2024-03-01", "bad-date"],
        }
    )

    cleaned, report = clean_customers(raw)

    assert len(cleaned) == 2
    assert report["duplicates_removed"] == 1

    c1_row = cleaned.loc[cleaned["customer_id"] == "C1"].iloc[0]
    assert c1_row["signup_date"] == pd.Timestamp("2024-03-01")
    assert c1_row["email"] == "alice@example.com"
    assert bool(c1_row["is_valid_email"]) is True

    c2_row = cleaned.loc[cleaned["customer_id"] == "C2"].iloc[0]
    assert bool(c2_row["is_valid_email"]) is False
    assert c2_row["region"] == "Unknown"


def test_clean_orders_drops_unrecoverable_and_fills_amount_from_product_median():
    raw = pd.DataFrame(
        {
            "order_id": ["O1", "O2", None],
            "customer_id": ["C1", "C2", None],
            "product": ["Widget A", "Widget A", "Widget B"],
            "amount": [120.0, None, 200.0],
            "order_date": ["2025-01-01", "02/01/2025", "2025-01-03"],
            "status": ["done", "pending", "completed"],
        }
    )

    cleaned, report = clean_orders(raw)

    assert report["dropped_unrecoverable"] == 1
    assert len(cleaned) == 2
    assert cleaned.loc[cleaned["order_id"] == "O2", "amount"].iloc[0] == 120.0
    assert cleaned.loc[cleaned["order_id"] == "O1", "status"].iloc[0] == "completed"
    assert cleaned.loc[cleaned["order_id"] == "O1", "order_year_month"].iloc[0] == "2025-01"
