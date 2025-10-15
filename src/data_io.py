import pandas as pd

def load_sales(path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.dropna(subset=["sku", "price", "units", "cost"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["units"] = pd.to_numeric(df["units"], errors="coerce")
    df["cost"]  = pd.to_numeric(df["cost"],  errors="coerce")
    df = df.dropna(subset=["price", "units", "cost"])
    df = df[df["price"] > 0]
    df["rev"] = df["price"] * df["units"]
    df["margin_unit"] = df["price"] - df["cost"]
    return df

def latest_baseline(df: pd.DataFrame) -> pd.DataFrame:
    latest_mask = df.groupby("sku")["date"].transform("max") == df["date"]
    base = (
        df[latest_mask]
        .groupby("sku", as_index=False)
        .agg(
            base_price=("price", "mean"),
            base_units=("units", "mean"),
            cost=("cost", "mean"),
        )
    )
    return base
