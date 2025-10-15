import pandas as pd

def summarize(base: pd.DataFrame, chosen: pd.DataFrame) -> pd.DataFrame:
    df = base.merge(chosen[["sku", "opt_price", "opt_qty", "opt_profit"]], on="sku")
    df["base_profit"] = (df["base_price"] - df["cost"]) * df["base_units"]
    df["delta_profit"] = df["opt_profit"] - df["base_profit"]
    df["delta_price_pct"] = (df["opt_price"] / df["base_price"] - 1.0) * 100
    return df.sort_values("delta_profit", ascending=False)
