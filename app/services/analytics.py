import pandas as pd
import numpy as np
from pathlib import Path


# Only load columns we actually need — skipping unused columns saves memory and speeds up parsing
NEEDED_COLUMNS = [
    "payment_status",
    "payment_source",
    "city",
    "country_code",
    "card_brand",
    "proposed_at",
]

# Use categorical dtype for low-cardinality string columns (big speedup for groupby)
DTYPE_MAP = {
    "payment_status": "category",
    "payment_source": "category",
    "card_brand": "category",
    "country_code": "category",
}


class TransactionAnalytics:
    """
    Core analytics engine — reads a CSV/Excel file and produces
    all the aggregations the dashboard needs.
    """

    def __init__(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            self.df = pd.read_csv(
                file_path,
                usecols=lambda c: c in NEEDED_COLUMNS,
                dtype=DTYPE_MAP,
                low_memory=False,
            )
        elif ext in (".xlsx", ".xls"):
            self.df = pd.read_excel(
                file_path,
                usecols=lambda c: c in NEEDED_COLUMNS,
            )
            # Apply categorical dtypes after reading Excel
            for col, dtype in DTYPE_MAP.items():
                if col in self.df.columns:
                    self.df[col] = self.df[col].astype(dtype)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        self._preprocess()

    def _preprocess(self):
        df = self.df
        df["proposed_at"] = pd.to_datetime(df["proposed_at"], errors="coerce")
        df["hour"] = df["proposed_at"].dt.hour
        df["month"] = df["proposed_at"].dt.to_period("M").astype(str)
        # Normalize city for consistent grouping
        df["city_normalized"] = df["city"].str.strip().str.upper().astype("category")
        self.df = df

    def summary(self) -> dict:
        df = self.df
        status_counts = df["payment_status"].value_counts().to_dict()
        total = len(df)
        return {
            "total": total,
            "success": int(status_counts.get("success", 0)),
            "failed": int(status_counts.get("failed", 0)),
            "pending": int(status_counts.get("pending", 0)),
            "success_rate": round(status_counts.get("success", 0) / total * 100, 2) if total else 0,
            "failure_rate": round(status_counts.get("failed", 0) / total * 100, 2) if total else 0,
        }

    def by_payment_source(self) -> list[dict]:
        df = self.df
        grouped = df.groupby("payment_source", observed=True)["payment_status"].value_counts().unstack(fill_value=0)
        grouped["total"] = grouped.sum(axis=1)
        if "failed" in grouped.columns:
            grouped["fail_rate"] = (grouped["failed"] / grouped["total"] * 100).round(2)
        else:
            grouped["fail_rate"] = 0.0
        grouped = grouped.reset_index().sort_values("total", ascending=False)
        return grouped.to_dict(orient="records")

    def by_city(self, top_n: int = 20) -> list[dict]:
        df = self.df
        city_fail = (
            df[df["payment_status"] == "failed"]
            .groupby("city_normalized", observed=True)
            .size()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
        city_fail.columns = ["city", "failures"]
        return city_fail.to_dict(orient="records")

    def by_country(self, top_n: int = 15) -> list[dict]:
        df = self.df
        country_fail = (
            df[df["payment_status"] == "failed"]
            .groupby("country_code", observed=True)
            .size()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
        country_fail.columns = ["country_code", "failures"]
        return country_fail.to_dict(orient="records")

    def by_hour(self) -> list[dict]:
        df = self.df
        hourly = (
            df.groupby(["hour", "payment_status"], observed=True)
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        return hourly.to_dict(orient="records")

    def by_month(self) -> list[dict]:
        df = self.df
        monthly = (
            df.groupby(["month", "payment_status"], observed=True)
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        return monthly.to_dict(orient="records")

    def by_card_brand(self) -> list[dict]:
        df = self.df
        mask = df["card_brand"].notna() & (df["card_brand"].astype(str) != "NULL")
        brands = (
            df[mask]
            .groupby("card_brand", observed=True)["payment_status"]
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )
        return brands.to_dict(orient="records")

    def full_report(self) -> dict:
        return {
            "summary": self.summary(),
            "by_payment_source": self.by_payment_source(),
            "by_city": self.by_city(),
            "by_country": self.by_country(),
            "by_hour": self.by_hour(),
            "by_month": self.by_month(),
            "by_card_brand": self.by_card_brand(),
        }
