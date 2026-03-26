TABLES_SQL = """
SELECT
  t.table_name
FROM information_schema.tables t
WHERE t.table_schema = $1
  AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;
"""

COLUMNS_SQL = """
SELECT
  c.table_name,
  c.column_name,
  c.data_type,
  c.is_nullable,
  c.ordinal_position
FROM information_schema.columns c
WHERE c.table_schema = $1
ORDER BY c.table_name, c.ordinal_position;
"""

PRIMARY_KEYS_SQL = """
SELECT
  tc.table_name,
  kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema = $1;
"""

FOREIGN_KEYS_SQL = """
SELECT
  tc.constraint_name,
  tc.table_name AS source_table,
  kcu.column_name AS source_column,
  ccu.table_name AS target_table,
  ccu.column_name AS target_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = $1
ORDER BY tc.table_name, tc.constraint_name;
"""

INDEXES_SQL = """
SELECT
  i.tablename AS table_name,
  i.indexname AS index_name,
  i.indexdef AS index_definition
FROM pg_indexes i
WHERE i.schemaname = $1
ORDER BY i.tablename, i.indexname;
"""
