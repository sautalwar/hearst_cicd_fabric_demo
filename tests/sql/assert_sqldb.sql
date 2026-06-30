-- UAT Assertion SQL: SQL Database Schema & Tables
-- Queries that FAIL (RAISERROR or return mismatches) if app schema / app.config are missing or empty.
-- Run via scripts/run_uat_tests.py or manually via sqlcmd.
-- Expected outcome: zero rows returned = success; any row = failure.

SET NOCOUNT ON;

-- 1. Assert app schema exists
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'app')
BEGIN
    RAISERROR('ASSERTION FAILED: app schema does not exist in sqldb_hearst', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ app schema exists';
END

-- 2. Assert app.config table exists
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE schema_id = SCHEMA_ID('app') AND name = 'config')
BEGIN
    RAISERROR('ASSERTION FAILED: app.config table does not exist', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ app.config table exists';
END

-- 3. Assert app.config is not empty
DECLARE @config_count INT;
SELECT @config_count = COUNT(*) FROM app.config;
IF @config_count = 0
BEGIN
    RAISERROR('ASSERTION FAILED: app.config table is empty', 16, 1);
END
ELSE
BEGIN
    PRINT '✓ app.config has rows';
END

-- 4. Optional: assert required config keys exist
-- Example: check for a mandatory "EnvironmentName" key
-- IF NOT EXISTS (SELECT 1 FROM app.config WHERE config_key = 'EnvironmentName')
-- BEGIN
--     RAISERROR('ASSERTION FAILED: Required config key "EnvironmentName" missing in app.config', 16, 1);
-- END

PRINT '✓ All SQL Database assertions passed';
