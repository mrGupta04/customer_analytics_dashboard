from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError


def load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"File not found: {path}") from exc
    except EmptyDataError as exc:
        raise EmptyDataError(f"File is empty: {path}") from exc


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Merge cleaned datasets and run analysis.")
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
        help="Directory containing cleaned CSVs and output location for analysis CSVs.",
    )
    return parser.parse_args()


def merge_datasets(
    customers_clean: pd.DataFrame, orders_clean: pd.DataFrame, products: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders_with_customers = orders_clean.merge(
        customers_clean,
        on="customer_id",
        how="left",
        suffixes=("_order", "_customer"),
    )

    full_data = orders_with_customers.merge(
        products,
        left_on="product",
        right_on="product_name",
        how="left",
    )
    return orders_with_customers, full_data


def compute_churn_flags(
    customers_clean: pd.DataFrame, completed_orders: pd.DataFrame, reference_date: pd.Timestamp
) -> pd.DataFrame:
    last_completed = (
        completed_orders.groupby("customer_id", dropna=False)["order_date"]
        .max()
        .reset_index(name="last_completed_order_date")
    )

    churn_df = customers_clean[["customer_id"]].drop_duplicates().merge(
        last_completed,
        on="customer_id",
        how="left",
    )

    if pd.isna(reference_date):
        churn_df["churned"] = True
        return churn_df[["customer_id", "churned"]]

    churn_cutoff = reference_date - pd.Timedelta(days=90)
    churn_df["churned"] = churn_df["last_completed_order_date"].isna() | (
        churn_df["last_completed_order_date"] < churn_cutoff
    )
    return churn_df[["customer_id", "churned"]]


def build_outputs(
    customers_clean: pd.DataFrame, orders_with_customers: pd.DataFrame, full_data: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    full_data = full_data.copy()
    full_data["order_date"] = pd.to_datetime(full_data["order_date"], errors="coerce")
    full_data["amount"] = pd.to_numeric(full_data["amount"], errors="coerce")
    full_data["region"] = full_data["region"].fillna("Unknown")

    completed_orders = full_data.loc[full_data["status"] == "completed"].copy()
    reference_date = full_data["order_date"].max()

    monthly_revenue = (
        completed_orders.dropna(subset=["order_year_month"])
        .groupby("order_year_month", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_revenue"})
        .sort_values("order_year_month")
    )

    top_customers = (
        completed_orders.groupby(["customer_id", "name", "region"], dropna=False)["amount"]
        .sum()
        .reset_index(name="total_spend")
        .sort_values("total_spend", ascending=False)
        .head(10)
    )
    churn_flags = compute_churn_flags(customers_clean, completed_orders, reference_date)
    top_customers = top_customers.merge(churn_flags, on="customer_id", how="left")
    top_customers["churned"] = (
        top_customers["churned"].astype("boolean").fillna(True).astype(bool)
    )

    category_performance = (
        completed_orders.assign(category=completed_orders["category"].fillna("Unknown"))
        .groupby("category", as_index=False)
        .agg(
            total_revenue=("amount", "sum"),
            average_order_value=("amount", "mean"),
            number_of_orders=("order_id", "count"),
        )
        .sort_values("total_revenue", ascending=False)
    )

    customer_counts = (
        customers_clean.assign(region=customers_clean["region"].fillna("Unknown"))
        .groupby("region", as_index=False)
        .agg(number_of_customers=("customer_id", "nunique"))
    )
    order_counts = (
        full_data.groupby("region", as_index=False).agg(number_of_orders=("order_id", "count"))
    )
    revenue_by_region = (
        completed_orders.groupby("region", as_index=False).agg(total_revenue=("amount", "sum"))
    )

    regional_analysis = customer_counts.merge(order_counts, on="region", how="outer").merge(
        revenue_by_region, on="region", how="outer"
    )
    regional_analysis["number_of_customers"] = (
        regional_analysis["number_of_customers"].fillna(0).astype(int)
    )
    regional_analysis["number_of_orders"] = (
        regional_analysis["number_of_orders"].fillna(0).astype(int)
    )
    regional_analysis["total_revenue"] = regional_analysis["total_revenue"].fillna(0.0)
    regional_analysis["average_revenue_per_customer"] = np.where(
        regional_analysis["number_of_customers"] > 0,
        regional_analysis["total_revenue"] / regional_analysis["number_of_customers"],
        0.0,
    )
    regional_analysis = regional_analysis.sort_values("region")

    return {
        "monthly_revenue": monthly_revenue,
        "top_customers": top_customers,
        "category_performance": category_performance,
        "regional_analysis": regional_analysis,
    }


def main() -> None:
    args = parse_args()
    args.processed_dir.mkdir(parents=True, exist_ok=True)

    customers_clean = load_csv(args.processed_dir / "customers_clean.csv")
    orders_clean = load_csv(args.processed_dir / "orders_clean.csv")
    products = load_csv(args.raw_dir / "products.csv")

    orders_with_customers, full_data = merge_datasets(customers_clean, orders_clean, products)

    unmatched_customers = int(orders_with_customers["name"].isna().sum())
    unmatched_products = int(full_data["product_id"].isna().sum())
    print(f"Order rows without customer match: {unmatched_customers}")
    print(f"Order rows without product match: {unmatched_products}")

    outputs = build_outputs(customers_clean, orders_with_customers, full_data)
    outputs["monthly_revenue"].to_csv(
        args.processed_dir / "monthly_revenue.csv", index=False
    )
    outputs["top_customers"].to_csv(args.processed_dir / "top_customers.csv", index=False)
    outputs["category_performance"].to_csv(
        args.processed_dir / "category_performance.csv", index=False
    )
    outputs["regional_analysis"].to_csv(
        args.processed_dir / "regional_analysis.csv", index=False
    )


if __name__ == "__main__":
    main()
