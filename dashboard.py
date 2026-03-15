"""
E-Commerce Analytics Dashboard
Streamlit + Plotly | Dark theme | 4 pages: Overview, Products, Customers, Orders
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DB_URL = "postgresql://postgres:postgres123@localhost:5432/ecommerce_warehouse"
PLOTLY_TEMPLATE = "plotly_dark"
ACCENT = [
    "#7C3AED",  # purple
    "#10B981",  # emerald
    "#F59E0B",  # amber
    "#3B82F6",  # blue
    "#EF4444",  # red
    "#EC4899",  # pink
    "#14B8A6",  # teal
    "#F97316",  # orange
]

st.set_page_config(
    page_title="ShopMetrics — E-Commerce Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Base background ──────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"]              { background-color: #0F172A !important; }
[data-testid="stSidebar"]           { background-color: #1E293B !important; border-right: 1px solid #334155; }
[data-testid="stSidebarContent"]    { padding-top: 0 !important; }

/* ── Metric cards ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 18px 20px !important;
}
[data-testid="stMetricLabel"] > div  { color: #94A3B8 !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"]        { color: #F1F5F9 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"]        { font-size: 0.8rem !important; }

/* ── Typography ───────────────────────────────────────────────────────────── */
h1, h2, h3, h4 { color: #F1F5F9 !important; }
p, li          { color: #CBD5E1; }
label          { color: #94A3B8 !important; }

/* ── Sidebar nav radio ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #CBD5E1 !important;
    font-size: 0.95rem;
    padding: 6px 0;
}
[data-testid="stSidebar"] [data-testid="stRadio"] div[data-baseweb="radio"] input:checked + div {
    background: #7C3AED !important;
    border-color: #7C3AED !important;
}

/* ── Divider ──────────────────────────────────────────────────────────────── */
hr { border-color: #334155 !important; }

/* ── Scrollbar ────────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0F172A; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
</style>
""",
    unsafe_allow_html=True,
)


# ─── DB HELPERS ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def fmt_usd(v: float) -> str:
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:,.0f}"


def fmt_num(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:,.0f}"


def chart_layout(fig, *, height: int = 360, title: str = "", margin=None):
    """Apply a consistent dark, transparent layout to every figure."""
    m = margin or dict(l=10, r=15, t=45, b=10)
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, font=dict(size=14, color="#F1F5F9"), x=0.01),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=m,
        font=dict(color="#94A3B8"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=11, color="#CBD5E1"),
        ),
    )
    return fig


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding:28px 0 20px;text-align:center;border-bottom:1px solid #334155;margin-bottom:20px;">
            <div style="font-size:2rem;margin-bottom:4px;">🛒</div>
            <div style="font-size:1.25rem;font-weight:800;color:#7C3AED;letter-spacing:-0.5px;">ShopMetrics</div>
            <div style="font-size:0.72rem;color:#64748B;margin-top:2px;">E-Commerce Analytics</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "nav",
        ["📊  Overview", "📦  Products", "👥  Customers", "🧾  Orders"],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.72rem;color:#475569;text-align:center;">Data refreshes every 5 min · PostgreSQL</p>',
        unsafe_allow_html=True,
    )


def page_header(title: str, sub: str):
    st.markdown(
        f"""
        <div style="margin-bottom:6px;">
            <span style="font-size:1.65rem;font-weight:800;color:#F1F5F9;">{title}</span>
        </div>
        <div style="font-size:0.85rem;color:#64748B;margin-bottom:24px;">{sub}</div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊  Overview":
    page_header("📊 Overview", "High-level performance metrics across all channels and time periods")

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi = q("""
        SELECT
            SUM(revenue)                                                AS total_revenue,
            COUNT(DISTINCT order_id)                                    AS total_orders,
            COUNT(DISTINCT customer_key)                                AS total_customers,
            SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0)         AS aov,
            SUM(gross_profit)                                           AS total_profit,
            SUM(gross_profit) / NULLIF(SUM(revenue), 0) * 100          AS profit_margin_pct
        FROM fact_sales
        WHERE order_status != 'Cancelled'
    """).iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Revenue",   fmt_usd(kpi["total_revenue"]))
    c2.metric("Total Orders",    fmt_num(kpi["total_orders"]))
    c3.metric("Unique Customers", fmt_num(kpi["total_customers"]))
    c4.metric("Avg Order Value", fmt_usd(kpi["aov"]))
    c5.metric("Gross Profit",    fmt_usd(kpi["total_profit"]))
    c6.metric("Profit Margin",   f"{kpi['profit_margin_pct']:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Monthly trend + Channel donut ─────────────────────────────────────────
    monthly = q("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', d.full_date), 'YYYY-MM') AS month,
            SUM(f.revenue)                                        AS revenue,
            SUM(f.gross_profit)                                   AS gross_profit,
            COUNT(DISTINCT f.order_id)                            AS orders
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE f.order_status != 'Cancelled'
        GROUP BY DATE_TRUNC('month', d.full_date)
        ORDER BY 1
    """)

    channel = q("""
        SELECT channel, SUM(revenue) AS revenue
        FROM fact_sales
        WHERE order_status != 'Cancelled'
        GROUP BY channel
        ORDER BY revenue DESC
    """)

    col_trend, col_donut = st.columns([3, 2])

    with col_trend:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly["month"], y=monthly["revenue"],
            name="Revenue",
            mode="lines+markers",
            line=dict(color="#7C3AED", width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(124,58,237,0.12)",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["month"], y=monthly["gross_profit"],
            name="Gross Profit",
            mode="lines+markers",
            line=dict(color="#10B981", width=2, dash="dot"),
            marker=dict(size=5),
        ))
        chart_layout(fig, title="Monthly Revenue & Gross Profit Trend", height=360)
        fig.update_layout(
            legend=dict(orientation="h", y=1.12, x=0),
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_donut:
        fig2 = px.pie(
            channel, names="channel", values="revenue",
            color_discrete_sequence=ACCENT, hole=0.52,
        )
        chart_layout(fig2, title="Revenue by Sales Channel", height=360)
        fig2.update_traces(
            textinfo="percent+label",
            textfont_size=11,
            marker=dict(line=dict(color="#0F172A", width=2)),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Monthly orders bar + Channel grouped bar ───────────────────────────────
    col_bar, col_grp = st.columns(2)

    with col_bar:
        fig3 = px.bar(
            monthly, x="month", y="orders",
            color_discrete_sequence=["#3B82F6"],
        )
        chart_layout(fig3, title="Monthly Order Volume", height=300)
        fig3.update_layout(xaxis_title=None, yaxis_title="Orders")
        st.plotly_chart(fig3, use_container_width=True)

    with col_grp:
        ch_grp = q("""
            SELECT channel,
                   SUM(revenue)      AS revenue,
                   SUM(gross_profit) AS gross_profit
            FROM fact_sales
            WHERE order_status != 'Cancelled'
            GROUP BY channel
            ORDER BY revenue DESC
        """)
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(name="Revenue",      x=ch_grp["channel"], y=ch_grp["revenue"],      marker_color="#7C3AED"))
        fig4.add_trace(go.Bar(name="Gross Profit", x=ch_grp["channel"], y=ch_grp["gross_profit"], marker_color="#10B981"))
        chart_layout(fig4, title="Channel: Revenue vs Gross Profit", height=300)
        fig4.update_layout(
            barmode="group",
            legend=dict(orientation="h", y=1.12),
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
        )
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦  Products":
    page_header("📦 Products", "Top performers, category breakdown, and margin tier analysis")

    # ── Top 15 products horizontal bar ────────────────────────────────────────
    top_prod = q("""
        SELECT
            p.product_name,
            p.category,
            SUM(f.revenue)      AS revenue,
            SUM(f.gross_profit) AS gross_profit,
            SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100 AS margin_pct
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        WHERE f.order_status != 'Cancelled'
        GROUP BY p.product_name, p.category
        ORDER BY revenue DESC
        LIMIT 15
    """)

    fig_top = px.bar(
        top_prod,
        x="revenue", y="product_name",
        orientation="h",
        color="margin_pct",
        color_continuous_scale="Viridis",
        text=top_prod["revenue"].map(fmt_usd),
        labels={"revenue": "Revenue", "product_name": "", "margin_pct": "Margin %"},
    )
    chart_layout(fig_top, title="Top 15 Products by Revenue (colour = Margin %)", height=490)
    fig_top.update_layout(
        yaxis_autorange="reversed",
        xaxis=dict(tickprefix="$", tickformat=",.0f"),
        coloraxis_colorbar=dict(title="Margin %", ticksuffix="%", len=0.6),
    )
    fig_top.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
    st.plotly_chart(fig_top, use_container_width=True)

    # ── Category combo + Subcategory treemap ──────────────────────────────────
    col_cat, col_tree = st.columns(2)

    with col_cat:
        cat = q("""
            SELECT
                p.category,
                SUM(f.revenue)      AS revenue,
                SUM(f.gross_profit) AS gross_profit,
                SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100 AS margin_pct
            FROM fact_sales f
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE f.order_status != 'Cancelled'
            GROUP BY p.category
            ORDER BY revenue DESC
        """)
        fig_cat = go.Figure()
        fig_cat.add_trace(go.Bar(
            name="Revenue",
            x=cat["category"], y=cat["revenue"],
            marker_color="#7C3AED", yaxis="y",
        ))
        fig_cat.add_trace(go.Scatter(
            name="Margin %",
            x=cat["category"], y=cat["margin_pct"],
            mode="lines+markers",
            line=dict(color="#F59E0B", width=2),
            marker=dict(size=9, color="#F59E0B"),
            yaxis="y2",
        ))
        chart_layout(fig_cat, title="Category Revenue & Gross Margin")
        fig_cat.update_layout(
            yaxis=dict(title="Revenue", tickprefix="$", tickformat=",.0f"),
            yaxis2=dict(title="Margin %", overlaying="y", side="right", ticksuffix="%"),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_tree:
        subcat = q("""
            SELECT
                p.category,
                p.subcategory,
                SUM(f.revenue)      AS revenue,
                SUM(f.gross_profit) AS gross_profit
            FROM fact_sales f
            JOIN dim_product p ON f.product_key = p.product_key
            WHERE f.order_status != 'Cancelled'
            GROUP BY p.category, p.subcategory
        """)
        fig_tree = px.treemap(
            subcat,
            path=["category", "subcategory"],
            values="revenue",
            color="gross_profit",
            color_continuous_scale="Purples",
            labels={"gross_profit": "Gross Profit"},
        )
        chart_layout(fig_tree, title="Revenue Treemap — Category → Subcategory")
        fig_tree.update_layout(
            coloraxis_colorbar=dict(title="Gross Profit", tickprefix="$"),
        )
        fig_tree.update_traces(textfont_size=12)
        st.plotly_chart(fig_tree, use_container_width=True)

    # ── Margin tier: grouped bar + scatter ────────────────────────────────────
    margin_tier = q("""
        SELECT
            p.margin_tier,
            SUM(f.revenue)      AS revenue,
            SUM(f.gross_profit) AS gross_profit,
            AVG(f.discount_pct) * 100 AS avg_discount,
            SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100 AS realized_margin
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        WHERE f.order_status != 'Cancelled'
        GROUP BY p.margin_tier
        ORDER BY realized_margin DESC
    """)

    col_mt1, col_mt2 = st.columns(2)

    with col_mt1:
        fig_mt = go.Figure()
        fig_mt.add_trace(go.Bar(name="Revenue",      x=margin_tier["margin_tier"], y=margin_tier["revenue"],      marker_color="#7C3AED"))
        fig_mt.add_trace(go.Bar(name="Gross Profit", x=margin_tier["margin_tier"], y=margin_tier["gross_profit"], marker_color="#10B981"))
        chart_layout(fig_mt, title="Revenue & Profit by Margin Tier", height=320)
        fig_mt.update_layout(
            barmode="group",
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig_mt, use_container_width=True)

    with col_mt2:
        fig_sc = px.scatter(
            margin_tier,
            x="avg_discount", y="realized_margin",
            size="revenue", color="margin_tier",
            text="margin_tier",
            color_discrete_sequence=ACCENT,
            labels={
                "avg_discount": "Avg Discount %",
                "realized_margin": "Realized Margin %",
                "margin_tier": "Tier",
            },
        )
        chart_layout(fig_sc, title="Discount % vs Realized Margin (size = Revenue)", height=320)
        fig_sc.update_traces(textposition="top center", textfont_size=10)
        fig_sc.update_layout(showlegend=False)
        st.plotly_chart(fig_sc, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👥  Customers":
    page_header("👥 Customers", "RFM segmentation, lifetime value, and cohort behavioural analysis")

    rfm_seg = q("""
        SELECT
            segment,
            COUNT(*)            AS customers,
            AVG(rfm_score)      AS avg_rfm_score,
            AVG(recency_days)   AS avg_recency,
            AVG(frequency)      AS avg_frequency,
            AVG(monetary)       AS avg_monetary
        FROM fact_rfm
        GROUP BY segment
        ORDER BY avg_monetary DESC
    """)

    ltv = q("""
        SELECT
            r.segment,
            COUNT(DISTINCT r.customer_key)                              AS customers,
            SUM(f.revenue)                                              AS total_revenue,
            SUM(f.revenue) / NULLIF(COUNT(DISTINCT r.customer_key),0)  AS ltv,
            SUM(f.gross_profit) / NULLIF(COUNT(DISTINCT r.customer_key),0) AS avg_profit
        FROM fact_rfm r
        JOIN fact_sales f ON r.customer_key = f.customer_key
        WHERE f.order_status != 'Cancelled'
        GROUP BY r.segment
        ORDER BY ltv DESC
    """)

    # ── KPI row ───────────────────────────────────────────────────────────────
    def _seg_count(name):
        row = rfm_seg[rfm_seg["segment"] == name]
        return int(row["customers"].iloc[0]) if not row.empty else 0

    total_cust   = int(rfm_seg["customers"].sum())
    champions    = _seg_count("Champions")
    loyal        = _seg_count("Loyal")
    at_risk      = _seg_count("At Risk")
    avg_ltv_val  = ltv["ltv"].mean() if not ltv.empty else 0

    ck1, ck2, ck3, ck4, ck5 = st.columns(5)
    ck1.metric("Total Customers", fmt_num(total_cust))
    ck2.metric("Champions",       fmt_num(champions))
    ck3.metric("Loyal",           fmt_num(loyal))
    ck4.metric("At Risk",         fmt_num(at_risk))
    ck5.metric("Avg Customer LTV", fmt_usd(avg_ltv_val))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Donut + LTV bar ───────────────────────────────────────────────────────
    col_d, col_ltv = st.columns(2)

    with col_d:
        fig_d = px.pie(
            rfm_seg, names="segment", values="customers",
            color_discrete_sequence=ACCENT, hole=0.52,
        )
        chart_layout(fig_d, title="Customer Count by RFM Segment", height=380)
        fig_d.update_traces(
            textinfo="percent+label", textfont_size=11,
            marker=dict(line=dict(color="#0F172A", width=2)),
        )
        st.plotly_chart(fig_d, use_container_width=True)

    with col_ltv:
        fig_ltv = px.bar(
            ltv, x="segment", y="ltv",
            color="segment",
            color_discrete_sequence=ACCENT,
            text=ltv["ltv"].map(fmt_usd),
            labels={"segment": "Segment", "ltv": "Avg LTV (USD)"},
        )
        chart_layout(fig_ltv, title="Average Customer LTV by RFM Segment", height=380)
        fig_ltv.update_layout(showlegend=False, yaxis=dict(tickprefix="$", tickformat=",.0f"))
        fig_ltv.update_traces(textposition="outside", textfont_size=11, cliponaxis=False)
        st.plotly_chart(fig_ltv, use_container_width=True)

    # ── RFM bubble map ────────────────────────────────────────────────────────
    fig_bubble = px.scatter(
        rfm_seg,
        x="avg_recency", y="avg_frequency",
        size="avg_monetary", color="segment",
        text="segment",
        color_discrete_sequence=ACCENT,
        labels={
            "avg_recency": "Avg Recency (days since last order)",
            "avg_frequency": "Avg Purchase Frequency",
            "segment": "Segment",
        },
    )
    chart_layout(fig_bubble, title="RFM Segment Map  ·  Recency vs Frequency  (bubble = Avg Monetary)", height=400)
    fig_bubble.update_traces(textposition="top center", textfont_size=10, marker=dict(opacity=0.85))
    st.plotly_chart(fig_bubble, use_container_width=True)

    # ── Premium vs Standard + Age group ──────────────────────────────────────
    col_p, col_age = st.columns(2)

    with col_p:
        premium = q("""
            SELECT
                CASE WHEN c.is_premium THEN 'Premium' ELSE 'Standard' END AS segment,
                COUNT(DISTINCT c.customer_id)                              AS customers,
                SUM(f.revenue)                                             AS total_revenue,
                SUM(f.revenue) / NULLIF(COUNT(DISTINCT c.customer_id),0)  AS avg_revenue,
                AVG(f.discount_pct) * 100                                  AS avg_discount
            FROM dim_customer c
            JOIN fact_sales f ON c.customer_key = f.customer_key
            WHERE f.order_status != 'Cancelled'
            GROUP BY c.is_premium
            ORDER BY total_revenue DESC
        """)
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(
            name="Total Revenue",
            x=premium["segment"], y=premium["total_revenue"],
            marker_color=["#7C3AED", "#3B82F6"], yaxis="y",
        ))
        fig_p.add_trace(go.Scatter(
            name="Avg Rev / Customer",
            x=premium["segment"], y=premium["avg_revenue"],
            mode="markers",
            marker=dict(size=16, color="#F59E0B", symbol="diamond"),
            yaxis="y2",
        ))
        chart_layout(fig_p, title="Premium vs Standard Customers", height=340)
        fig_p.update_layout(
            yaxis=dict(title="Total Revenue", tickprefix="$", tickformat=",.0f"),
            yaxis2=dict(title="Avg Rev/Customer", overlaying="y", side="right", tickprefix="$", tickformat=",.0f"),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig_p, use_container_width=True)

    with col_age:
        age = q("""
            SELECT
                c.age_group,
                COUNT(DISTINCT c.customer_id)                             AS customers,
                SUM(f.revenue) / NULLIF(COUNT(DISTINCT c.customer_id),0) AS avg_revenue
            FROM dim_customer c
            JOIN fact_sales f ON c.customer_key = f.customer_key
            WHERE f.order_status != 'Cancelled'
            GROUP BY c.age_group
            ORDER BY avg_revenue DESC
        """)
        fig_age = px.bar(
            age, x="age_group", y="avg_revenue",
            color="customers",
            color_continuous_scale="Purples",
            text=age["avg_revenue"].map(fmt_usd),
            labels={"age_group": "Age Group", "avg_revenue": "Avg Revenue / Customer", "customers": "# Customers"},
        )
        chart_layout(fig_age, title="Avg Revenue per Customer by Age Group", height=340)
        fig_age.update_layout(yaxis=dict(tickprefix="$", tickformat=",.0f"))
        fig_age.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
        st.plotly_chart(fig_age, use_container_width=True)

    # ── State revenue map (horizontal bar top 15 states) ─────────────────────
    state_df = q("""
        SELECT
            c.state,
            SUM(f.revenue)                                            AS revenue,
            COUNT(DISTINCT c.customer_id)                             AS customers,
            SUM(f.revenue) / NULLIF(COUNT(DISTINCT c.customer_id),0) AS ltv
        FROM dim_customer c
        JOIN fact_sales f ON c.customer_key = f.customer_key
        WHERE f.order_status != 'Cancelled'
        GROUP BY c.state
        ORDER BY revenue DESC
        LIMIT 15
    """)
    fig_state = px.bar(
        state_df, x="revenue", y="state", orientation="h",
        color="ltv", color_continuous_scale="Purples",
        text=state_df["revenue"].map(fmt_usd),
        labels={"revenue": "Revenue", "state": "", "ltv": "Avg LTV"},
    )
    chart_layout(fig_state, title="Top 15 States by Revenue  (colour = Avg Customer LTV)", height=420)
    fig_state.update_layout(
        yaxis_autorange="reversed",
        xaxis=dict(tickprefix="$", tickformat=",.0f"),
        coloraxis_colorbar=dict(title="Avg LTV", tickprefix="$", len=0.6),
    )
    fig_state.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
    st.plotly_chart(fig_state, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ORDERS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧾  Orders":
    page_header("🧾 Orders", "Fulfilment rates, discount mechanics, and payment method breakdown")

    # ── KPI row ───────────────────────────────────────────────────────────────
    ok = q("""
        SELECT
            COUNT(DISTINCT order_id)                                                        AS total_orders,
            COUNT(DISTINCT CASE WHEN order_status = 'Completed' THEN order_id END)         AS completed,
            COUNT(DISTINCT CASE WHEN order_status = 'Cancelled' THEN order_id END)         AS cancelled,
            COUNT(DISTINCT CASE WHEN order_status = 'Returned'  THEN order_id END)         AS returned,
            COUNT(DISTINCT CASE WHEN order_status = 'Pending'   THEN order_id END)         AS pending,
            AVG(discount_pct) * 100                                                        AS avg_discount_pct
        FROM fact_sales
    """).iloc[0]

    oc1, oc2, oc3, oc4, oc5, oc6 = st.columns(6)
    oc1.metric("Total Orders",  fmt_num(ok["total_orders"]))
    oc2.metric("Completed",     fmt_num(ok["completed"]))
    oc3.metric("Cancelled",     fmt_num(ok["cancelled"]))
    oc4.metric("Returned",      fmt_num(ok["returned"]))
    oc5.metric("Pending",       fmt_num(ok["pending"]))
    oc6.metric("Avg Discount",  f"{ok['avg_discount_pct']:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Status donut + Payment bar ────────────────────────────────────────────
    col_s, col_pay = st.columns(2)

    with col_s:
        status_df = q("""
            SELECT order_status, COUNT(DISTINCT order_id) AS orders, SUM(revenue) AS revenue
            FROM fact_sales
            GROUP BY order_status
            ORDER BY orders DESC
        """)
        fig_s = px.pie(
            status_df, names="order_status", values="orders",
            color_discrete_sequence=["#10B981", "#EF4444", "#F59E0B", "#3B82F6", "#EC4899"],
            hole=0.48,
        )
        chart_layout(fig_s, title="Order Volume by Status", height=360)
        fig_s.update_traces(
            textinfo="percent+label", textfont_size=11,
            marker=dict(line=dict(color="#0F172A", width=2)),
        )
        st.plotly_chart(fig_s, use_container_width=True)

    with col_pay:
        pay_df = q("""
            SELECT
                payment_method,
                COUNT(DISTINCT order_id) AS orders,
                SUM(revenue)             AS revenue,
                AVG(discount_pct) * 100  AS avg_discount
            FROM fact_sales
            WHERE order_status != 'Cancelled'
            GROUP BY payment_method
            ORDER BY revenue DESC
        """)
        fig_pay = px.bar(
            pay_df, x="payment_method", y="revenue",
            color="avg_discount",
            color_continuous_scale="RdYlGn_r",
            text=pay_df["revenue"].map(fmt_usd),
            labels={"payment_method": "Payment Method", "revenue": "Revenue", "avg_discount": "Avg Discount %"},
        )
        chart_layout(fig_pay, title="Revenue by Payment Method  (colour = Avg Discount %)", height=360)
        fig_pay.update_layout(
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            coloraxis_colorbar=dict(title="Avg Disc %", ticksuffix="%", len=0.7),
        )
        fig_pay.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
        st.plotly_chart(fig_pay, use_container_width=True)

    # ── Discount band analysis ────────────────────────────────────────────────
    disc = q("""
        SELECT
            CASE
                WHEN discount_pct = 0      THEN '0  No Discount'
                WHEN discount_pct <= 0.10  THEN '1  1–10%'
                WHEN discount_pct <= 0.20  THEN '2  11–20%'
                WHEN discount_pct <= 0.30  THEN '3  21–30%'
                ELSE                            '4  30%+'
            END AS discount_band,
            COUNT(DISTINCT order_id)  AS orders,
            SUM(revenue)              AS revenue,
            SUM(gross_profit)         AS gross_profit,
            SUM(gross_profit) / NULLIF(SUM(revenue), 0) * 100 AS margin_pct
        FROM fact_sales
        WHERE order_status != 'Cancelled'
        GROUP BY discount_band
        ORDER BY discount_band
    """)
    # strip sort prefix for display
    disc["band"] = disc["discount_band"].str[3:]

    col_db, col_heat = st.columns(2)

    with col_db:
        fig_db = go.Figure()
        fig_db.add_trace(go.Bar(
            name="Orders",
            x=disc["band"], y=disc["orders"],
            marker_color="#3B82F6", yaxis="y",
        ))
        fig_db.add_trace(go.Scatter(
            name="Margin %",
            x=disc["band"], y=disc["margin_pct"],
            mode="lines+markers",
            line=dict(color="#EF4444", width=2),
            marker=dict(size=9, color="#EF4444"),
            yaxis="y2",
        ))
        chart_layout(fig_db, title="Discount Band — Order Volume & Margin Impact", height=340)
        fig_db.update_layout(
            yaxis=dict(title="Orders"),
            yaxis2=dict(title="Margin %", overlaying="y", side="right", ticksuffix="%"),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig_db, use_container_width=True)

    with col_heat:
        cs = q("""
            SELECT channel, order_status, COUNT(DISTINCT order_id) AS orders
            FROM fact_sales
            GROUP BY channel, order_status
        """)
        pivot = cs.pivot(index="channel", columns="order_status", values="orders").fillna(0).astype(int)
        fig_h = px.imshow(
            pivot,
            text_auto=True,
            color_continuous_scale="Purples",
            labels=dict(x="Order Status", y="Channel", color="Orders"),
        )
        chart_layout(fig_h, title="Orders Heatmap — Channel × Order Status", height=340)
        fig_h.update_layout(
            xaxis=dict(side="bottom"),
            coloraxis_colorbar=dict(title="Orders", len=0.7),
        )
        st.plotly_chart(fig_h, use_container_width=True)

    # ── Monthly revenue by status stacked area ────────────────────────────────
    st_trend = q("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', d.full_date), 'YYYY-MM') AS month,
            f.order_status,
            SUM(f.revenue) AS revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY DATE_TRUNC('month', d.full_date), f.order_status
        ORDER BY 1, 2
    """)
    fig_at = px.area(
        st_trend, x="month", y="revenue", color="order_status",
        color_discrete_sequence=["#10B981", "#3B82F6", "#EF4444", "#F59E0B", "#EC4899"],
        labels={"month": "Month", "revenue": "Revenue", "order_status": "Status"},
    )
    chart_layout(fig_at, title="Monthly Revenue Breakdown by Order Status", height=310)
    fig_at.update_layout(
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", y=1.12),
        xaxis_title=None,
    )
    st.plotly_chart(fig_at, use_container_width=True)
