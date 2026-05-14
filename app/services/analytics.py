import pandas as pd
import numpy as np
from pathlib import Path


class TransactionAnalytics:
    """
    Core analytics engine — reads a CSV/Excel file and produces
    all the aggregations the dashboard needs.
    """

    def __init__(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            self.df = pd.read_csv(file_path, low_memory=False)
        elif ext in (".xlsx", ".xls"):
            self.df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        self._preprocess()

    def _preprocess(self):
        df = self.df
        df["proposed_at"] = pd.to_datetime(df["proposed_at"], errors="coerce")
        df["hour"] = df["proposed_at"].dt.hour
        df["month"] = df["proposed_at"].dt.to_period("M").astype(str)
        df["city_normalized"] = df["city"].str.strip().str.upper()
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
            "success_rate": round(status_counts.get("success", 0) / total * 100, 2),
            "failure_rate": round(status_counts.get("failed", 0) / total * 100, 2),
        }

    def by_payment_source(self) -> list[dict]:
        df = self.df
        grouped = df.groupby("payment_source")["payment_status"].value_counts().unstack(fill_value=0)
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
            .groupby("city_normalized")
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
            .groupby("country_code")
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
            df.groupby(["hour", "payment_status"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        return hourly.to_dict(orient="records")

    def by_month(self) -> list[dict]:
        df = self.df
        monthly = (
            df.groupby(["month", "payment_status"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        return monthly.to_dict(orient="records")

    def by_card_brand(self) -> list[dict]:
        df = self.df
        brands = (
            df[df["card_brand"].notna() & (df["card_brand"] != "NULL")]
            .groupby("card_brand")["payment_status"]
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
