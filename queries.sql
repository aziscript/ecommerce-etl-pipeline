-- ============================================================
-- E-Commerce Warehouse — Analysis Queries
-- Run in DBeaver after the ETL loads
-- ============================================================


-- 1. Total revenue, orders, and gross profit by month
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.order_id)      AS total_orders,
    SUM(f.quantity)                 AS units_sold,
    ROUND(SUM(f.revenue)::numeric, 2)       AS total_revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2)  AS total_gross_profit,
    ROUND(
        SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100,
        1
    )                               AS gross_margin_pct
FROM fact_sales f
JOIN dim_date d
    ON f.date_key = d.date_key
WHERE f.order_status = 'completed'
GROUP BY
    d.year,
    d.month,
    d.month_name
ORDER BY
    d.year,
    d.month;


-- 2. Revenue by product category
SELECT
    p.category,
    COUNT(DISTINCT f.order_id)              AS orders,
    SUM(f.quantity)                         AS units_sold,
    ROUND(SUM(f.revenue)::numeric, 2)       AS total_revenue,
    ROUND(AVG(f.net_price)::numeric, 2)     AS avg_selling_price,
    ROUND(SUM(f.gross_profit)::numeric, 2)  AS gross_profit,
    ROUND(
        SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100,
        1
    )                                       AS margin_pct
FROM fact_sales f
JOIN dim_product p
    ON f.product_key = p.product_key
WHERE f.order_status = 'completed'
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 3. Top 20 best-selling products
SELECT
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,
    SUM(f.quantity)                         AS units_sold,
    ROUND(SUM(f.revenue)::numeric, 2)       AS total_revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2)  AS gross_profit,
    ROUND(AVG(f.discount_pct)::numeric, 1)  AS avg_discount_pct
FROM fact_sales f
JOIN dim_product p
    ON f.product_key = p.product_key
WHERE f.order_status = 'completed'
GROUP BY
    p.product_name,
    p.category,
    p.subcategory,
    p.brand
ORDER BY total_revenue DESC
LIMIT 20;


-- 4. Sales by channel and payment method
SELECT
    f.channel,
    f.payment_method,
    COUNT(DISTINCT f.order_id)          AS orders,
    ROUND(SUM(f.revenue)::numeric, 2)   AS total_revenue,
    ROUND(AVG(f.revenue)::numeric, 2)   AS avg_order_revenue
FROM fact_sales f
WHERE f.order_status = 'completed'
GROUP BY
    f.channel,
    f.payment_method
ORDER BY
    total_revenue DESC;


-- 5. Customer order summary — top 20 by revenue
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name  AS customer_name,
    c.state,
    c.age_group,
    c.is_premium,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    SUM(f.quantity)                     AS units_bought,
    ROUND(SUM(f.revenue)::numeric, 2)   AS lifetime_value,
    MIN(f.order_date)                   AS first_order,
    MAX(f.order_date)                   AS last_order
FROM fact_sales f
JOIN dim_customer c
    ON f.customer_key = c.customer_key
WHERE f.order_status = 'completed'
GROUP BY
    c.customer_id,
    customer_name,
    c.state,
    c.age_group,
    c.is_premium
ORDER BY lifetime_value DESC
LIMIT 20;


-- 6. Return and cancellation rates by category
SELECT
    p.category,
    COUNT(DISTINCT f.order_id)  AS total_orders,
    COUNT(DISTINCT CASE WHEN f.order_status = 'returned'   THEN f.order_id END) AS returned,
    COUNT(DISTINCT CASE WHEN f.order_status = 'cancelled'  THEN f.order_id END) AS cancelled,
    COUNT(DISTINCT CASE WHEN f.order_status = 'completed'  THEN f.order_id END) AS completed,
    ROUND(
        COUNT(DISTINCT CASE WHEN f.order_status = 'returned' THEN f.order_id END)::numeric
        / NULLIF(COUNT(DISTINCT f.order_id), 0) * 100,
        1
    )                           AS return_rate_pct
FROM fact_sales f
JOIN dim_product p
    ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY return_rate_pct DESC;


-- 7. Revenue by US state
SELECT
    c.state,
    COUNT(DISTINCT c.customer_id)       AS customers,
    COUNT(DISTINCT f.order_id)          AS orders,
    ROUND(SUM(f.revenue)::numeric, 2)   AS total_revenue,
    ROUND(AVG(f.revenue)::numeric, 2)   AS avg_order_value
FROM fact_sales f
JOIN dim_customer c
    ON f.customer_key = c.customer_key
WHERE f.order_status = 'completed'
GROUP BY c.state
ORDER BY total_revenue DESC;


-- 8. Premium vs standard customer comparison
SELECT
    c.is_premium,
    COUNT(DISTINCT c.customer_id)               AS customers,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    ROUND(AVG(order_totals.order_revenue)::numeric, 2) AS avg_order_value,
    ROUND(SUM(f.revenue)::numeric, 2)           AS total_revenue,
    ROUND(AVG(f.discount_pct)::numeric, 1)      AS avg_discount_pct
FROM fact_sales f
JOIN dim_customer c
    ON f.customer_key = c.customer_key
JOIN (
    SELECT
        order_id,
        SUM(revenue) AS order_revenue
    FROM fact_sales
    GROUP BY order_id
) order_totals
    ON f.order_id = order_totals.order_id
WHERE f.order_status = 'completed'
GROUP BY c.is_premium
ORDER BY c.is_premium DESC;


-- 9. Discount impact analysis
-- How much revenue is lost to discounts, and does discounting drive volume?
SELECT
    f.discount_pct,
    COUNT(DISTINCT f.order_id)                  AS orders,
    SUM(f.quantity)                             AS units_sold,
    ROUND(SUM(f.discount_amt)::numeric, 2)      AS total_discount_given,
    ROUND(SUM(f.revenue)::numeric, 2)           AS net_revenue,
    ROUND(SUM(f.gross_profit)::numeric, 2)      AS gross_profit,
    ROUND(
        SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) * 100,
        1
    )                                           AS margin_pct
FROM fact_sales f
WHERE f.order_status = 'completed'
GROUP BY f.discount_pct
ORDER BY f.discount_pct;


-- 10. Warehouse row counts (data quality check)
SELECT 'dim_date'     AS table_name, COUNT(*) AS rows FROM dim_date
UNION ALL
SELECT 'dim_customer',               COUNT(*)          FROM dim_customer
UNION ALL
SELECT 'dim_product',                COUNT(*)          FROM dim_product
UNION ALL
SELECT 'fact_sales',                 COUNT(*)          FROM fact_sales
UNION ALL
SELECT 'fact_rfm',                   COUNT(*)          FROM fact_rfm;


-- 11. RFM segment distribution and revenue summary
-- Shows how customers are spread across segments and their average behaviour.
SELECT
    r.segment,
    COUNT(*)                                                        AS customers,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)             AS pct_of_customers,
    ROUND(AVG(r.recency_days)::numeric, 0)                         AS avg_recency_days,
    ROUND(AVG(r.frequency)::numeric, 1)                            AS avg_orders,
    ROUND(AVG(r.monetary)::numeric, 2)                             AS avg_lifetime_value,
    ROUND(SUM(r.monetary)::numeric, 2)                             AS total_revenue,
    ROUND(SUM(r.monetary) * 100.0 / SUM(SUM(r.monetary)) OVER (), 1) AS pct_of_revenue,
    ROUND(AVG(r.rfm_score)::numeric, 1)                            AS avg_rfm_score
FROM fact_rfm r
GROUP BY r.segment
ORDER BY avg_rfm_score DESC;


-- 12. RFM segment × customer profile — Champions vs Lost deep-dive
-- Breaks down Champions and Lost customers by age group, premium status,
-- and state to identify where to focus retention or win-back campaigns.
SELECT
    r.segment,
    c.age_group,
    c.is_premium,
    c.state,
    COUNT(DISTINCT c.customer_key)              AS customers,
    ROUND(AVG(r.recency_days)::numeric, 0)      AS avg_recency_days,
    ROUND(AVG(r.frequency)::numeric, 1)         AS avg_orders,
    ROUND(AVG(r.monetary)::numeric, 2)          AS avg_spend,
    ROUND(SUM(r.monetary)::numeric, 2)          AS total_spend
FROM fact_rfm r
JOIN dim_customer c
    ON r.customer_key = c.customer_key
WHERE r.segment IN ('Champions', 'Lost')
GROUP BY
    r.segment,
    c.age_group,
    c.is_premium,
    c.state
ORDER BY
    r.segment,
    customers DESC;
