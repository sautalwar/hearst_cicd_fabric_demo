-- Fabric SQL Database: sqldb_hearst
-- SCAFFOLD — Real Git sync will regenerate/refine this content
-- Schema: app
-- ⚠️ REMINDER: Deployment pipelines move schema DEFINITIONS, not data rows.
--    Each stage (DEV/UAT/PROD) must execute this DDL and seed configuration data independently.

-- Create schema (idempotent)
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'app')
BEGIN
    EXEC('CREATE SCHEMA app');
END
GO

-- Application configuration table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'config' AND schema_id = SCHEMA_ID('app'))
BEGIN
    CREATE TABLE app.config (
        config_key NVARCHAR(100) NOT NULL,
        config_value NVARCHAR(MAX),
        description NVARCHAR(500),
        last_updated DATETIME2,
        CONSTRAINT PK_config PRIMARY KEY (config_key)
    );
END
GO

-- Seed data instructions (as comment, to be executed per-stage post-deploy)
/*
-- Sample seed (run after DDL in each environment):
-- Values should be parameterized per stage (DEV/UAT/PROD)

INSERT INTO app.config (config_key, config_value, description, last_updated)
VALUES
    ('environment', 'DEV', 'Current environment (DEV/UAT/PROD)', GETDATE()),
    ('api_endpoint', 'https://dev-api.hearst.com', 'API base URL', GETDATE()),
    ('max_retry_count', '3', 'Maximum retry attempts for failed operations', GETDATE()),
    ('log_level', 'DEBUG', 'Application logging level', GETDATE()),
    ('feature_flags', '{"new_ui": true, "beta_analytics": false}', 'JSON feature toggles', GETDATE());

-- For UAT, replace 'DEV' with 'UAT', 'dev-api' with 'uat-api', 'DEBUG' with 'INFO'
-- For PROD, replace with 'PROD', 'api.hearst.com', 'WARNING'
*/
