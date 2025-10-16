import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_io import load_sales, latest_baseline
from src.demand import estimate_elasticity
from src.optimize import solve_prices
from src.report import summarize

st.set_page_config(page_title="AI based Price Optimization", layout="wide")
st.title("🧮 AI Price Optimization")

data_file = st.file_uploader(
    "Upload sales CSV with columns: date, sku, price, units, cost",
    type=["csv"]
)

# -------------------- Load Data --------------------
try:
    if data_file is None:
        st.info("No file uploaded — using bundled sample data.")
        df = load_sales("data/sales_sample.csv")
    else:
        df = load_sales(data_file)
except Exception as e:
    st.error(f"Could not read the CSV. Check columns and types. Details: {e}")
    st.stop()

# -------------------- Preview & KPIs --------------------
st.subheader("1) Sales preview")
st.dataframe(df.head(20), use_container_width=True)

total_revenue = float(df["rev"].sum()) if "rev" in df.columns else 0.0
total_units   = float(df["units"].sum()) if "units" in df.columns else 0.0
c1, c2 = st.columns(2)
c1.metric("Total Revenue", f"{total_revenue:.0f}")
c2.metric("Total Units",   f"{total_units:.0f}")

# -------------------- Elasticity --------------------
st.subheader("2) Elasticity (price sensitivity)")
elas = estimate_elasticity(df)
st.dataframe(elas, use_container_width=True)

# -------------------- Demand Curve (Plotly) --------------------
st.subheader("3) Demand Curve (Price vs Quantity Sold)")
selected_sku = st.selectbox("Select SKU to visualize", df["sku"].unique())
sku_data = df[df["sku"] == selected_sku].sort_values("price")

fig_demand = px.line(
    sku_data,
    x="price",
    y="units",
    markers=True,
    title=f"Demand Curve for {selected_sku}",
    labels={"price": "Price", "units": "Units Sold"}
)
st.plotly_chart(fig_demand, use_container_width=True)

# -------------------- Baseline --------------------
st.subheader("4) Baseline (latest prices & units)")
base = latest_baseline(df)
if base.empty:
    st.warning("Baseline is empty. Check your data file.")
    st.stop()
st.dataframe(base, use_container_width=True)

# -------------------- Rules --------------------
st.subheader("5) Rules")
lb = st.slider("Lowest price (% of baseline)", 50, 100, 70)
ub = st.slider("Highest price (% of baseline)", 100, 200, 130)
min_margin = st.slider("Minimum margin over cost (%)", 0, 50, 5)

rep = pd.DataFrame()  # predeclare so we can safely check later

# -------------------- Solve --------------------
if st.button("✨ Solve for best prices"):
    chosen = solve_prices(
        base, elas,
        price_bounds_pct=(lb / 100.0, ub / 100.0),
        min_margin_pct=min_margin / 100.0
    )
    if chosen.empty:
        st.error("No solution found with the current settings. Try widening the price range or lowering min margin.")
    else:
        rep = summarize(base, chosen)
        # Make quantities integers for realism
        if "opt_qty" in rep.columns:
            rep["opt_qty"] = rep["opt_qty"].round().astype(int)
        if "base_units" in rep.columns:
            rep["base_units"] = rep["base_units"].round().astype(int)

        st.success("Done. One best price per SKU selected.")
        st.dataframe(rep, use_container_width=True)

        # Download button lives with the results
        st.download_button(
            "Download price book (CSV)",
            rep.to_csv(index=False),
            file_name="price_book.csv",
            mime="text/csv"
        )

        # -------------------- Profit Curve (Plotly) --------------------
        st.subheader("6) Profit Curve (Optimized Range)")
        sku = st.selectbox("Select SKU to view profit curve", rep["sku"].unique(), key="profit_curve_sku")
        sku_row = rep[rep["sku"] == sku].iloc[0]

        base_price = float(sku_row["base_price"])
        opt_price  = float(sku_row["opt_price"])
        base_units = float(sku_row["base_units"])
        elasticity = float(elas.loc[elas["sku"] == sku, "elasticity"].values[0])
        cost       = float(sku_row["cost"])

        prices = np.linspace(base_price * 0.7, base_price * 1.3, 25)
        quantities = base_units * (prices / base_price) ** elasticity
        profits = (prices - cost) * quantities

        fig_profit = go.Figure()
        fig_profit.add_trace(go.Scatter(x=prices, y=profits, mode="lines", name="Profit"))
        fig_profit.add_vline(
            x=opt_price, line_dash="dash", line_color="red",
            annotation_text="Optimized Price", annotation_position="top right"
        )
        fig_profit.update_layout(title=f"Profit Curve for {sku}", xaxis_title="Price", yaxis_title="Profit")
        st.plotly_chart(fig_profit, use_container_width=True)

        # -------------------- Baseline vs Optimized Profit (Plotly) --------------------
        st.subheader("7) Baseline vs Optimized Profit Comparison")
        rep_plot = rep.copy()
        rep_plot["Base Profit"] = (rep_plot["base_price"] - rep_plot["cost"]) * rep_plot["base_units"]
        rep_plot["Optimized Profit"] = rep_plot["opt_profit"]

        plot_data = rep_plot.melt(
            id_vars=["sku"],
            value_vars=["Base Profit", "Optimized Profit"],
            var_name="Type",
            value_name="Profit"
        )

        fig_bar = px.bar(
            plot_data, x="sku", y="Profit", color="Type", barmode="group",
            title="Baseline vs Optimized Profit per SKU"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

st.caption("Tip: If you upload your own data, keep columns exactly: date, sku, price, units, cost.")

