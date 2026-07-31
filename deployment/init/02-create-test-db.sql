-- Creates a second, isolated database for the pytest suite so integration
-- tests never share data with the development database. Runs only on first
-- container init (docker-entrypoint-initdb.d), alongside enable-pgvector.sql.

SELECT 'CREATE DATABASE lenny_growth_assistant_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lenny_growth_assistant_test')\gexec

\c lenny_growth_assistant_test
CREATE EXTENSION IF NOT EXISTS vector;
