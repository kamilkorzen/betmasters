# Prediction League Tracker (viewer)

A read-only Streamlit app. You maintain `scores.csv` yourself (e.g. via your
own backend/repo sync); the app just visualises it.

## Data format

`scores.csv` needs exactly these columns:

```
user,date,cumulative_points
Alice,2026-01-10,5
Alice,2026-01-17,12
Bob,2026-01-10,3
Bob,2026-01-17,3
```

- `user`: player name (string)
- `date`: any date format pandas can parse (YYYY-MM-DD recommended)
- `cumulative_points`: running total for that player as of that date

Each player should ideally have one row per "checkpoint" date (e.g. weekly),
with `cumulative_points` being their total up to and including that date.
You don't need a row for every player on every date if data is missing, but
the heatmap "points gained" calc is a simple diff between consecutive rows
per player — if dates are irregular per player, the diff is still computed
between whatever rows exist for that player.

## What's shown

1. **Line chart** – cumulative points over time for every player (filterable
   by player and date range in the sidebar).
2. **Heatmap** – points gained (cumulative diff) per player per date. Useful
   to spot hot/cold streaks across ~20 players at a glance.

## Run locally

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push `app.py`, `requirements.txt`, and `scores.csv` to a GitHub repo.
2. Go to https://share.streamlit.io, "New app", point it at the repo and
   `app.py`.
3. To update data: just push a new `scores.csv` to the repo (overwrite the
   file). Streamlit Cloud auto-redeploys on push, and the app reloads with
   the new data (the `@st.cache_data` decorator caches per file content, but
   redeploy clears it anyway).

## Notes

- ~20 players works fine for both charts. The heatmap height auto-scales with
  the number of selected players.
- If your update cadence isn't weekly/regular, that's fine — the x-axis just
  uses whatever dates appear in the data.
