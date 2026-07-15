-- =====================================================================
-- UK House Price Index — Analysis Queries
-- =====================================================================

-- 1. Average price by region, most recent month available
SELECT r.region_name, ph.average_price, ph.price_date
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name = 'All'
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
ORDER BY ph.average_price DESC;

-- 2. Average price by region, by year (headline category only)
SELECT r.region_name, YEAR(ph.price_date) AS yr, ROUND(AVG(ph.average_price), 0) AS avg_price
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name = 'All'
GROUP BY r.region_name, YEAR(ph.price_date)
ORDER BY r.region_name, yr;

-- 3. Month-over-month growth for a specific region (parameterize RegionName as needed)
SELECT ph.price_date, ph.average_price, ph.change_1m_pct
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE r.region_name = 'London' AND c.category_name = 'All'
ORDER BY ph.price_date;

-- 4. Top 5 fastest-growing regions over the last 12 months (by average of 12m%Change)
SELECT r.region_name, ROUND(AVG(ph.change_12m_pct), 2) AS avg_12m_growth
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name = 'All'
  AND ph.price_date >= (SELECT DATE_SUB(MAX(price_date), INTERVAL 12 MONTH) FROM price_history)
  AND r.region_tier != 'Nation'
GROUP BY r.region_name
ORDER BY avg_12m_growth DESC
LIMIT 5;

-- 5. Bottom 5 slowest-growing (or shrinking) regions, same window
SELECT r.region_name, ROUND(AVG(ph.change_12m_pct), 2) AS avg_12m_growth
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name = 'All'
  AND ph.price_date >= (SELECT DATE_SUB(MAX(price_date), INTERVAL 12 MONTH) FROM price_history)
  AND r.region_tier != 'Nation'
GROUP BY r.region_name
ORDER BY avg_12m_growth ASC
LIMIT 5;

-- 6. Property type price comparison, most recent month, by region
SELECT r.region_name, c.category_name, ph.average_price
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_group = 'PropertyType'
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
ORDER BY r.region_name, c.category_name;

-- 7. New-build premium: how much more expensive is new vs old, by region
SELECT
    r.region_name,
    MAX(CASE WHEN c.category_name = 'New' THEN ph.average_price END) AS new_price,
    MAX(CASE WHEN c.category_name = 'Old' THEN ph.average_price END) AS old_price,
    ROUND(
        (MAX(CASE WHEN c.category_name = 'New' THEN ph.average_price END)
         / MAX(CASE WHEN c.category_name = 'Old' THEN ph.average_price END) - 1) * 100
    , 2) AS new_build_premium_pct
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name IN ('New', 'Old')
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
GROUP BY r.region_name
HAVING new_price IS NOT NULL AND old_price IS NOT NULL
ORDER BY new_build_premium_pct DESC;

-- 8. Cash vs Mortgage buyers: average price and sales volume split, most recent month
SELECT
    r.region_name,
    MAX(CASE WHEN c.category_name = 'Cash' THEN ph.average_price END) AS cash_price,
    MAX(CASE WHEN c.category_name = 'Cash' THEN ph.sales_volume END) AS cash_volume,
    MAX(CASE WHEN c.category_name = 'Mortgage' THEN ph.average_price END) AS mortgage_price,
    MAX(CASE WHEN c.category_name = 'Mortgage' THEN ph.sales_volume END) AS mortgage_volume
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name IN ('Cash', 'Mortgage')
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
GROUP BY r.region_name;

-- 9. First-time buyer vs existing-owner price gap, by region, most recent month
SELECT
    r.region_name,
    MAX(CASE WHEN c.category_name = 'FTB' THEN ph.average_price END) AS ftb_price,
    MAX(CASE WHEN c.category_name = 'FOO' THEN ph.average_price END) AS foo_price,
    ROUND(
        MAX(CASE WHEN c.category_name = 'FOO' THEN ph.average_price END)
        - MAX(CASE WHEN c.category_name = 'FTB' THEN ph.average_price END)
    , 0) AS price_gap
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name IN ('FTB', 'FOO')
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
GROUP BY r.region_name
ORDER BY price_gap DESC;

-- 10. Data reliability check: how many rows per category are flagged unreliable/estimated
SELECT c.category_name, ph.is_data_reliable, COUNT(*) AS row_count
FROM price_history ph
JOIN categories c ON c.category_id = ph.category_id
GROUP BY c.category_name, ph.is_data_reliable
ORDER BY c.category_name;

-- 11. National vs regional vs local authority: average price by tier, most recent month
SELECT r.region_tier, ROUND(AVG(ph.average_price), 0) AS avg_price, COUNT(*) AS n_regions
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE c.category_name = 'All'
  AND ph.price_date = (SELECT MAX(price_date) FROM price_history)
GROUP BY r.region_tier;

-- 12. Rolling 3-month average price trend for a region (window function)
SELECT
    r.region_name,
    ph.price_date,
    ph.average_price,
    ROUND(AVG(ph.average_price) OVER (
        PARTITION BY r.region_id ORDER BY ph.price_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 0) AS rolling_3m_avg
FROM price_history ph
JOIN regions r ON r.region_id = ph.region_id
JOIN categories c ON c.category_id = ph.category_id
WHERE r.region_name = 'London' AND c.category_name = 'All'
ORDER BY ph.price_date;
