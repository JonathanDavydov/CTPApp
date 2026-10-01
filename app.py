import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Page configuration / styling
# -----------------------------
st.set_page_config(
    page_title="Movie Ratings Dashboard",
    page_icon="🎬",
    layout="wide",
)

COLORS = {
    "primary": "#4C78A8",
    "secondary": "#72B7B2",
    "accent": "#F58518",
    "reference": "#E45756",
    "muted": "#BDBDBD",
    "background": "#F7F9FC",
}

st.markdown(
    f"""
    <style>
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        .explanation {{
            background-color: {COLORS["background"]};
            border-left: 4px solid {COLORS["primary"]};
            border-radius: 4px;
            padding: 1rem 1.25rem;
            margin: 0.5rem 0 1rem 0;
            min-height: 120px;
        }}

        .placeholder {{
            color: #777;
            font-style: italic;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data loading
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("movie_ratings.csv")

    # Use the supplied column names exactly.
    required_columns = [
        "user_id",
        "movie_id",
        "rating",
        "timestamp",
        "title",
        "year",
        "genres",
    ]

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(
            f"movie_ratings.csv is missing these required columns: {missing}"
        )

    return df


df = load_data()


# -----------------------------
# General preprocessing
# -----------------------------
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

df = df.dropna(subset=["rating", "title", "year"])

# Split multi-genre movies into one row per movie-genre tag.
genre_df = df.assign(
    genre=df["genres"].fillna("").str.split("|")
).explode("genre")

genre_df["genre"] = genre_df["genre"].str.strip()
genre_df = genre_df[genre_df["genre"].ne("")]

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Filters")

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider(
    "Movie release year", year_min, year_max, (year_min, year_max)
)

genre_df = genre_df[genre_df["year"].between(*year_range)]
df = df[df["year"].between(*year_range)]

if df.empty:
    st.warning("No movies match the current filters.")
    st.stop()

# ============================================================
# SECTION 1 — Genre Breakdown
# ============================================================
st.header("1. Genre Breakdown")

st.markdown(
    """
    <div class="explanation">
        Movies with more than one genre are counted once under every genre they belong to, so a x-genre movie adds one to each of x different genre totals.
        <br><br>
        <span class="placeholder">
        This chart shows how many movie-genre tags each genre has, from most to least common.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

genre_counts = (
    genre_df.groupby("genre")
    .size()
    .reset_index(name="movie_genre_tags")
    .sort_values("movie_genre_tags", ascending=True)
)

fig_genre_breakdown = px.bar(
    genre_counts,
    x="movie_genre_tags",
    y="genre",
    orientation="h",
    labels={
        "movie_genre_tags": "Number of movie-genre tags",
        "genre": "Genre",
    },
    color_discrete_sequence=[COLORS["primary"]],
)

fig_genre_breakdown.update_layout(
    height=max(450, len(genre_counts) * 28),
    margin=dict(l=20, r=30, t=20, b=20),
    yaxis=dict(categoryorder="array", categoryarray=genre_counts["genre"]),
)

st.plotly_chart(fig_genre_breakdown, use_container_width=True)


# ============================================================
# SECTION 2 — Genre Satisfaction
# ============================================================
st.header("2. Genre Satisfaction")

overall_mean = df["rating"].mean()

genre_satisfaction = (
    genre_df.groupby("genre")
    .agg(
        average_rating=("rating", "mean"),
        rating_count=("rating", "size"),
    )
    .reset_index()
    .sort_values("average_rating", ascending=True)
)

# Highest and lowest genres are explicitly identified from
# the displayed data, without imposing an external ranking.
highest_genre = genre_satisfaction.loc[
    genre_satisfaction["average_rating"].idxmax()
]
lowest_genre = genre_satisfaction.loc[
    genre_satisfaction["average_rating"].idxmin()
]

st.markdown(
    f"""
    <div class="explanation">
        <p>
        This chart compares the average rating for each genre with the
        overall mean rating of <strong>{overall_mean:.2f}</strong>.
        The number shown beside each bar is the number of ratings contributing
        to that genre's average.
        </p>
        <p>
        <strong>Highest average:</strong>
        {highest_genre["genre"]} ({highest_genre["average_rating"]:.2f})
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <strong>Lowest average:</strong>
        {lowest_genre["genre"]} ({lowest_genre["average_rating"]:.2f})
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

fig_genre_satisfaction = go.Figure()

fig_genre_satisfaction.add_trace(
    go.Bar(
        x=genre_satisfaction["average_rating"],
        y=genre_satisfaction["genre"],
        orientation="h",
        marker_color=COLORS["secondary"],
        customdata=genre_satisfaction["rating_count"],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Average rating: %{x:.2f}<br>"
            "Number of ratings: %{customdata:,}"
            "<extra></extra>"
        ),
    )
)

fig_genre_satisfaction.add_vline(
    x=overall_mean,
    line_width=2,
    line_dash="dash",
    line_color=COLORS["reference"],
    annotation_text=f"Overall mean: {overall_mean:.2f}",
    annotation_position="top",
)

# Put rating counts immediately after each bar.
for _, row in genre_satisfaction.iterrows():
    fig_genre_satisfaction.add_annotation(
        x=row["average_rating"] + 0.015,
        y=row["genre"],
        text=f"n={row['rating_count']:,}",
        showarrow=False,
        xanchor="left",
        font=dict(size=11, color="#555"),
    )

fig_genre_satisfaction.update_layout(
    height=max(450, len(genre_satisfaction) * 28),
    xaxis_title="Average rating",
    yaxis_title="Genre",
    margin=dict(l=20, r=100, t=40, b=20),
)

st.plotly_chart(fig_genre_satisfaction, use_container_width=True)


# ============================================================
# SECTION 3 — Ratings Over Time
# ============================================================
st.header("3. Ratings Over Time")

st.markdown(
    """
    <div class="explanation">
        <p>
        The line shows the mean rating for movies by their release year.
        The supporting bars show how many ratings contribute to each year,
        making it easier to identify years where the mean is based on
        relatively little data.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

yearly_ratings = (
    df.groupby("year")
    .agg(
        mean_rating=("rating", "mean"),
        rating_count=("rating", "size"),
    )
    .reset_index()
    .sort_values("year")
)

fig_yearly = go.Figure()

# Faint supporting bars.
fig_yearly.add_trace(
    go.Bar(
        x=yearly_ratings["year"],
        y=yearly_ratings["rating_count"],
        name="Number of ratings",
        marker_color=COLORS["muted"],
        opacity=0.35,
        yaxis="y2",
        hovertemplate=(
            "Year: %{x}<br>"
            "Ratings: %{y:,}"
            "<extra></extra>"
        ),
    )
)

# Mean-rating line.
fig_yearly.add_trace(
    go.Scatter(
        x=yearly_ratings["year"],
        y=yearly_ratings["mean_rating"],
        mode="lines+markers",
        name="Mean rating",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=6),
        hovertemplate=(
            "Year: %{x}<br>"
            "Mean rating: %{y:.2f}"
            "<extra></extra>"
        ),
    )
)

fig_yearly.update_layout(
    height=600,
    xaxis=dict(
        title="Movie release year",
        rangeslider=dict(visible=True),
    ),
    yaxis=dict(
        title="Mean rating",
        side="left",
    ),
    yaxis2=dict(
        title="Number of ratings",
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    margin=dict(l=20, r=20, t=50, b=20),
)

st.plotly_chart(fig_yearly, use_container_width=True)


# ============================================================
# SECTION 4 — Best Movies, With a Floor
# ============================================================
st.header("4. Best Movies, With a Floor")

st.markdown(
    """
    <div class="explanation">
        <p>
        These charts show the five movies with the highest mean rating after
        applying a minimum-rating floor. Increasing the floor from 50 to 150
        ratings reduces the influence of movies with relatively small numbers
        of ratings.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def get_top_movies(min_ratings, n=5):
    movie_stats = (
        df.groupby(["movie_id", "title"])
        .agg(
            mean_rating=("rating", "mean"),
            rating_count=("rating", "size"),
        )
        .reset_index()
    )

    return (
        movie_stats[movie_stats["rating_count"] >= min_ratings]
        .sort_values(
            ["mean_rating", "rating_count"],
            ascending=[False, False],
        )
        .head(n)
        .sort_values("mean_rating", ascending=True)
    )


top_50 = get_top_movies(50)
top_150 = get_top_movies(150)


def movie_dot_plot(data, floor):
    plot_data = data.copy()

    # Include the rating count directly in the y-axis label.
    plot_data["movie_label"] = (
        plot_data["title"]
        + "  (n="
        + plot_data["rating_count"].map(lambda x: f"{x:,}")
        + ")"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_data["mean_rating"],
            y=plot_data["movie_label"],
            mode="markers",
            marker=dict(
                size=13,
                color=COLORS["primary"],
                line=dict(width=1, color="white"),
            ),
            customdata=plot_data["rating_count"],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Mean rating: %{x:.2f}<br>"
                "Ratings: %{customdata:,}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=f"Minimum {floor} ratings",
        height=360,
        xaxis_title="Mean rating",
        yaxis_title="",
        margin=dict(l=20, r=20, t=55, b=20),
    )

    return fig


col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        movie_dot_plot(top_50, 50),
        use_container_width=True,
    )

with col2:
    st.plotly_chart(
        movie_dot_plot(top_150, 150),
        use_container_width=True,
    )


# Explain the actual change between the two floors.
titles_50 = set(top_50["movie_id"])
titles_150 = set(top_150["movie_id"])

dropped = top_50[~top_50["movie_id"].isin(titles_150)]
added = top_150[~top_150["movie_id"].isin(titles_50)]

dropped_names = ", ".join(dropped["title"].tolist())
added_names = ", ".join(added["title"].tolist())

if dropped_names:
    dropped_text = (
        f"When the floor increased from 50 to 150 ratings, "
        f"{dropped_names} no longer qualified for the displayed top five."
    )
else:
    dropped_text = (
        "All five movies in the 50-rating top five also qualified "
        "for the 150-rating floor."
    )

if added_names:
    added_text = f"Movies entering the displayed top five included {added_names}."
else:
    added_text = (
        "No new movie entered the displayed top five when the floor was raised."
    )

st.markdown(
    f"""
    <div class="explanation">
        <strong>What changed?</strong><br>
        {dropped_text}<br>
        {added_text}
    </div>
    """,
    unsafe_allow_html=True,
)
