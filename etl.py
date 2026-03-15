"""
E-Commerce Sales ETL Pipeline
==============================
Extract:   Generated mock orders, customers, and products data
Transform: Clean, deduplicate, build star schema dimensions
Load:      PostgreSQL warehouse (fact_sales + dim tables)

Star Schema:
    dim_customer   — customer profile + location
    dim_product    — product catalog + category hierarchy
    dim_date       — full date dimension
    fact_sales     — order line items with revenue metrics
    fact_rfm       — customer RFM scores and segments (Champions, Loyal, At Risk, Lost)
"""

import os
import logging
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

fake = Faker("en_US")
random.seed(42)
np.random.seed(42)

# ── Config ────────────────────────────────────────────────────────────────────

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres123@localhost:5432/ecommerce_warehouse"
)

NUM_CUSTOMERS = 2_000
NUM_PRODUCTS  = 500
NUM_ORDERS    = 20_000
START_DATE    = datetime(2022, 1, 1)
END_DATE      = datetime(2026, 3, 14)

# ── Product catalog definition ────────────────────────────────────────────────

PRODUCT_CATALOG = {
    "Electronics": {
        "Smartphones":    (199.99, 999.99),
        "Laptops":        (499.99, 2499.99),
        "Headphones":     (29.99,  349.99),
        "Tablets":        (149.99, 999.99),
        "Smartwatches":   (99.99,  499.99),
    },
    "Clothing": {
        "T-Shirts":       (9.99,   49.99),
        "Jeans":          (29.99,  129.99),
        "Dresses":        (19.99,  199.99),
        "Jackets":        (49.99,  299.99),
        "Shoes":          (39.99,  249.99),
    },
    "Home & Garden": {
        "Furniture":      (99.99,  999.99),
        "Kitchen":        (14.99,  299.99),
        "Bedding":        (24.99,  199.99),
        "Garden Tools":   (9.99,   149.99),
        "Lighting":       (19.99,  249.99),
    },
    "Books": {
        "Fiction":        (7.99,   24.99),
        "Non-Fiction":    (9.99,   34.99),
        "Textbooks":      (29.99,  199.99),
        "Children":       (4.99,   19.99),
        "Comics":         (9.99,   49.99),
    },
    "Sports": {
        "Gym Equipment":  (19.99,  999.99),
        "Outdoor Gear":   (29.99,  499.99),
        "Sportswear":     (14.99,  149.99),
        "Cycling":        (49.99,  1999.99),
        "Swimming":       (9.99,   99.99),
    },
}

ORDER_STATUSES   = ["completed", "completed", "completed", "returned", "cancelled"]
PAYMENT_METHODS  = ["credit_card", "credit_card", "paypal", "debit_card", "bank_transfer"]
CHANNELS         = ["web", "web", "mobile", "email", "social"]
US_STATES        = [
    "CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI",
    "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI",
]

# ── Extract (Generate mock data) ──────────────────────────────────────────────

def generate_customers(n: int) -> pd.DataFrame:
    """Generate a realistic customer base with demographics."""
    log.info(f"Generating {n} customers")
    rows = []
    for i in range(1, n + 1):
        signup = fake.date_time_between(start_date=START_DATE, end_date=END_DATE)
        rows.append({
            "customer_id":    i,
            "first_name":     fake.first_name(),
            "last_name":      fake.last_name(),
            "email":          fake.email(),
            "city":           fake.city(),
            "state":          random.choice(US_STATES),
            "country":        "US",
            "age_group":      random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            "gender":         random.choice(["M", "F", "Other"]),
            "signup_date":    signup.date(),
            "is_premium":     random.random() < 0.15,   # 15% premium members
        })
    return pd.DataFrame(rows)


def generate_products(n: int) -> pd.DataFrame:
    """Generate a product catalog with category hierarchy and pricing."""
    log.info(f"Generating {n} products")
    rows = []
    product_id = 1
    categories = list(PRODUCT_CATALOG.keys())

    while product_id <= n:
        category = random.choice(categories)
        subcategory = random.choice(list(PRODUCT_CATALOG[category].keys()))
        price_min, price_max = PRODUCT_CATALOG[category][subcategory]
        cost_ratio = random.uniform(0.35, 0.65)
        unit_price = round(random.uniform(price_min, price_max), 2)
        unit_cost  = round(unit_price * cost_ratio, 2)

        rows.append({
            "product_id":   product_id,
            "product_name": f"{fake.word().capitalize()} {subcategory[:-1] if subcategory.endswith('s') else subcategory}",
            "category":     category,
            "subcategory":  subcategory,
            "brand":        fake.company().split()[0],
            "unit_price":   unit_price,
            "unit_cost":    unit_cost,
            "is_active":    random.random() < 0.90,
        })
        product_id += 1

    return pd.DataFrame(rows)


def generate_orders(
    n: int,
    customers: pd.DataFrame,
    products: pd.DataFrame
) -> pd.DataFrame:
    """Generate order line items linking customers and products."""
    log.info(f"Generating {n} orders")
    rows = []
    order_id = 1
    date_range = (END_DATE - START_DATE).days

    for _ in range(n):
        customer     = customers.sample(1).iloc[0]
        num_items    = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 12, 8, 5])[0]
        order_date   = START_DATE + timedelta(days=random.randint(0, date_range))
        status       = random.choice(ORDER_STATUSES)
        payment      = random.choice(PAYMENT_METHODS)
        channel      = random.choice(CHANNELS)
        discount_pct = random.choices(
            [0, 5, 10, 15, 20, 25],
            weights=[50, 15, 15, 10, 7, 3]
        )[0]

        order_products = products[products["is_active"]].sample(num_items)

        for _, product in order_products.iterrows():
            quantity    = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 6, 4])[0]
            unit_price  = product["unit_price"]
            unit_cost   = product["unit_cost"]
            discount_amt = round(unit_price * discount_pct / 100, 2)
            net_price   = round(unit_price - discount_amt, 2)
            revenue     = round(net_price * quantity, 2)
            cogs        = round(unit_cost * quantity, 2)
            gross_profit = round(revenue - cogs, 2)

            rows.append({
                "order_id":       order_id,
                "customer_id":    customer["customer_id"],
                "product_id":     product["product_id"],
                "order_date":     order_date,
                "quantity":       quantity,
                "unit_price":     unit_price,
                "discount_pct":   discount_pct,
                "discount_amt":   discount_amt,
                "net_price":      net_price,
                "revenue":        revenue,
                "cogs":           cogs,
                "gross_profit":   gross_profit,
                "order_status":   status,
                "payment_method": payment,
                "channel":        channel,
            })

        order_id += 1

    return pd.DataFrame(rows)

# ── Transform ─────────────────────────────────────────────────────────────────

def build_dim_date(start: datetime, end: datetime) -> pd.DataFrame:
    """Generate a complete date dimension table."""
    dates = pd.date_range(start=start, end=end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_key"]       = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"]           = df["full_date"].dt.year
    df["quarter"]        = df["full_date"].dt.quarter
    df["month"]          = df["full_date"].dt.month
    df["month_name"]     = df["full_date"].dt.strftime("%B")
    df["week_of_year"]   = df["full_date"].dt.isocalendar().week.astype(int)
    df["day_of_week"]    = df["full_date"].dt.dayofweek
    df["day_name"]       = df["full_date"].dt.strftime("%A")
    df["is_weekend"]     = df["day_of_week"] >= 5
    df["is_month_start"] = df["full_date"].dt.is_month_start
    df["is_month_end"]   = df["full_date"].dt.is_month_end
    df["is_quarter_end"] = df["full_date"].dt.is_quarter_end
    return df


def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    """Clean and deduplicate customer dimension."""
    df = customers.copy()

    # Normalize email to lowercase
    df["email"] = df["email"].str.lower().str.strip()

    # Drop duplicate emails (keep first occurrence)
    df = df.drop_duplicates(subset=["email"], keep="first")

    # Assign surrogate key
    df = df.reset_index(drop=True)
    df.insert(0, "customer_key", df.index + 1)

    log.info(f"dim_customer: {len(df)} rows after deduplication")
    return df


def build_dim_product(products: pd.DataFrame) -> pd.DataFrame:
    """Clean product dimension and add margin bucket."""
    df = products.copy()

    # Compute margin percentage
    df["margin_pct"] = (
        (df["unit_price"] - df["unit_cost"]) / df["unit_price"] * 100
    ).round(1)

    # Bucket margin into tiers
    df["margin_tier"] = pd.cut(
        df["margin_pct"],
        bins=[0, 30, 50, 70, 100],
        labels=["Low", "Medium", "High", "Premium"]
    ).astype(str)

    # Assign surrogate key
    df.insert(0, "product_key", df.index + 1)

    log.info(f"dim_product: {len(df)} rows")
    return df


def transform_fact(
    orders: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame
) -> pd.DataFrame:
    """
    Build fact_sales by joining orders with dimension surrogate keys.
    Adds date_key and filters out bad rows.
    """
    df = orders.copy()

    # Add date_key
    df["date_key"] = pd.to_datetime(df["order_date"]).dt.strftime("%Y%m%d").astype(int)

    # Join customer surrogate key
    customer_map = dim_customer[["customer_id", "customer_key"]]
    df = df.merge(customer_map, on="customer_id", how="left")

    # Join product surrogate key
    product_map = dim_product[["product_id", "product_key"]]
    df = df.merge(product_map, on="product_id", how="left")

    # Drop rows with missing keys (data quality)
    before = len(df)
    df = df.dropna(subset=["customer_key", "product_key"])
    dropped = before - len(df)
    if dropped:
        log.warning(f"Dropped {dropped} rows with missing dimension keys")

    # Select final columns
    fact = df[[
        "date_key", "customer_key", "product_key",
        "order_id", "order_date", "quantity",
        "unit_price", "discount_pct", "discount_amt",
        "net_price", "revenue", "cogs", "gross_profit",
        "order_status", "payment_method", "channel"
    ]].copy()

    # Cast types
    fact["customer_key"] = fact["customer_key"].astype(int)
    fact["product_key"]  = fact["product_key"].astype(int)

    log.info(f"fact_sales: {len(fact)} rows, {fact['order_id'].nunique()} orders")
    return fact

# ── RFM Segmentation ──────────────────────────────────────────────────────────

def build_rfm(fact: pd.DataFrame, snapshot_date: datetime) -> pd.DataFrame:
    """
    Compute Recency / Frequency / Monetary scores for every customer.

    Scoring (1–4 per dimension, quartile-based):
        Recency   — 4 = purchased most recently
        Frequency — 4 = most orders
        Monetary  — 4 = highest spend

    Segments:
        Champions — R≥3, F≥3, M≥3  (best customers)
        Loyal     — F≥3 and M≥3, or R≥3 and F≥2  (high-value regulars)
        At Risk   — R≤2 and F≥2  (used to buy, going quiet)
        Lost      — everyone else (very inactive or one-time low-value)
    """
    snapshot = pd.Timestamp(snapshot_date)
    completed = fact[fact["order_status"] == "completed"].copy()
    completed["order_date"] = pd.to_datetime(completed["order_date"])

    rfm = completed.groupby("customer_key").agg(
        recency_days=("order_date", lambda x: (snapshot - x.max()).days),
        frequency   =("order_id",   "nunique"),
        monetary    =("revenue",    "sum"),
    ).reset_index()
    rfm["monetary"] = rfm["monetary"].round(2)

    # Rank first so ties don't cause qcut to fail
    # Recency: ascending=False so highest recency_days (most inactive) → lowest rank → score 1
    rfm["r_score"] = pd.qcut(
        rfm["recency_days"].rank(method="first", ascending=False),
        q=4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"),
        q=4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"),
        q=4, labels=[1, 2, 3, 4]
    ).astype(int)

    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def _segment(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 3 and f >= 3 and m >= 3:
            return "Champions"
        elif (f >= 3 and m >= 3) or (r >= 3 and f >= 2):
            return "Loyal"
        elif r <= 2 and f >= 2:
            return "At Risk"
        else:
            return "Lost"

    rfm["segment"]       = rfm.apply(_segment, axis=1)
    rfm["snapshot_date"] = snapshot_date.date()

    log.info(f"fact_rfm: {len(rfm)} customers scored")
    log.info(f"Segments: {rfm['segment'].value_counts().to_dict()}")
    return rfm


# ── Load ──────────────────────────────────────────────────────────────────────

def create_schema(engine) -> None:
    """Create warehouse tables if they don't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_key        INTEGER PRIMARY KEY,
        full_date       DATE NOT NULL,
        year            SMALLINT,
        quarter         SMALLINT,
        month           SMALLINT,
        month_name      VARCHAR(10),
        week_of_year    SMALLINT,
        day_of_week     SMALLINT,
        day_name        VARCHAR(10),
        is_weekend      BOOLEAN,
        is_month_start  BOOLEAN,
        is_month_end    BOOLEAN,
        is_quarter_end  BOOLEAN
    );

    CREATE TABLE IF NOT EXISTS dim_customer (
        customer_key    SERIAL PRIMARY KEY,
        customer_id     INTEGER UNIQUE NOT NULL,
        first_name      VARCHAR(50),
        last_name       VARCHAR(50),
        email           VARCHAR(100),
        city            VARCHAR(80),
        state           VARCHAR(5),
        country         VARCHAR(50),
        age_group       VARCHAR(10),
        gender          VARCHAR(10),
        signup_date     DATE,
        is_premium      BOOLEAN
    );

    CREATE TABLE IF NOT EXISTS dim_product (
        product_key     SERIAL PRIMARY KEY,
        product_id      INTEGER UNIQUE NOT NULL,
        product_name    VARCHAR(150),
        category        VARCHAR(50),
        subcategory     VARCHAR(50),
        brand           VARCHAR(80),
        unit_price      NUMERIC(10,2),
        unit_cost       NUMERIC(10,2),
        margin_pct      NUMERIC(6,1),
        margin_tier     VARCHAR(10),
        is_active       BOOLEAN
    );

    CREATE TABLE IF NOT EXISTS fact_sales (
        sale_id         BIGSERIAL PRIMARY KEY,
        date_key        INTEGER     REFERENCES dim_date(date_key),
        customer_key    INTEGER     REFERENCES dim_customer(customer_key),
        product_key     INTEGER     REFERENCES dim_product(product_key),
        order_id        INTEGER,
        order_date      DATE,
        quantity        SMALLINT,
        unit_price      NUMERIC(10,2),
        discount_pct    NUMERIC(5,2),
        discount_amt    NUMERIC(10,2),
        net_price       NUMERIC(10,2),
        revenue         NUMERIC(12,2),
        cogs            NUMERIC(12,2),
        gross_profit    NUMERIC(12,2),
        order_status    VARCHAR(20),
        payment_method  VARCHAR(20),
        channel         VARCHAR(20)
    );

    CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key     ON fact_sales(date_key);
    CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_key ON fact_sales(customer_key);
    CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key  ON fact_sales(product_key);
    CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id     ON fact_sales(order_id);
    CREATE INDEX IF NOT EXISTS idx_fact_sales_channel      ON fact_sales(channel);
    CREATE INDEX IF NOT EXISTS idx_fact_sales_status       ON fact_sales(order_status);

    CREATE TABLE IF NOT EXISTS fact_rfm (
        rfm_id          BIGSERIAL PRIMARY KEY,
        customer_key    INTEGER UNIQUE REFERENCES dim_customer(customer_key),
        snapshot_date   DATE NOT NULL,
        recency_days    INTEGER,
        frequency       INTEGER,
        monetary        NUMERIC(12,2),
        r_score         SMALLINT,
        f_score         SMALLINT,
        m_score         SMALLINT,
        rfm_score       SMALLINT,
        segment         VARCHAR(20)
    );

    CREATE INDEX IF NOT EXISTS idx_fact_rfm_segment      ON fact_rfm(segment);
    CREATE INDEX IF NOT EXISTS idx_fact_rfm_customer_key ON fact_rfm(customer_key);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    log.info("Schema created / verified")


def load_dim_date(engine, df: pd.DataFrame) -> None:
    log.info(f"Loading dim_date: {len(df)} rows")
    df = df.copy()
    df["full_date"] = pd.to_datetime(df["full_date"]).dt.date
    df.to_sql("dim_date_staging", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO dim_date (
                date_key, full_date, year, quarter, month, month_name,
                week_of_year, day_of_week, day_name, is_weekend,
                is_month_start, is_month_end, is_quarter_end
            )
            SELECT
                date_key, full_date::date, year, quarter, month, month_name,
                week_of_year, day_of_week, day_name, is_weekend,
                is_month_start, is_month_end, is_quarter_end
            FROM dim_date_staging
            ON CONFLICT (date_key) DO NOTHING
        """))
        conn.execute(text("DROP TABLE IF EXISTS dim_date_staging"))


def load_dim_customer(engine, df: pd.DataFrame) -> None:
    log.info(f"Loading dim_customer: {len(df)} rows")
    cols = [
        "customer_key", "customer_id", "first_name", "last_name", "email",
        "city", "state", "country", "age_group", "gender", "signup_date", "is_premium"
    ]
    df[cols].to_sql("dim_customer_staging", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO dim_customer (
                customer_key, customer_id, first_name, last_name, email,
                city, state, country, age_group, gender, signup_date, is_premium
            )
            SELECT
                customer_key, customer_id, first_name, last_name, email,
                city, state, country, age_group, gender, signup_date, is_premium
            FROM dim_customer_staging
            ON CONFLICT (customer_id) DO UPDATE SET
                first_name   = EXCLUDED.first_name,
                last_name    = EXCLUDED.last_name,
                email        = EXCLUDED.email,
                city         = EXCLUDED.city,
                state        = EXCLUDED.state,
                is_premium   = EXCLUDED.is_premium
        """))
        conn.execute(text("DROP TABLE IF EXISTS dim_customer_staging"))


def load_dim_product(engine, df: pd.DataFrame) -> None:
    log.info(f"Loading dim_product: {len(df)} rows")
    cols = [
        "product_key", "product_id", "product_name", "category", "subcategory",
        "brand", "unit_price", "unit_cost", "margin_pct", "margin_tier", "is_active"
    ]
    df[cols].to_sql("dim_product_staging", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO dim_product (
                product_key, product_id, product_name, category, subcategory,
                brand, unit_price, unit_cost, margin_pct, margin_tier, is_active
            )
            SELECT
                product_key, product_id, product_name, category, subcategory,
                brand, unit_price, unit_cost, margin_pct, margin_tier, is_active
            FROM dim_product_staging
            ON CONFLICT (product_id) DO UPDATE SET
                unit_price  = EXCLUDED.unit_price,
                unit_cost   = EXCLUDED.unit_cost,
                margin_pct  = EXCLUDED.margin_pct,
                margin_tier = EXCLUDED.margin_tier,
                is_active   = EXCLUDED.is_active
        """))
        conn.execute(text("DROP TABLE IF EXISTS dim_product_staging"))


def load_fact_sales(engine, df: pd.DataFrame) -> None:
    log.info(f"Loading fact_sales: {len(df)} rows")
    # Use staging table + insert for performance
    df.to_sql("fact_sales_staging", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO fact_sales (
                date_key, customer_key, product_key,
                order_id, order_date, quantity,
                unit_price, discount_pct, discount_amt,
                net_price, revenue, cogs, gross_profit,
                order_status, payment_method, channel
            )
            SELECT
                date_key, customer_key, product_key,
                order_id, order_date, quantity,
                unit_price, discount_pct, discount_amt,
                net_price, revenue, cogs, gross_profit,
                order_status, payment_method, channel
            FROM fact_sales_staging
        """))
        conn.execute(text("DROP TABLE IF EXISTS fact_sales_staging"))
    log.info("fact_sales loaded")

def load_fact_rfm(engine, df: pd.DataFrame) -> None:
    log.info(f"Loading fact_rfm: {len(df)} rows")
    cols = [
        "customer_key", "snapshot_date", "recency_days", "frequency",
        "monetary", "r_score", "f_score", "m_score", "rfm_score", "segment",
    ]
    df[cols].to_sql("fact_rfm_staging", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO fact_rfm (
                customer_key, snapshot_date, recency_days, frequency,
                monetary, r_score, f_score, m_score, rfm_score, segment
            )
            SELECT
                customer_key, snapshot_date, recency_days, frequency,
                monetary, r_score, f_score, m_score, rfm_score, segment
            FROM fact_rfm_staging
            ON CONFLICT (customer_key) DO UPDATE SET
                snapshot_date = EXCLUDED.snapshot_date,
                recency_days  = EXCLUDED.recency_days,
                frequency     = EXCLUDED.frequency,
                monetary      = EXCLUDED.monetary,
                r_score       = EXCLUDED.r_score,
                f_score       = EXCLUDED.f_score,
                m_score       = EXCLUDED.m_score,
                rfm_score     = EXCLUDED.rfm_score,
                segment       = EXCLUDED.segment
        """))
        conn.execute(text("DROP TABLE IF EXISTS fact_rfm_staging"))
    log.info("fact_rfm loaded")


# ── Quality checks ────────────────────────────────────────────────────────────

def run_quality_checks(fact: pd.DataFrame) -> None:
    """Run data quality checks on the fact table before loading."""
    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)

    # Check 1: Negative revenue
    neg = fact[fact["revenue"] < 0]
    if len(neg):
        print(f"[WARN] {len(neg)} rows with negative revenue")
    else:
        print("[OK] No negative revenue rows")

    # Check 2: Quantity = 0
    zero_qty = fact[fact["quantity"] == 0]
    if len(zero_qty):
        print(f"[WARN] {len(zero_qty)} rows with zero quantity")
    else:
        print("[OK] No zero-quantity rows")

    # Check 3: Missing dimension keys
    missing_keys = fact[fact["customer_key"].isna() | fact["product_key"].isna()]
    if len(missing_keys):
        print(f"[WARN] {len(missing_keys)} rows with missing dimension keys")
    else:
        print("[OK] All dimension keys present")

    # Check 4: Revenue vs quantity * net_price mismatch
    fact["_expected_revenue"] = (fact["quantity"] * fact["net_price"]).round(2)
    mismatches = fact[fact["revenue"] != fact["_expected_revenue"]]
    if len(mismatches):
        print(f"[WARN] {len(mismatches)} rows where revenue != quantity * net_price")
    else:
        print("[OK] Revenue calculations consistent")

    # Summary stats
    print(f"\nSummary:")
    print(f"  Total rows:     {len(fact):,}")
    print(f"  Total orders:   {fact['order_id'].nunique():,}")
    print(f"  Total revenue:  ${fact['revenue'].sum():,.2f}")
    print(f"  Avg order value:${fact.groupby('order_id')['revenue'].sum().mean():,.2f}")
    print(f"  Date range:     {fact['order_date'].min()} → {fact['order_date'].max()}")
    print("=" * 60 + "\n")

# ── Orchestrate ───────────────────────────────────────────────────────────────

def run():
    log.info("=== E-Commerce Sales ETL Pipeline starting ===")
    engine = create_engine(DB_URL)

    # 1. Schema
    create_schema(engine)

    # 2. Extract (generate mock data)
    customers = generate_customers(NUM_CUSTOMERS)
    products  = generate_products(NUM_PRODUCTS)
    orders    = generate_orders(NUM_ORDERS, customers, products)

    # 3. Build dimensions
    dim_date     = build_dim_date(START_DATE, END_DATE)
    dim_customer = build_dim_customer(customers)
    dim_product  = build_dim_product(products)

    # 4. Build fact table
    fact = transform_fact(orders, dim_customer, dim_product)

    # 5. Build RFM scores
    rfm = build_rfm(fact, END_DATE)

    # 6. Quality checks
    run_quality_checks(fact)

    # 7. Load
    load_dim_date(engine, dim_date)
    load_dim_customer(engine, dim_customer)
    load_dim_product(engine, dim_product)
    load_fact_sales(engine, fact)
    load_fact_rfm(engine, rfm)

    log.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run()
