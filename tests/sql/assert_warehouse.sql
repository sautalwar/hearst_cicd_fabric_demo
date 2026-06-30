-- UAT Assertion SQL: Warehouse Schema & Tables
-- Queries that FAIL (RAISERROR or return mismatches) if sales schema/tables are missing or empty.
-- Run via scripts/run_uat_tests.py or manually via sqlcmd / Azure Data Studio.
-- Expected outcome: zero rows returned = success; any row = failure.

SET NOCOUNT ON;

-- 1. Assert sales schema exists
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'sales')
BEGIN
    RAISERROR('ASSERTION FAILED: sales schema does not exist in wh_hearst', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ sales schema exists';
END

-- 2. Assert sales.customer table exists
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE schema_id = SCHEMA_ID('sales') AND name = 'customer')
BEGIN
    RAISERROR('ASSERTION FAILED: sales.customer table does not exist', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ sales.customer table exists';
END

-- 3. Assert sales.order table exists
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE schema_id = SCHEMA_ID('sales') AND name = 'order')
BEGIN
    RAISERROR('ASSERTION FAILED: sales.order table does not exist', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ sales.order table exists';
END

-- 4. Assert sales.customer is not empty
DECLARE @customer_count INT;
SELECT @customer_count = COUNT(*) FROM sales.customer;
IF @customer_count = 0
BEGIN
    RAISERROR('ASSERTION FAILED: sales.customer table is empty', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ sales.customer has rows';
END

-- 5. Assert sales.order is not empty
DECLARE @order_count INT;
SELECT @order_count = COUNT(*) FROM sales.[order];
IF @order_count = 0
BEGIN
    RAISERROR('ASSERTION FAILED: sales.order table is empty', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ sales.order has rows';
END

-- 6. Optional: verify referential integrity (sample)
-- Example: assert all order.customer_id values exist in customer.customer_id
-- Uncomment if your schema includes FK constraints or if this check is critical.
-- IF EXISTS (
--     SELECT 1 FROM sales.[order] o
--     WHERE NOT EXISTS (SELECT 1 FROM sales.customer c WHERE c.customer_id = o.customer_id)
-- )
-- BEGIN
--     RAISERROR('ASSERTION FAILED: Orphan rows in sales.order (customer_id not in customer)', 16, 1);
-- END

PRINT '✓ All warehouse assertions passed';
