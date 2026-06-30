-- Fabric Warehouse: wh_hearst
-- SCAFFOLD — Real Git sync will regenerate/refine this content
-- Schema: sales
-- ⚠️ REMINDER: Deployment pipelines move schema DEFINITIONS, not data rows.
--    Each stage (DEV/UAT/PROD) must execute this DDL and seed sample data independently.

-- Create schema (idempotent; Fabric Warehouse supports CREATE SCHEMA IF NOT EXISTS in newer builds)
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'sales')
BEGIN
    EXEC('CREATE SCHEMA sales');
END
GO

-- Customer dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'customer' AND schema_id = SCHEMA_ID('sales'))
BEGIN
    CREATE TABLE sales.customer (
        customer_id INT NOT NULL,
        customer_name NVARCHAR(255) NOT NULL,
        email NVARCHAR(255),
        region NVARCHAR(50),
        created_date DATE,
        CONSTRAINT PK_customer PRIMARY KEY (customer_id)
    );
END
GO

-- Order fact table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'order' AND schema_id = SCHEMA_ID('sales'))
BEGIN
    CREATE TABLE sales.[order] (
        order_id INT NOT NULL,
        customer_id INT NOT NULL,
        order_date DATE NOT NULL,
        order_total DECIMAL(18, 2),
        order_status NVARCHAR(50),
        CONSTRAINT PK_order PRIMARY KEY (order_id),
        CONSTRAINT FK_order_customer FOREIGN KEY (customer_id) REFERENCES sales.customer(customer_id)
    );
END
GO

-- Sales summary view (always recreate or use CREATE OR ALTER in compatible Fabric builds)
IF OBJECT_ID('sales.v_sales_summary', 'V') IS NOT NULL
    DROP VIEW sales.v_sales_summary;
GO

CREATE VIEW sales.v_sales_summary AS
SELECT
    c.customer_id,
    c.customer_name,
    c.region,
    COUNT(o.order_id) AS total_orders,
    SUM(o.order_total) AS total_revenue,
    MAX(o.order_date) AS last_order_date
FROM
    sales.customer c
    LEFT JOIN sales.[order] o ON c.customer_id = o.customer_id
GROUP BY
    c.customer_id, c.customer_name, c.region;
GO

-- Seed data instructions (as comment, to be executed per-stage post-deploy)
/*
-- Sample seed (run after DDL in each environment):

INSERT INTO sales.customer (customer_id, customer_name, email, region, created_date)
VALUES
    (1, 'Acme Corp', 'contact@acme.com', 'North America', '2025-01-15'),
    (2, 'Global Media Inc', 'sales@globalmedia.com', 'Europe', '2025-03-20'),
    (3, 'TechStart LLC', 'info@techstart.com', 'Asia Pacific', '2025-05-10');

INSERT INTO sales.[order] (order_id, customer_id, order_date, order_total, order_status)
VALUES
    (101, 1, '2026-06-01', 15000.00, 'completed'),
    (102, 1, '2026-06-15', 8500.00, 'completed'),
    (103, 2, '2026-06-10', 22000.00, 'pending'),
    (104, 3, '2026-06-20', 5000.00, 'completed');
*/
