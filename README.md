# E-Commerce Sales ETL Pipeline

A production-style ETL pipeline that generates realistic e-commerce data, transforms it into a star schema, and loads it into a PostgreSQL data warehouse.

---

## Architecture

```
Mock Data Generator (Faker)
    │
    ├── customers (2,000 records)
    ├── products  (500 records)
    └── orders    (20,000 orders → ~45,000 line items)
         │
         ▼
    [ TRANSFORM ]
         ├── dim_date     — Full date dimension (2022–2026)
         ├── dim_customer — Customer profiles + demographics
         ├── dim_product  — Product catalog + margin tiers
         └── fact_sales   — Order line items with revenue metrics
         │
         ▼
    [ LOAD ] → PostgreSQL warehouse (star schema)
```

---

## Star Schema

### dim_date
Full date dimension with year, quarter, month, week, day, and calendar flags (is_weekend, is_month_end, is_quarter_end).

### dim_customer
| Column | Description |
|--------|-------------|
| customer_key | Surrogate PK |
| customer_id | Source system ID |
| first_name, last_name, email | Identity |
| city, state, country | Location |
| age_group | 18-24, 25-34, 35-44, 45-54, 55+ |
| gender | M / F / Other |
| signup_date | When they joined |
| is_premium | Premium membership flag |

### dim_product
| Column | Description |
|--------|-------------|
| product_key | Surrogate PK |
| product_name, brand | Identity |
| category, subcategory | 2-level hierarchy |
| unit_price, unit_cost | Pricing |
| margin_pct, margin_tier | Profitability (Low/Medium/High/Premium) |
| is_active | Active listing flag |

### fact_sales
| Column | Description |
|--------|-------------|
| date_key, customer_key, product_key | Dimension FKs |
| order_id | Order grouping key |
| quantity | Units ordered |
| unit_price, discount_pct, discount_amt | Pricing detail |
| net_price, revenue, cogs, gross_profit | Revenue metrics |
| order_status | completed / returned / cancelled |
| payment_method | credit_card / paypal / debit_card / bank_transfer |
| channel | web / mobile / email / social |

---

## Setup

### 1. Create the database
```sql
CREATE DATABASE ecommerce_warehouse;
```

### 2. Set up virtual environment
```bat
cd C:\projects\ecommerce_etl
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure .env
```bat
copy .env.example .env
```

### 4. Run the pipeline
```bat
python etl.py
```

Generates ~45,000 fact rows across 20,000 orders. Runs in under 30 seconds.

---

## Analysis Queries

See `queries.sql` for 10 ready-to-run queries:

1. Monthly revenue + gross profit trend
2. Revenue by product category
3. Top 20 best-selling products
4. Sales by channel and payment method
5. Top 20 customers by lifetime value
6. Return and cancellation rates by category
7. Revenue by US state
8. Premium vs standard customer comparison
9. Discount impact analysis
10. Warehouse row counts

---

## Product Categories

| Category | Subcategories |
|----------|---------------|
| Electronics | Smartphones, Laptops, Headphones, Tablets, Smartwatches |
| Clothing | T-Shirts, Jeans, Dresses, Jackets, Shoes |
| Home & Garden | Furniture, Kitchen, Bedding, Garden Tools, Lighting |
| Books | Fiction, Non-Fiction, Textbooks, Children, Comics |
| Sports | Gym Equipment, Outdoor Gear, Sportswear, Cycling, Swimming |

---

## Skills Demonstrated

- Star schema dimensional modeling (4 tables, 3 dimensions)
- Synthetic data generation with Faker
- Multi-table joins and surrogate key management
- Revenue metric calculation (COGS, gross profit, margin %)
- Discount impact modeling
- Automated data quality checks
- Staging table pattern for bulk loads
- FK constraints and query-optimized indexes

---

## Extend with Claude Code

Open this folder in Claude Code and try:

- *"Add a customer RFM segmentation model (Recency, Frequency, Monetary)"*
- *"Add a daily sales summary mart table"*
- *"Add cohort analysis — revenue by customer signup month"*
- *"Build a Streamlit dashboard showing category performance"*
- *"Add a slowly changing dimension (SCD2) for product price changes"*
