-- =============================================================================
-- PostgreSQL 16 Setup Script: Dedicated Least-Privilege Application User
-- =============================================================================

-- 1. Create dedicated user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'interview_app_user') THEN
      CREATE ROLE interview_app_user WITH LOGIN CREATEDB PASSWORD 'SecureAppUserPassword123!';
   ELSE
      ALTER ROLE interview_app_user CREATEDB;
   END IF;
END
$do$;

-- 2. Create database if not exists
SELECT 'CREATE DATABASE mock_interview_db OWNER interview_app_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mock_interview_db')\gexec

-- 3. Grant privileges to interview_app_user
GRANT CONNECT ON DATABASE mock_interview_db TO interview_app_user;
\c mock_interview_db

GRANT ALL ON SCHEMA public TO interview_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO interview_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO interview_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO interview_app_user;
