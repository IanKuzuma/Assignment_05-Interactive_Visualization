import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="What Makes a Hit? | Video Game Sales Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── LOAD & CLEAN DATA ────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("Video_Games_Sales_as_at_22_Dec_2016.csv")
    df = df.dropna(subset=["Name", "Genre", "Critic_Score", "Global_Sales"])
    df["Year_of_Release"] = df["Year_of_Release"].fillna(0).astype(int)
    df = df[df["Year_of_Release"] > 0]
    df["User_Score"] = pd.to_numeric(df["User_Score"], errors="coerce")
    # Normalize user score to 0-100 scale (originally 0-10)
    df["User_Score_100"] = df["User_Score"] * 10
    df["Rating"] = df["Rating"].fillna("Unknown")
    df["Publisher"] = df["Publisher"].fillna("Unknown")
    df["Developer"] = df["Developer"].fillna("Unknown")
    return df

df = load_data()

# ── SIDEBAR FILTERS ──────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# Year range
year_min, year_max = int(df["Year_of_Release"].min()), int(df["Year_of_Release"].max())
year_range = st.sidebar.slider(
    "Release Year Range",
    min_value=year_min,
    max_value=year_max,
    value=(1996, 2016),
)

# Genre
all_genres = sorted(df["Genre"].unique())
selected_genres = st.sidebar.multiselect(
    "Genre",
    options=all_genres,
    default=all_genres,
)

# Region toggle
region = st.sidebar.radio(
    "Sales Region",
    options=["Global", "North America", "Europe", "Japan", "Other"],
    index=0,
)
region_col_map = {
    "Global": "Global_Sales",
    "North America": "NA_Sales",
    "Europe": "EU_Sales",
    "Japan": "JP_Sales",
    "Other": "Other_Sales",
}
sales_col = region_col_map[region]

# Platform filter (group the 31 platforms into major ones + Other)
top_platforms = (
    df.groupby("Platform")["Global_Sales"]
    .sum()
    .sort_values(ascending=False)
    .head(12)
    .index.tolist()
)
selected_platforms = st.sidebar.multiselect(
    "Platform (top 12 by sales)",
    options=top_platforms,
    default=top_platforms,
)

# ESRB rating
all_ratings = sorted(df["Rating"].unique())
selected_ratings = st.sidebar.multiselect(
    "ESRB Rating",
    options=all_ratings,
    default=all_ratings,
)

# Score type toggle
score_type = st.sidebar.radio(
    "Score Axis",
    options=["Critic Score", "User Score"],
    index=0,
)
score_col = "Critic_Score" if score_type == "Critic Score" else "User_Score_100"

# ── FILTER DATA ──────────────────────────────────────────────────────────────
filtered = df[
    (df["Year_of_Release"] >= year_range[0])
    & (df["Year_of_Release"] <= year_range[1])
    & (df["Genre"].isin(selected_genres))
    & (df["Platform"].isin(selected_platforms))
    & (df["Rating"].isin(selected_ratings))
].copy()

# Drop rows missing the selected score
filtered = filtered.dropna(subset=[score_col])

# ── HEADER ───────────────────────────────────────────────────────────────────
st.title("🎮 What Makes a Hit?")
st.markdown(
    "Explore the relationship between critic/user reviews, sales, genres, "
    "and platforms across decades of video game history."
)

# ── METRICS ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Games Shown", f"{len(filtered):,}")
col2.metric(f"Avg {score_type}", f"{filtered[score_col].mean():.1f}")
col3.metric(f"Total {region} Sales", f"{filtered[sales_col].sum():.1f}M units")
col4.metric("Avg Sales/Game", f"{filtered[sales_col].mean():.2f}M units")

st.divider()

# ── MAIN SCATTER PLOT ────────────────────────────────────────────────────────
st.markdown(f"#### {score_type} vs {region} Sales by Genre")

fig_scatter = px.scatter(
    filtered,
    x=score_col,
    y=sales_col,
    color="Genre",
    size="Global_Sales",
    size_max=40,
    hover_name="Name",
    hover_data={
        "Platform": True,
        "Publisher": True,
        "Year_of_Release": True,
        score_col: ":.1f",
        sales_col: ":.2f",
        "Global_Sales": False,
    },
    log_y=True,
    labels={
        score_col: score_type,
        sales_col: f"{region} Sales (M units)",
        "Genre": "Genre",
    },
    opacity=0.6,
)

fig_scatter.update_layout(
    title=dict(text=f"{score_type} vs {region} Sales by Genre", x=0.5, xanchor="center"),
    height=550,
    template="plotly_dark",
    paper_bgcolor="#1c1c1c",
    plot_bgcolor="#1c1c1c",
    font=dict(color="#ccccee"),
    margin=dict(l=60, r=40, t=80, b=50),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.0,
        xanchor="center",
        x=0.5,
        font=dict(size=11),
    ),
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ── BOTTOM SECTION: TWO COORDINATED CHARTS ───────────────────────────────────
left_col, right_col = st.columns(2)

with left_col:
    # Top publishers by sales in current filter
    pub_sales = (
        filtered.groupby("Publisher")[sales_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    pub_sales.columns = ["Publisher", "Sales"]

    fig_pub = px.bar(
        pub_sales,
        x="Sales",
        y="Publisher",
        orientation="h",
        labels={"Sales": f"{region} Sales (M units)"},
        color="Sales",
        color_continuous_scale="Teal",
    )
    fig_pub.update_layout(
        title=dict(text=f"Top 10 Publishers by {region} Sales", x=0.5, xanchor="center"),
        height=400,
        template="plotly_dark",
        paper_bgcolor="#1c1c1c",
        plot_bgcolor="#1c1c1c",
        font=dict(color="#ccccee"),
        margin=dict(l=10, r=30, t=50, b=40),
        showlegend=False,
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_pub, use_container_width=True)

with right_col:
    # Average score by genre
    genre_scores = (
        filtered.groupby("Genre")
        .agg(
            avg_score=(score_col, "mean"),
            avg_sales=(sales_col, "mean"),
            count=("Name", "count"),
        )
        .reset_index()
        .sort_values("avg_score", ascending=False)
    )

    fig_genre = px.bar(
        genre_scores,
        x="avg_score",
        y="Genre",
        orientation="h",
        labels={"avg_score": f"Avg {score_type}", "Genre": "Genre"},
        color="avg_sales",
        color_continuous_scale="Sunset",
        hover_data={"count": True, "avg_sales": ":.2f"},
    )
    fig_genre.update_layout(
        title=dict(text=f"Average {score_type} by Genre", x=0.5, xanchor="center"),
        height=400,
        template="plotly_dark",
        paper_bgcolor="#1c1c1c",
        plot_bgcolor="#1c1c1c",
        font=dict(color="#ccccee"),
        margin=dict(l=10, r=30, t=50, b=40),
        showlegend=False,
        coloraxis_colorbar=dict(title="Avg Sales (M)"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_genre, use_container_width=True)

# ── DATA TABLE ───────────────────────────────────────────────────────────────
with st.expander("Show filtered data"):
    display_cols = [
        "Name", "Platform", "Year_of_Release", "Genre", "Publisher",
        "Critic_Score", "User_Score", "Rating",
        "NA_Sales", "EU_Sales", "JP_Sales", "Global_Sales",
    ]
    st.dataframe(
        filtered[display_cols].sort_values("Global_Sales", ascending=False),
        use_container_width=True,
        height=400,
    )

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()

st.header("Write-Up")

st.subheader("Question")
st.markdown(
    """
    The question I'm trying to answer with this visualization is: do better-reviewed
    video games actually sell more, and how does that relationship change depending on
    the genre, the platform, the region, and the time period? I think it's a genuinely
    interesting question because on the surface it seems like the answer should
    obviously be yes, but when you actually look at the data it's way more complicated
    than that. Some genres like Sports and Action absolutely dominate total sales
    despite having pretty average review scores, while niche genres like Strategy
    score really well with critics but barely move units. I wanted to build something
    that lets you explore those patterns yourself rather than just showing you one
    static chart and calling it a day.
    """
)

st.subheader("Design Rationale")
st.markdown(
    """
    The main visualization is a scatter plot with critic (or user) score on the
    x-axis and sales on the y-axis, colored by genre. I went with a scatter plot
    because the core question is about the relationship between two continuous
    variables, and honestly there's no better chart type for that. The y-axis uses
    a log scale because the sales data is extremely right-skewed, a handful of games
    sell 20M+ units while the vast majority sell under 0.5M, and without the log
    scale everything just gets compressed into a tiny cluster at the bottom which
    is completely unreadable. Bubble size encodes global sales so you can still get
    a sense of each game's overall market impact even when you're looking at regional
    sales. Genre is mapped to color because it's the most interesting categorical
    variable for this question, and Plotly's legend conveniently lets you click to
    isolate individual genres which I think is a really neat interaction.

    For the sidebar, I chose a year range slider instead of a single year dropdown
    because trends in the score-to-sales relationship are way more visible across
    spans of time than in any individual year. The region toggle is probably the most
    interesting filter, it lets you switch the sales axis between NA, EU, Japan, and
    Global, and it reveals how the same games perform very differently across markets.
    For instance RPGs absolutely dominate Japan but lag behind in NA, which you can
    see immediately when you flip between the two. I considered using a dropdown for
    platforms but there are 31 of them in the dataset which is way too many, so I
    pre-filtered to the top 12 by total sales to keep the control usable.

    The two bottom charts are coordinated with the same sidebar filters to give
    supporting context. The publisher bar chart answers "who's winning in the current
    view?" and the genre score chart answers "which genres are best-reviewed?" with
    the bar color encoding average sales as a second dimension. I considered adding a
    time series line chart as a third view, but decided it would make the whole
    dashboard feel too sprawling and unfocused, which is exactly what the assignment
    told us to avoid. The year range slider already lets you explore temporal patterns
    through the scatter plot anyway so I felt like it was redundant.

    The dark theme was a deliberate choice because I think it fits the gaming
    aesthetic and it's just easier on the eyes during extended exploration sessions.
    """
)

st.subheader("References")
st.markdown(
    """
    - **Dataset:** [Video Game Sales with Ratings](https://www.kaggle.com/datasets/rush4ratio/video-game-sales-with-ratings) by Rush Kirubi on Kaggle. The dataset contains around 16,700 video games with sales data sourced from VGChartz and review scores from Metacritic, compiled as of December 2016.
    - **Tools:** Built with [Streamlit](https://streamlit.io/) for the web framework and [Plotly Express](https://plotly.com/python/plotly-express/) for the interactive charts. Deployed via Streamlit Cloud.
    """
)

st.subheader("Development Process")
st.markdown(
    """
    I spent roughly 8 to 10 hours developing this application. The breakdown was
    approximately 1 to 2 hours on dataset selection and initial exploration (I went
    through a few gaming datasets before settling on this one because it had both
    critic and user scores alongside regional sales data which is exactly what I
    needed), 3 to 4 hours on building and iterating on the Streamlit app itself
    (getting the filters, chart layouts, and coordinated views all working together
    properly), 2 hours on visual polish and the dark theme styling, and 1 to 2 hours
    on writing this write-up and deploying to Streamlit Cloud.

    The aspect that took the most time was honestly getting the sidebar filters to
    play nicely together without creating weird empty states. For example when you
    filter to a really narrow year range and a single niche genre, sometimes there
    are barely any data points left, and the charts need to handle that gracefully
    instead of just breaking or showing empty axes. I also spent a lot of time tuning
    the scatter plot specifically, things like the opacity, the size scaling, and the
    hover data, because when you have thousands of overlapping points it can get
    really messy really fast. The log scale on the y-axis was actually a late decision
    that dramatically improved the readability of the whole thing.
    """
)
