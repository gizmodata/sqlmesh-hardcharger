"""SQLMesh's DuckDB semantics over the native Hardcharger Warp SQL ADBC driver."""

from __future__ import annotations

import typing as t

from sqlglot import exp
from sqlmesh.core.engine_adapter.duckdb import DuckDBEngineAdapter
from sqlmesh.core.engine_adapter.shared import SourceQuery

if t.TYPE_CHECKING:
    from sqlmesh.core._typing import TableName
    from sqlmesh.core.engine_adapter._typing import DF


class HardchargerEngineAdapter(DuckDBEngineAdapter):
    """Remote DuckDB 2.0, with Arrow ingestion and session-scoped transactions.

    Reuse upstream catalog discovery, DuckLake partitioning and cascade handling.
    Only transport-dependent operations are specialized here.
    """

    SUPPORTS_TRANSACTIONS = True

    def _execute(self, sql: str, track_rows_processed: bool = False, **kwargs: t.Any) -> None:
        # The driver executes DDL/DML immediately, without fetching a result first.
        self.cursor.execute(sql, **kwargs)

    def _drop_catalog(self, catalog_name: exp.Identifier) -> None:
        # DETACH executes on the server. Never unlink a similarly named client file.
        self.execute(exp.Detach(this=catalog_name, exists=True))

    def table_exists(self, table_name: TableName) -> bool:
        # A failed DESCRIBE aborts a Warp SQL transaction. Existence probes are
        # expected to return False inside plan/migration transactions, so query
        # metadata without issuing a statement against a potentially absent table.
        table = exp.to_table(table_name, dialect=self.dialect)
        catalog = table.catalog or self.get_current_catalog()
        current_schema = self.fetchone("SELECT current_schema()") if not table.db else None
        schema = table.db or (current_schema[0] if current_schema else "main")
        query = exp.select("1").from_("system.information_schema.tables")
        for column, value in (
            ("table_catalog", catalog),
            ("table_schema", schema),
            ("table_name", table.name),
        ):
            query = query.where(
                exp.func("LOWER", exp.column(column)).eq(
                    exp.func("LOWER", exp.Literal.string(value))
                )
            )
        return self.fetchone(query.limit(1)) is not None

    def columns(
        self, table_name: TableName, include_pseudo_columns: bool = False
    ) -> t.Dict[str, exp.DataType]:
        # SQLMesh also probes columns before a physical model table is created.
        # Metadata lookup keeps that normal path from aborting its transaction.
        table = exp.to_table(table_name, dialect=self.dialect)
        current_schema = self.fetchone("SELECT current_schema()") if not table.db else None
        query = exp.select("column_name", "data_type").from_("system.information_schema.columns")
        for column, value in (
            ("table_catalog", table.catalog or self.get_current_catalog()),
            ("table_schema", table.db or (current_schema[0] if current_schema else "main")),
            ("table_name", table.name),
        ):
            query = query.where(
                exp.func("LOWER", exp.column(column)).eq(
                    exp.func("LOWER", exp.Literal.string(value))
                )
            )
        return {
            name: exp.DataType.build(data_type, dialect=self.dialect)
            for name, data_type in self.fetchall(query.order_by("ordinal_position"))
        }

    def _ensure_schema_exists(self, table_name: TableName) -> None:
        table = exp.to_table(table_name, dialect=self.dialect)
        if table.db:
            # Keep quoted identifiers intact (including dots embedded in names).
            schema = exp.Table(this=table.args["db"].copy())
            if table.catalog:
                schema.set("db", table.args["catalog"].copy())
            self.create_schema(schema, ignore_if_exists=True)

    def create_table(
        self,
        table_name: TableName,
        target_columns_to_types: t.Dict[str, exp.DataType],
        primary_key: t.Optional[t.Tuple[str, ...]] = None,
        exists: bool = True,
        table_description: t.Optional[str] = None,
        column_descriptions: t.Optional[t.Dict[str, str]] = None,
        **kwargs: t.Any,
    ) -> None:
        self._ensure_schema_exists(table_name)
        super().create_table(
            table_name,
            target_columns_to_types,
            primary_key=primary_key,
            exists=exists,
            table_description=table_description,
            column_descriptions=column_descriptions,
            **kwargs,
        )

    def ctas(
        self,
        table_name: TableName,
        query_or_df: t.Any,
        target_columns_to_types: t.Optional[t.Dict[str, exp.DataType]] = None,
        exists: bool = True,
        table_description: t.Optional[str] = None,
        column_descriptions: t.Optional[t.Dict[str, str]] = None,
        source_columns: t.Optional[t.List[str]] = None,
        **kwargs: t.Any,
    ) -> None:
        self._ensure_schema_exists(table_name)
        super().ctas(
            table_name,
            query_or_df,
            target_columns_to_types=target_columns_to_types,
            exists=exists,
            table_description=table_description,
            column_descriptions=column_descriptions,
            source_columns=source_columns,
            **kwargs,
        )

    def _df_to_source_queries(
        self,
        df: DF,
        target_columns_to_types: t.Dict[str, exp.DataType],
        batch_size: int,
        target_table: TableName,
        source_columns: t.Optional[t.List[str]] = None,
    ) -> t.List[SourceQuery]:
        """
        Convert a DataFrame to source queries for insertion.

        Uses ADBC bulk ingestion (adbc_ingest) for efficient Arrow-native data transfer
        to Hardcharger, avoiding row-by-row insertion overhead.
        """
        import pyarrow as pa

        temp_table = self._get_temp_table(target_table)

        # Select only the source columns in the right order
        source_columns_to_types = (
            {col: target_columns_to_types[col] for col in source_columns}
            if source_columns
            else target_columns_to_types
        )
        ordered_df = df[list(source_columns_to_types.keys())]

        # Convert DataFrame to PyArrow Table for bulk ingestion
        arrow_table = pa.Table.from_pandas(ordered_df, preserve_index=False)
        # Pandas represents zoned timestamps in nanoseconds. DuckDB 2.0's
        # TIMESTAMPTZ_NS cannot yet cast directly to standard SQL timestamps.
        # Match standard TIMESTAMP/TIMESTAMPTZ target precision before ingest.
        for index, field in enumerate(arrow_table.schema):
            target_type = source_columns_to_types[field.name].sql(dialect=self.dialect).upper()
            if (
                pa.types.is_timestamp(field.type)
                and field.type.tz is not None
                and field.type.unit == "ns"
                and target_type in {"TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"}
            ):
                column = arrow_table.column(index).cast(
                    pa.timestamp("us", field.type.tz), safe=False
                )
                arrow_table = arrow_table.set_column(index, field.name, column)

        # Use ADBC bulk ingestion with temporary table
        # Note: DuckDB temporary tables cannot have catalog/schema prefixes,
        # so we only pass the table name when temporary=True
        self.cursor.adbc_ingest(
            table_name=temp_table.name,
            data=arrow_table,
            mode="create",
            temporary=True,
        )

        # Reference temp table by name only (no schema prefix for temporary tables)
        temp_table_name = exp.to_table(temp_table.name)

        return [
            SourceQuery(
                query_factory=lambda: exp.select(
                    *self._casted_columns(target_columns_to_types, source_columns)
                ).from_(temp_table_name),
                cleanup_func=lambda: self.drop_table(temp_table_name),
            )
        ]

    def _fetch_native_df(
        self, query: t.Union[exp.Expr, str], quote_identifiers: bool = False
    ) -> DF:
        """
        Fetches a Pandas DataFrame from a SQL query.

        Hardcharger returns Arrow tables which can be efficiently converted to Pandas.
        """
        sql = self._to_sql(query, quote=quote_identifiers) if isinstance(query, exp.Expr) else query

        with self.transaction():
            cursor = self.cursor
            cursor.execute(sql)
            return cursor.fetch_arrow_table().to_pandas(date_as_object=False)
