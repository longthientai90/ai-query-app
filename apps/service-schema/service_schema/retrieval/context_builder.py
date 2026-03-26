from __future__ import annotations

from service_schema.indexing.store import SchemaStore


def build_compact_context(
    *,
    store: SchemaStore,
    table_names: list[str],
    include_indexes: bool,
    include_relationships: bool,
    max_columns_per_table: int,
    max_chars: int,
) -> str:
    sections: list[str] = []
    for table_name in table_names:
        table = store.tables.get(table_name)
        if table is None:
            continue

        # Keep the prompt representation shallow and regular so downstream prompts can
        # include multiple tables without carrying raw DDL or every column.
        column_lines = []
        for column in sorted(table.columns, key=lambda item: item.ordinal_position)[:max_columns_per_table]:
            markers: list[str] = []
            if column.is_primary_key:
                markers.append("PK")
            indexed = any(column.name in index.columns for index in table.indexes)
            if indexed:
                markers.append("IDX")
            marker_text = f" [{' / '.join(markers)}]" if markers else ""
            column_lines.append(f"  - {column.name}: {column.data_type}{marker_text}")

        lines = [f"table {table.name}"]
        if table.aliases:
            lines.append(f"aliases: {', '.join(table.aliases)}")
        if table.business_tags:
            lines.append(f"tags: {', '.join(table.business_tags)}")
        lines.extend(column_lines)

        if include_relationships and table.foreign_keys:
            lines.append("relationships:")
            for foreign_key in table.foreign_keys:
                lines.append(
                    f"  - {foreign_key.source_column} -> "
                    f"{foreign_key.target_table}.{foreign_key.target_column}"
                )

        if include_indexes and table.indexes:
            lines.append("indexes:")
            for index in table.indexes[:3]:
                suffix = f" ({', '.join(index.columns)})" if index.columns else ""
                lines.append(f"  - {index.name}{suffix}")

        sections.append("\n".join(lines))
        compact = "\n\n".join(sections)
        if len(compact) >= max_chars:
            return compact[:max_chars].rstrip()

    return "\n\n".join(sections)[:max_chars].rstrip()
