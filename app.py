import streamlit as st
import pandas as pd
import altair as alt

CSV_PATH = "scores.csv"

st.set_page_config(page_title="Prediction League Tracker", layout="wide")
st.title("⚽ Prediction League Tracker")


@st.cache_data
def load_data(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values(["user", "date"])
    return df


df = load_data(CSV_PATH)

if df.empty:
    st.info("No data found in scores.csv yet.")
    st.stop()

users = sorted(df["user"].unique())

# --- Sidebar filters ---
st.sidebar.header("Filters")
selected_users = st.sidebar.multiselect(
    "Players to show", options=users, default=users
)

date_min, date_max = df["date"].min(), df["date"].max()
date_range = st.sidebar.date_input(
    "Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max
)

if len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
else:
    start_date, end_date = date_min, date_max

filtered = df[
    (df["user"].isin(selected_users))
    & (df["date"] >= start_date)
    & (df["date"] <= end_date)
]

if filtered.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# --- Line chart: cumulative points over time ---
st.header("📈 Cumulative points over time")

line_chart = (
    alt.Chart(filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("cumulative_points:Q", title="Cumulative points"),
        color=alt.Color("user:N", title="Player"),
        tooltip=["user", "date:T", "cumulative_points"],
    )
    .properties(height=500)
    .interactive()
)

st.altair_chart(line_chart, use_container_width=True)

# --- Heatmap: points gained per period ---
st.header("🔥 Points gained per period")

# Compute points gained between consecutive dates per user
gains = filtered.copy()
gains["points_gained"] = gains.groupby("user")["cumulative_points"].diff()

# First entry per user has no previous value to diff against, so gains is NaN.
# Drop those rows from the heatmap (no "gain" can be computed for the first date).
gains = gains.dropna(subset=["points_gained"])

if gains.empty:
    st.info("Need at least two dates per player to compute points gained.")
else:
    heatmap = (
        alt.Chart(gains)
        .mark_rect()
        .encode(
            x=alt.X("date:O", title="Date"),
            y=alt.Y("user:N", title="Player", sort=users),
            color=alt.Color(
                "points_gained:Q",
                title="Points gained",
                scale=alt.Scale(scheme="yelloworangered"),
            ),
            tooltip=["user", "date:T", "points_gained"],
        )
        .properties(height=max(300, 20 * len(selected_users)))
    )

    st.altair_chart(heatmap, use_container_width=True)

# --- Raw data ---
with st.expander("📋 Raw data"):
    st.dataframe(filtered, use_container_width=True)