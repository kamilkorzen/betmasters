import streamlit as st
import pandas as pd
import altair as alt
import os

SCORES_PATH = "scores.csv"
MATCHES_PATH = "matches.csv"

st.set_page_config(page_title="Betmasters 2026", layout="wide")
st.title("Betmasters 2026 | update daily at 12:00")


# --- Loaders ---
@st.cache_data
def load_scores(path):
    df = pd.read_csv(path)
    df["date"] = df["date"].astype(str).str.strip().str.strip("'\"")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["cumulative_points"] = pd.to_numeric(df["cumulative_points"], errors="coerce")
    df = df.sort_values(["user", "date"]).dropna(subset=["cumulative_points"])
    return df


@st.cache_data
def load_matches(path):
    df = pd.read_csv(path)
    df["date"] = df["date"].astype(str).str.strip().str.strip("'\"")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["matches_played"] = pd.to_numeric(df["matches_played"], errors="coerce")
    df = df.sort_values("date").dropna(subset=["matches_played"])
    return df


df = load_scores(SCORES_PATH)
has_matches = os.path.exists(MATCHES_PATH)
matches_df = load_matches(MATCHES_PATH) if has_matches else pd.DataFrame()

if df.empty:
    st.info("No data found in scores.csv yet.")
    st.stop()

users = sorted(df["user"].unique())

# Calculate daily gains on full dataset before filtering
df["points_gained"] = df.groupby("user")["cumulative_points"].diff()

# Latest standings (last row per user = latest date)
latest = df.groupby("user").last().reset_index()
top_player = latest.sort_values("cumulative_points", ascending=False)["user"].iloc[0]

# --- Sidebar ---
st.sidebar.header("Filters")
selected_users = st.sidebar.multiselect("Players to show", options=users, default=users)

date_min, date_max = df["date"].min(), df["date"].max()
date_range = st.sidebar.date_input(
    "Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max
)
start_date, end_date = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_min, date_max)

filtered = df[
    df["user"].isin(selected_users)
    & (df["date"] >= start_date)
    & (df["date"] <= end_date)
]

if filtered.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# Standings for selected users (latest points)
standings = (
    latest[latest["user"].isin(selected_users)]
    .sort_values("cumulative_points", ascending=False)
    .reset_index(drop=True)
)

# --- Summary metrics (top 5) ---
cols = st.columns(min(5, len(standings)))
for i, row in standings.head(5).iterrows():
    cols[i].metric(f"#{i+1} {row['user']}", f"{int(row['cumulative_points'])} pts")

st.divider()

# --- 1. Cumulative points over time ---
st.subheader("📈 Cumulative points over time")
line = (
    alt.Chart(filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("date:T", title="Date", axis=alt.Axis(format="%Y-%m-%d")),
        y=alt.Y("cumulative_points:Q", title="Cumulative points"),
        color=alt.Color("user:N", title="Player"),
        tooltip=["user", alt.Tooltip("date:T", format="%Y-%m-%d"), "cumulative_points:Q"],
    )
)
st.altair_chart(line, use_container_width=True)

# --- 2. Points gained heatmap ---
st.subheader("🔥 Points gained per round")
gains_data = filtered.dropna(subset=["points_gained"]).copy()
# Convert date to string to force clean formatting on the Ordinal axis
gains_data["date_str"] = gains_data["date"].apply(lambda x: x.strftime("%Y-%m-%d"))

user_order = standings["user"].tolist()

if not gains_data.empty:
    hm = (
        alt.Chart(gains_data)
        .mark_rect()
        .encode(
            x=alt.X("date_str:O", title="Date", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("user:N", title="Player", sort=user_order, axis=alt.Axis(labelLimit=0)),
            color=alt.Color(
                "points_gained:Q",
                title="Points gained",
                scale=alt.Scale(scheme="yelloworangered"),
            ),
            tooltip=["user", alt.Tooltip("date_str:N", title="Date"), "points_gained:Q"],
        )
        .properties(height=max(300, 24 * len(selected_users)))
    )
    st.altair_chart(hm, use_container_width=True)

# --- 3. Rankings over time (bump chart) ---
st.subheader("🏅 Rankings over time")
st.caption("Each player's league position at every checkpoint — lines crossing = an overtake.")
rank_df = filtered.copy()
rank_df["rank"] = (
    rank_df.groupby("date")["cumulative_points"]
    .rank(ascending=False, method="min")
    .astype(int)
)
n_players = len(selected_users)

bump = (
    alt.Chart(rank_df)
    .mark_line(point=True, strokeWidth=2)
    .encode(
        x=alt.X("date:T", title="Date", axis=alt.Axis(format="%Y-%m-%d")),
        y=alt.Y(
            "rank:Q",
            title="Position",
            scale=alt.Scale(domain=[n_players + 0.5, 0.5]),
            axis=alt.Axis(tickMinStep=1),
        ),
        color=alt.Color("user:N", title="Player"),
        tooltip=[
            "user",
            alt.Tooltip("date:T", format="%Y-%m-%d"),
            alt.Tooltip("rank:Q", title="Position"),
            "cumulative_points:Q",
        ],
    )
)
st.altair_chart(bump, use_container_width=True)

# --- 4. Head-to-head gap ---
st.subheader("🆚 Head-to-head gap")
c1, c2 = st.columns(2)
with c1:
    player_a = st.selectbox("Player A", options=users, index=0)
with c2:
    default_b = top_player if top_player != player_a else (users[1] if len(users) > 1 else users[0])
    player_b = st.selectbox("Player B (reference)", options=users, index=users.index(default_b))

comp_a = df[df["user"] == player_a][["date", "cumulative_points"]].rename(columns={"cumulative_points": "pts_a"})
comp_b = df[df["user"] == player_b][["date", "cumulative_points"]].rename(columns={"cumulative_points": "pts_b"})
comp = pd.merge(comp_a, comp_b, on="date", how="outer").sort_values("date").ffill()
comp["diff"] = comp["pts_a"] - comp["pts_b"]
comp["diff_pos"] = comp["diff"].clip(lower=0)
comp["diff_neg"] = comp["diff"].clip(upper=0)
comp["date"] = pd.to_datetime(comp["date"])

area_pos = alt.Chart(comp).mark_area(opacity=0.35, color="#2ecc71").encode(
    x=alt.X("date:T", title="Date", axis=alt.Axis(format="%Y-%m-%d")),
    y=alt.Y("diff_pos:Q", title=f"Points gap ({player_a} − {player_b})"),
    y2=alt.Y2(datum=0),
)
area_neg = alt.Chart(comp).mark_area(opacity=0.35, color="#e74c3c").encode(
    x=alt.X("date:T", axis=alt.Axis(format="%Y-%m-%d")),
    y="diff_neg:Q",
    y2=alt.Y2(datum=0),
)
line_diff = alt.Chart(comp).mark_line(color="#333", strokeWidth=1.5).encode(
    x=alt.X("date:T", axis=alt.Axis(format="%Y-%m-%d")),
    y="diff:Q",
    tooltip=[alt.Tooltip("date:T", format="%Y-%m-%d"), alt.Tooltip("diff:Q", title="Gap")],
)
zero_rule = (
    alt.Chart(pd.DataFrame({"y": [0]}))
    .mark_rule(strokeDash=[5, 3], color="#888", strokeWidth=1)
    .encode(y="y:Q")
)

st.caption(f"Green = **{player_a}** ahead · Red = **{player_b}** ahead")
st.altair_chart((area_pos + area_neg + line_diff + zero_rule), use_container_width=True)

# --- 5. Points per match (efficiency) ---
if not matches_df.empty:
    st.subheader("🎯 Points per match (efficiency)")
    st.caption("Points gained on a specific date divided by matches played on that date (PPG).")
    
    # Merge daily gains with match counts
    ppm = pd.merge(filtered.dropna(subset=["points_gained"]), matches_df, on="date", how="inner")
    ppm = ppm[ppm["matches_played"] > 0]

    if not ppm.empty:
        ppm["ppg"] = ppm["points_gained"] / ppm["matches_played"]
        ppm_chart = (
            alt.Chart(ppm)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date", axis=alt.Axis(format="%Y-%m-%d")),
                y=alt.Y("ppg:Q", title="Points per match (PPG)"),
                color=alt.Color("user:N", title="Player"),
                tooltip=[
                    "user",
                    alt.Tooltip("date:T", format="%Y-%m-%d"),
                    alt.Tooltip("ppg:Q", format=".2f", title="PPG"),
                    alt.Tooltip("points_gained:Q", title="Points Gained"),
                    alt.Tooltip("matches_played:Q", title="Matches played"),
                ],
            )
        )
        st.altair_chart(ppm_chart, use_container_width=True)
else:
    st.info(
        "Add a `matches.csv` file (columns: `date, matches_played`) to unlock the points-per-match chart."
    )

# --- Raw data ---
with st.expander("📋 Raw data"):
    if not matches_df.empty:
        t1, t2 = st.tabs(["Scores", "Matches"])
        with t1:
            st.dataframe(filtered, use_container_width=True)
        with t2:
            st.dataframe(matches_df, use_container_width=True)
    else:
        st.dataframe(filtered, use_container_width=True)
