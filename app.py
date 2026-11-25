import plotly.graph_objects as go
import streamlit as st

from census_data import BOUNDARY_URL, COUNTIES, METRICS, load_data


def format_value(value, spec):
    if value is None:
        return "Unavailable"
    return "$" + format(value, spec[1:]) if spec.startswith("$") else format(value, spec)


def county_map(rows, boundaries, metric, spec):
    figure = go.Figure()
    for available in (True, False):
        group = [row for row in rows if (row[metric] is not None) == available]
        if not group:
            continue
        figure.add_trace(go.Choroplethmap(
            geojson=boundaries,
            locations=[row["fips"] for row in group],
            z=[row[metric] if available else 0 for row in group],
            customdata=[[row["county"], format_value(row[metric], spec)] for row in group],
            hovertemplate="%{customdata[0]} County<br>%{customdata[1]}<extra></extra>",
            colorscale="Teal" if available else [[0, "#a3aab5"], [1, "#a3aab5"]],
            showscale=available,
            colorbar={"tickformat": spec, "thickness": 12},
            marker={"line": {"color": "white", "width": 2}},
        ))
    figure.update_layout(
        map={"style": "white-bg", "center": {"lat": 36.18, "lon": -93.88}, "zoom": 6.6},
        margin={"t": 0, "l": 0, "r": 0, "b": 0},
        height=390,
    )
    return figure


def comparison(rows, metric, label, spec):
    ranked = sorted((row for row in rows if row[metric] is not None), key=lambda row: row[metric])
    figure = go.Figure(go.Bar(
        x=[row[metric] for row in ranked],
        y=[row["county"] for row in ranked],
        orientation="h",
        marker_color="#147d78",
        text=[format_value(row[metric], spec) for row in ranked],
        hovertemplate="%{y} County<br>%{text}<extra></extra>",
    ))
    figure.update_layout(
        xaxis={"title": label, "tickformat": spec, "rangemode": "tozero"},
        height=390,
        margin={"t": 12, "l": 0, "r": 12, "b": 0},
    )
    return figure


st.set_page_config(page_title="Northwest Arkansas County Explorer", layout="wide")
st.title("Northwest Arkansas County Explorer")
st.caption("2020–2024 American Community Survey 5-year estimates · 2024 Census county boundaries")

with st.sidebar:
    st.header("Explore the data")
    metric = st.selectbox("Demographic measure", list(METRICS), format_func=lambda key: METRICS[key][0])
    counties = st.multiselect("Counties", list(COUNTIES.values()), default=list(COUNTIES.values()))

try:
    with st.spinner("Loading Census data. The first download may take a minute."):
        data = load_data()
except Exception as error:
    st.error("Couldn’t load the Census data. Check your internet connection and try again.")
    st.caption(str(error))
    if st.button("Retry download"):
        st.rerun()
    st.stop()

rows = [row for row in data["rows"] if row["county"] in counties]
if not rows:
    st.info("Select at least one county to see the map and chart.")
    st.stop()

label, _, _, spec = METRICS[metric]
map_column, chart_column = st.columns(2)
with map_column:
    st.subheader(f"{label} by county")
    st.plotly_chart(county_map(rows, data["boundaries"], metric, spec), config={"scrollZoom": True})
with chart_column:
    st.subheader("County comparison")
    if any(row[metric] is not None for row in rows):
        st.plotly_chart(comparison(rows, metric, label, spec))
    else:
        st.info("The selected measure is unavailable for these counties.")

st.subheader("County estimates")
st.dataframe(
    [{"County": row["county"], **{name: row[key] for key, (name, _, _, _) in METRICS.items()}}
     for row in rows],
    column_config={name: st.column_config.NumberColumn(
                       format={"$,.0f": "dollar", ".1%": "percent", ",.0f": "localized", ".1f": "%.1f"}[fmt])
                   for name, _, _, fmt in METRICS.values()},
    hide_index=True,
)
st.caption("Blank cells and gray map areas indicate unavailable estimates.")

with st.expander("Sources and measure definitions"):
    st.markdown(f"""
- **Population** counts all residents (B01003). **Median age** is reported in years (B01002).
- **Median household income** uses 2024 inflation-adjusted dollars (B19013).
- **Bachelor’s degree or higher** is the share of people age 25 and older with a bachelor’s,
  master’s, professional, or doctorate degree (B15003).
- **Poverty rate** is the share of people below the poverty line among people for whom poverty
  status was determined (B17001).
- **Median home value** covers owner-occupied housing units and is reported in dollars (B25077).
- These are survey estimates pooled over five years. The charts display point estimates.

[U.S. Census Bureau ACS Summary Files](https://www.census.gov/programs-surveys/acs/data/summary-file.html)
· [2024 county boundaries]({BOUNDARY_URL})
""")
