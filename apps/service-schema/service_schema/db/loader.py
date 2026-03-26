from __future__ import annotations

from collections import defaultdict

from service_schema.db.pool import get_pool
from service_schema.db.queries import (
    COLUMNS_SQL,
    FOREIGN_KEYS_SQL,
    INDEXES_SQL,
    PRIMARY_KEYS_SQL,
    TABLES_SQL,
)
from service_schema.models.schema import (
    ColumnMetadata,
    ForeignKeyMetadata,
    IndexMetadata,
    TableMetadata,
)
from service_schema.util import extract_index_columns, infer_aliases, infer_business_tags


class SchemaLoader:
    def __init__(
        self,
        *,
        schema_name: str,
        alias_overrides: dict[str, list[str]],
        tag_overrides: dict[str, list[str]],
    ) -> None:
        self.schema_name = schema_name
        self.alias_overrides = alias_overrides
        self.tag_overrides = tag_overrides

    async def load(self, *, include_indexes: bool) -> list[TableMetadata]:
        pool = get_pool()
        # Fetch metadata in coarse batches, then normalize it into one in-memory model
        # so retrieval avoids repeated catalog queries during request handling.
        table_rows = await pool.fetch(TABLES_SQL, self.schema_name)
        column_rows = await pool.fetch(COLUMNS_SQL, self.schema_name)
        pk_rows = await pool.fetch(PRIMARY_KEYS_SQL, self.schema_name)
        fk_rows = await pool.fetch(FOREIGN_KEYS_SQL, self.schema_name)
        index_rows = await pool.fetch(INDEXES_SQL, self.schema_name) if include_indexes else []

        pk_map: dict[str, set[str]] = defaultdict(set)
        for row in pk_rows:
            pk_map[row["table_name"]].add(row["column_name"])

        tables: dict[str, TableMetadata] = {}
        for row in table_rows:
            table_name = row["table_name"]
            tables[table_name] = TableMetadata(
                name=table_name,
                schema_name=self.schema_name,
                aliases=sorted(
                    {
                        *infer_aliases(table_name),
                        *self.alias_overrides.get(table_name, []),
                    }
                ),
                business_tags=sorted(
                    {
                        *infer_business_tags(table_name),
                        *self.tag_overrides.get(table_name, []),
                    }
                ),
            )

        for row in column_rows:
            table_name = row["table_name"]
            table = tables.get(table_name)
            if table is None:
                continue
            table.columns.append(
                ColumnMetadata(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=row["is_nullable"] == "YES",
                    is_primary_key=row["column_name"] in pk_map.get(table_name, set()),
                    ordinal_position=int(row["ordinal_position"]),
                )
            )

        for row in fk_rows:
            table = tables.get(row["source_table"])
            if table is None:
                continue
            table.foreign_keys.append(
                ForeignKeyMetadata(
                    name=row["constraint_name"],
                    source_table=row["source_table"],
                    source_column=row["source_column"],
                    target_table=row["target_table"],
                    target_column=row["target_column"],
                )
            )

        for row in index_rows:
            table = tables.get(row["table_name"])
            if table is None:
                continue
            table.indexes.append(
                IndexMetadata(
                    name=row["index_name"],
                    definition=row["index_definition"],
                    columns=extract_index_columns(row["index_definition"]),
                )
            )

        return list(tables.values())
