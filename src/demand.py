import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

def estimate_elasticity(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sku, g in df.groupby("sku"):
        g = g[(g["units"] > 0) & (g["price"] > 0)]
        if len(g) < 3:
            out.append({"sku": sku, "elasticity": -1.0})
            continue
        X = np.log(g["price"].values).reshape(-1, 1)
        y = np.log(g["units"].values)
        lr = LinearRegression().fit(X, y)
        out.append({"sku": sku, "elasticity": float(lr.coef_[0])})
    return pd.DataFrame(out)

def demand_at_price(base_units, base_price, elasticity, new_price):
    return base_units * (new_price / base_price) ** elasticity
