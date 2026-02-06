-- Create the additional databases required by YuantusPLM when running against a
-- single Postgres instance.
--
-- NOTE: `POSTGRES_DB` creates the main database (yuantus). Identity lives in a
-- separate DB (yuantus_identity) by default.

SELECT 'CREATE DATABASE yuantus_identity'
WHERE NOT EXISTS (
  SELECT 1 FROM pg_database WHERE datname = 'yuantus_identity'
)\gexec

