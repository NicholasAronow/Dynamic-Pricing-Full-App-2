-- Performance optimization indexes for handling large datasets
-- Run this SQL to optimize queries for tens of thousands of orders

-- Index for orders table - critical for date range queries
CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders(user_id, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_date_user ON orders(order_date, user_id);

-- Index for order_items table - critical for item aggregation
CREATE INDEX IF NOT EXISTS idx_order_items_item_id ON order_items(item_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- Composite index for order_items with order join
CREATE INDEX IF NOT EXISTS idx_order_items_item_order ON order_items(item_id, order_id);

-- Index for items table - user filtering
CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);

-- Partial indexes for active items (if you have a status field)
-- CREATE INDEX IF NOT EXISTS idx_items_active_user ON items(user_id) WHERE status = 'active';

-- Consider adding these if you have timestamp columns for better performance
-- CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
-- CREATE INDEX IF NOT EXISTS idx_order_items_created_at ON order_items(created_at);

-- For PostgreSQL: Consider creating a materialized view for frequently accessed data
-- This would be especially useful if you're running the same time-based queries repeatedly
/*
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_item_performance AS
SELECT 
    i.id as item_id,
    i.user_id,
    DATE(o.order_date) as order_date,
    SUM(oi.quantity) as daily_quantity,
    SUM(oi.quantity * oi.unit_price) as daily_revenue,
    SUM(oi.quantity * COALESCE(oi.unit_cost, 0)) as daily_cost
FROM items i
LEFT JOIN order_items oi ON i.id = oi.item_id
LEFT JOIN orders o ON oi.order_id = o.id
WHERE o.order_date IS NOT NULL
GROUP BY i.id, i.user_id, DATE(o.order_date);

-- Index on the materialized view
CREATE INDEX IF NOT EXISTS idx_daily_perf_user_date ON daily_item_performance(user_id, order_date);
CREATE INDEX IF NOT EXISTS idx_daily_perf_item_date ON daily_item_performance(item_id, order_date);

-- Refresh the materialized view (you'd need to do this periodically)
-- REFRESH MATERIALIZED VIEW daily_item_performance;
*/
