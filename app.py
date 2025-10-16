import streamlit as st
import pandas as pd

from src.data_io import load_sales, latest_baseline
from src.demand import estimate_elasticity
from src.optimize import solve_prices
from src.report import summarize

st.set_page_config(page_title="AI based Price Optimization", layout="wide")
st.title("🧮AI Price Optimization")

data_file = st.file_uploader("Upload sales CSV with columns: date, sku, price, units, cost", type=["csv"])

try:
    if data_file is None:
        st.info("No file uploaded — using bundled sample data.")
        df = load_sales("data/sales_sample.csv")
    else:
        df = load_sales(data_file)
except Exception as e:
    st.error(f"Could not read the CSV. Check columns and types. Details: {e}")
    st.stop()

st.subheader("1) Sales preview")
st.dataframe(df.head(20), use_container_width=True)

# --- robust KPIs (works across pandas versions) ---
total_revenue = float(df["rev"].sum()) if "rev" in df.columns else 0.0
total_units   = float(df["units"].sum()) if "units" in df.columns else 0.0

c1, c2 = st.columns(2)
c1.metric("Total Revenue", f"{total_revenue:.0f}")
c2.metric("Total Units",   f"{total_units:.0f}")

st.subheader("2) Elasticity (price sensitivity)")
elas = estimate_elasticity(df)
st.dataframe(elas, use_container_width=True)

st.subheader("3) Baseline (latest prices & units)")
base = latest_baseline(df)
if base.empty:
    st.warning("Baseline is empty. Check your data file.")
    st.stop()
st.dataframe(base, use_container_width=True)

st.subheader("4) Rules")
lb = st.slider("Lowest price (% of baseline)", 50, 100, 70)
ub = st.slider("Highest price (% of baseline)", 100, 200, 130)
min_margin = st.slider("Minimum margin over cost (%)", 0, 50, 5)

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
        st.success("Done. One best price per SKU selected.")
        st.dataframe(rep, use_container_width=True)
        st.download_button(
            "Download price book (CSV)",
            rep.to_csv(index=False),
            file_name="price_book.csv",
            mime="text/csv"
        )

st.caption("Tip: If you upload your own data, keep columns exactly: date, sku, price, units, cost.")

