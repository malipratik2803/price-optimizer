import pandas as pd
import pulp
from .demand import demand_at_price

def _get_solver():
    try:
        return pulp.PULP_HIGHS_CMD(msg=False)   # uses highspy
    except Exception:
        pass
    try:
        return pulp.PULP_CBC_CMD(msg=False)
    except Exception:
        pass
    return None

def solve_prices(base: pd.DataFrame,
                 elas: pd.DataFrame,
                 price_bounds_pct=(0.7, 1.3),
                 min_margin_pct=0.05) -> pd.DataFrame:

    df = base.merge(elas, on="sku", how="left").fillna({"elasticity": -1.0})
    if df.empty:
        return pd.DataFrame(columns=["sku", "opt_price", "opt_qty", "opt_profit"])

    candidates = []
    for _, r in df.iterrows():
        pmin_floor = float(r["cost"]) * (1 + float(min_margin_pct))
        pmin_band  = float(r["base_price"]) * float(price_bounds_pct[0])
        pmin = max(pmin_floor, pmin_band)
        pmax = float(r["base_price"]) * float(price_bounds_pct[1])
        if pmax < pmin:
            pmax = pmin

        grid = sorted(set(round(pmin + (pmax - pmin) * i / 10, 2) for i in range(11)))
        for p in grid:
            q = demand_at_price(float(r["base_units"]), float(r["base_price"]),
                                float(r["elasticity"]), float(p))
            q = max(0.0, float(q))
            profit = (float(p) - float(r["cost"])) * q
            candidates.append({"sku": r["sku"], "price": p, "qty": q, "profit": profit})

    cand = pd.DataFrame(candidates)
    if cand.empty:
        return pd.DataFrame(columns=["sku", "opt_price", "opt_qty", "opt_profit"])

    prob = pulp.LpProblem("PriceOptimization", pulp.LpMaximize)
    x = {i: pulp.LpVariable(f"x_{i}", lowBound=0, upBound=1, cat="Binary") for i in cand.index}
    prob += pulp.lpSum(x[i] * cand.loc[i, "profit"] for i in x)

    for sku, g in cand.groupby("sku"):
        prob += pulp.lpSum(x[i] for i in g.index) == 1

    solver = _get_solver()
    prob.solve(solver) if solver is not None else prob.solve()

    chosen_idx = [i for i, var in x.items() if var.varValue == 1]
    chosen = cand.loc[chosen_idx].copy()
    chosen.rename(columns={"price": "opt_price", "qty": "opt_qty", "profit": "opt_profit"}, inplace=True)

    if chosen.empty:
        fallback = df[["sku", "base_price", "base_units", "cost"]].copy()
        fallback["opt_price"] = fallback["base_price"]
        fallback["opt_qty"]   = fallback["base_units"]
        fallback["opt_profit"]= (fallback["opt_price"] - fallback["cost"]) * fallback["opt_qty"]
        return fallback[["sku", "opt_price", "opt_qty", "opt_profit"]]

    return chosen[["sku", "opt_price", "opt_qty", "opt_profit"]]
