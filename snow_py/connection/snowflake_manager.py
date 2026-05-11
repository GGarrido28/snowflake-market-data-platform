from __future__ import annotations

import snowflake.connector
import logging
import json
import re
from datetime import datetime, date, time
from pathlib import Path
from uuid import UUID
from time import sleep
from typing import Any, Sequence

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from snow_py.connection.config import SNOWFLAKE_CONFIG

logging.basicConfig(level=logging.INFO)


class SnowflakeManager:
    @staticmethod
    def validate_identifier(name: str, identifier_type: str = "identifier") -> str:
        """
        Validate that a string is safe to use as a SQL identifier.

        Args:
            name (str): The identifier to validate
            identifier_type (str): Type of identifier for error messages

        Returns:
            str: The validated identifier

        Raises:
            ValueError: If the identifier contains invalid characters
        """
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid {identifier_type}: must be a non-empty string")

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            raise ValueError(
                f"Invalid {identifier_type} '{name}': must start with letter or underscore, "
                "and contain only alphanumeric characters and underscores"
            )

        sql_keywords = {'select', 'insert', 'update', 'delete', 'drop', 'truncate', 'alter', 'create'}
        if name.lower() in sql_keywords:
            raise ValueError(f"Invalid {identifier_type} '{name}': cannot use SQL keyword as identifier")

        return name

    def __init__(
        self,
        database: str,
        schema: str,
        warehouse: str | None = None,
        role: str | None = None,
        return_logging: bool = False,
    ) -> None:
        """
        Initialize a SnowflakeManager connection.

        Args:
            database (str): Snowflake database name
            schema (str): Snowflake schema name
            warehouse (str): Snowflake warehouse (overrides env var)
            role (str): Snowflake role (overrides env var)
            return_logging (bool): Whether to log verbose output
        """
        self.database: str = database
        self.schema: str = schema
        self.warehouse: str | None = warehouse or SNOWFLAKE_CONFIG.get("warehouse")
        self.role: str | None = role or SNOWFLAKE_CONFIG.get("role")
        self.return_logging: bool = return_logging

        # Validate identifiers
        self.validate_identifier(self.database, "database")
        self.validate_identifier(self.schema, "schema")

        # Validate essential connection parameters
        self.account: str | None = SNOWFLAKE_CONFIG.get("account")
        self.user: str | None = SNOWFLAKE_CONFIG.get("user")
        self.private_key_path: str | None = SNOWFLAKE_CONFIG.get("private_key_path")
        self.private_key_passphrase: str | None = SNOWFLAKE_CONFIG.get("private_key_passphrase")

        for param_name, param_value in [
            ("account", self.account),
            ("user", self.user),
            ("private_key_path", self.private_key_path),
        ]:
            if not param_value:
                env_var = f"SNOWFLAKE_{param_name.upper()}"
                raise ValueError(
                    f"Required connection parameter '{param_name}' is missing. "
                    f"Set the {env_var} environment variable."
                )

        self._private_key_bytes: bytes = self._load_private_key()

        self.connect_with_retries()

        if self.return_logging:
            logging.info(f"Connected to Snowflake: {self.account}")
            logging.info(f"Database: {self.database}, Schema: {self.schema}")
            logging.info(f"Warehouse: {self.warehouse}, Role: {self.role}")

    def _load_private_key(self) -> bytes:
        """Load and serialize the RSA private key for Snowflake key-pair auth."""
        key_path = Path(self.private_key_path).expanduser()
        if not key_path.exists():
            raise FileNotFoundError(
                f"Snowflake private key not found at {key_path}. "
                "Set SNOWFLAKE_PRIVATE_KEY_PATH to the correct .p8 file."
            )

        passphrase_bytes = (
            self.private_key_passphrase.encode() if self.private_key_passphrase else None
        )
        with key_path.open("rb") as fh:
            private_key = serialization.load_pem_private_key(
                fh.read(),
                password=passphrase_bytes,
                backend=default_backend(),
            )

        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_cursor(self) -> snowflake.connector.cursor.SnowflakeCursor:
        """Get a new cursor, creating a new connection if necessary."""
        try:
            if self.connection.is_closed():
                logging.info("Connection lost, reconnecting...")
                self.connect_with_retries()
            return self.connection.cursor()
        except Exception:
            logging.info("Connection lost, reconnecting...")
            self.connect_with_retries()
            return self.connection.cursor()

    def connect_with_retries(self, max_retries: int = 5) -> bool:
        """Establish a connection to Snowflake with retry logic."""
        for attempt in range(max_retries):
            try:
                connect_params: dict[str, Any] = {
                    "account": self.account,
                    "user": self.user,
                    "private_key": self._private_key_bytes,
                    "database": self.database,
                    "schema": self.schema,
                }
                if self.warehouse:
                    connect_params["warehouse"] = self.warehouse
                if self.role:
                    connect_params["role"] = self.role

                self.connection: snowflake.connector.SnowflakeConnection = snowflake.connector.connect(**connect_params)

                if self.return_logging:
                    logging.info("Snowflake connection successful!")
                return True
            except snowflake.connector.errors.DatabaseError as e:
                logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    logging.info(f"Retrying in {sleep_time} seconds...")
                    sleep(sleep_time)
                else:
                    logging.error("All connection attempts failed")
                    raise ConnectionError("Cannot establish Snowflake connection")
        return False

    def _quote_identifier(self, name: str) -> str:
        """Quote a SQL identifier to prevent injection."""
        # Snowflake uses double quotes for identifiers
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    def execute(
        self,
        q: str,
        params: Sequence[Any] | None = None,
        raise_exc: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results as a list of dicts.

        Args:
            q (str): SQL query
            params (tuple/list): Query parameters
            raise_exc (bool): Whether to raise exceptions

        Returns:
            list[dict]: Query results
        """
        cursor = self.get_cursor()
        if self.return_logging:
            logging.info(q)
        results: list[dict[str, Any]] = []
        try:
            if params:
                cursor.execute(q, params)
            else:
                cursor.execute(q)

            if cursor.description:
                field_names = [i[0].lower() for i in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(field_names, row)) for row in rows]
            return results
        except Exception as e:
            if self.return_logging:
                logging.warning(e)
            if raise_exc:
                raise
            return results
        finally:
            cursor.close()

    def execute_query(self, query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        """Execute a query and return results as a list of dicts (alias for execute)."""
        return self.execute(query, params)

    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the current database/schema.

        Args:
            table_name (str): Table name to check

        Returns:
            bool: True if table exists
        """
        self.validate_identifier(table_name, "table")
        try:
            cursor = self.get_cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s",
                (self.schema.upper(), table_name.upper())
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] > 0 if result else False
        except Exception as e:
            logging.error(f"Error checking if table exists: {e}")
            return False

    def get_table_primary_key(self, table: str) -> list[str] | None:
        """
        Get primary key columns for a table.

        Note: Snowflake supports primary key constraints but they are informational only
        (not enforced). This queries the constraint metadata.

        Args:
            table (str): Table name

        Returns:
            list or None: List of primary key column names, or None
        """
        self.validate_identifier(table, "table")
        try:
            cursor = self.get_cursor()
            cursor.execute(
                "SHOW PRIMARY KEYS IN TABLE {}.{}.{}".format(
                    self._quote_identifier(self.database),
                    self._quote_identifier(self.schema),
                    self._quote_identifier(table)
                )
            )
            rows = cursor.fetchall()
            cursor.close()

            if rows:
                # SHOW PRIMARY KEYS returns columns; column_name is at index 4
                pk_cols = [row[4].lower() for row in rows]
                return pk_cols if pk_cols else None
            return None
        except Exception as e:
            logging.warning(f"Error getting primary key for {table}: {e}")
            return None

    def determine_column_type(self, values: list[Any]) -> str:
        """
        Determine the appropriate Snowflake type for a column based on its values.

        Args:
            values (list): Sample values for the column

        Returns:
            str: Snowflake data type
        """
        type_map: dict[type, str] = {
            str: "VARCHAR",
            float: "FLOAT",
            bool: "BOOLEAN",
            dict: "VARIANT",
            list: "VARIANT",
            datetime: "TIMESTAMP_NTZ",
            date: "DATE",
            time: "TIME",
            bytes: "BINARY",
            UUID: "VARCHAR(36)",
        }

        non_none_values = [value for value in values if value is not None]
        encountered_types = set(type(value) for value in non_none_values)

        if len(encountered_types) == 0:
            return "VARCHAR"

        if len(encountered_types) == 1:
            encountered_type = next(iter(encountered_types))
            if encountered_type == int:
                max_value = max(non_none_values)
                min_value = min(non_none_values)
                if -32768 <= min_value <= 32767 and max_value <= 32767:
                    return "SMALLINT"
                elif -2147483648 <= min_value <= 2147483647 and max_value <= 2147483647:
                    return "INTEGER"
                else:
                    return "BIGINT"
            return type_map.get(encountered_type, "VARCHAR")

        if encountered_types <= {int, float}:
            return "FLOAT"
        elif encountered_types <= {str, int, float}:
            return "VARCHAR"
        elif encountered_types <= {datetime, str}:
            return "TIMESTAMP_NTZ"
        elif encountered_types <= {date, str}:
            return "DATE"
        elif encountered_types <= {time, str}:
            return "TIME"
        else:
            return "VARCHAR"

    def get_all_columns(self, rows: list[dict[str, Any]], columns: list[str] | None = None) -> list[str]:
        """Extract all unique column names from a list of dicts, ensuring all rows have all columns."""
        if columns is None:
            columns = []

        has_all_columns = True
        for row in rows:
            if list(row.keys()) != columns:
                has_all_columns = False
                for key in row:
                    if key not in columns:
                        columns.append(key)
        if not has_all_columns:
            for col in columns:
                for row in rows:
                    if col not in row:
                        row[col] = None
        return columns

    def check_duplicate_rows(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
    ) -> tuple[bool, dict[str, int]]:
        """Check for duplicate rows based on specified columns."""
        if columns is None:
            columns = []
        duplicates = False
        duplicate_rows: dict[str, int] = {}

        for row in rows:
            filtered_row = {key: row[key] for key in columns if key in row}
            if not filtered_row:
                continue
            for key, value in filtered_row.items():
                if isinstance(value, (dict, list)):
                    filtered_row[key] = json.dumps(value)
                elif isinstance(value, (datetime, date)):
                    filtered_row[key] = value.isoformat()
                elif isinstance(value, UUID):
                    filtered_row[key] = str(value)

            row_key = json.dumps(filtered_row, sort_keys=True)

            if row_key in duplicate_rows:
                duplicates = True
                duplicate_rows[row_key] += 1
            else:
                duplicate_rows[row_key] = 1

        flagged_duplicates = {
            key: count for key, count in duplicate_rows.items() if count > 1
        }

        return duplicates, flagged_duplicates

    def insert_rows(
        self,
        target_table: str,
        columns: list[str],
        rows: list[dict[str, Any]],
        contains_dicts: bool = False,
        update: bool = False,
        return_error_msg: bool = False,
    ) -> bool | tuple[bool, str | None]:
        """
        Insert rows into a Snowflake table.

        Args:
            target_table (str): Table to insert into
            columns (list): Column names
            rows (list): Data rows (list of dicts if contains_dicts=True)
            contains_dicts (bool): Whether rows are dicts
            update (bool): Whether to upsert (uses MERGE)
            return_error_msg (bool): If True, return (success, error_msg) tuple

        Returns:
            bool or tuple: Success status, optionally with error message
        """
        self.validate_identifier(target_table, "table")

        try:
            if not rows:
                message = f"No rows provided for insert into {target_table}"
                logging.info(message)
                return (True, message) if return_error_msg else True

            check_dupes, dupe_rows = self.check_duplicate_rows(rows, columns)
            if check_dupes:
                logging.warning("Duplicate rows found in data.")
                logging.warning(dupe_rows)
                duplicate_rows = []
                for key in dupe_rows:
                    for row in rows:
                        filtered_row = {k: row[k] for k in columns}
                        if json.dumps(filtered_row) == key:
                            duplicate_rows.append(row)
                for row in duplicate_rows:
                    logging.info(row)
                    rows.remove(row)

            pk = self.get_table_primary_key(target_table)
            if pk is None and update:
                error_msg = f"Cannot perform upsert on table {target_table} - no primary key defined"
                logging.error(error_msg)
                return (False, error_msg) if return_error_msg else False

            if pk:
                check_dupe_keys, dupe_keys = self.check_duplicate_rows(rows, pk)
                if check_dupe_keys:
                    logging.warning("Duplicate primary keys found in data.")
                    logging.warning(dupe_keys)
                    duplicate_rows = []
                    for key in dupe_keys:
                        for row in rows:
                            filtered_row = {k: row[k] for k in pk}
                            if json.dumps(filtered_row) == key:
                                duplicate_rows.append(row)
                    for row in duplicate_rows:
                        logging.info(row)
                        rows.remove(row)

            columns = list(columns)
            columns = self.get_all_columns(rows, columns)

            for col in columns:
                self.validate_identifier(col, "column")

            # Prepare row values and track which columns contain dict/list (VARIANT) data
            variant_cols: set[str] = set()
            prepared_rows: list[tuple[Any, ...]] = []
            if contains_dicts:
                for row in rows:
                    prepared_row: list[Any] = []
                    for col in columns:
                        value = row.get(col)
                        if isinstance(value, (dict, list)):
                            variant_cols.add(col)
                            value = json.dumps(value)
                        elif value == "":
                            value = None
                        prepared_row.append(value)
                    prepared_rows.append(tuple(prepared_row))
            else:
                if isinstance(rows, dict):
                    prepared_row = [rows.get(col) for col in columns]
                    prepared_rows.append(tuple(prepared_row))
                else:
                    prepared_rows = [tuple(row) if isinstance(row, (list, tuple)) else (row,) for row in rows]

            quoted_cols = ", ".join(self._quote_identifier(col) for col in columns)
            placeholders = ", ".join(
                "PARSE_JSON(%s)" if col in variant_cols else "%s"
                for col in columns
            )
            qualified_table = f"{self._quote_identifier(self.database)}.{self._quote_identifier(self.schema)}.{self._quote_identifier(target_table)}"

            cursor = self.get_cursor()

            if update and pk:
                if self.return_logging:
                    logging.info("MERGE into %s (%s rows)", target_table, len(prepared_rows))
                self._execute_chunked_merge(
                    cursor=cursor,
                    qualified_table=qualified_table,
                    columns=columns,
                    prepared_rows=prepared_rows,
                    variant_cols=variant_cols,
                    primary_keys=pk,
                )
            else:
                # Standard INSERT — use INSERT INTO ... SELECT when VARIANT columns need PARSE_JSON()
                if variant_cols:
                    insert_query = f"INSERT INTO {qualified_table} ({quoted_cols}) SELECT {placeholders}"
                else:
                    insert_query = f"INSERT INTO {qualified_table} ({quoted_cols}) VALUES ({placeholders})"
                if self.return_logging:
                    logging.info(f"{insert_query} ({len(prepared_rows)} rows)")
                try:
                    cursor.executemany(insert_query, prepared_rows)
                except snowflake.connector.errors.InterfaceError as e:
                    # Some connector versions fail to rewrite bulk inserts for valid row sets.
                    if "Failed to rewrite multi-row insert" not in str(e):
                        raise
                    logging.warning(
                        "Bulk insert rewrite failed for %s; retrying with chunked multi-row inserts.",
                        target_table,
                    )
                    self._execute_chunked_insert(
                        cursor=cursor,
                        qualified_table=qualified_table,
                        columns=columns,
                        prepared_rows=prepared_rows,
                        variant_cols=variant_cols,
                    )

            cursor.close()
            logging.info(f"Rows inserted successfully into {target_table}")
            return (True, None) if return_error_msg else True

        except snowflake.connector.errors.ProgrammingError as e:
            error_msg = f"Snowflake programming error: {e}"
            logging.error(error_msg)
            return (False, error_msg) if return_error_msg else False
        except snowflake.connector.errors.DatabaseError as e:
            error_msg = f"Snowflake database error: {e}"
            logging.error(error_msg)
            return (False, error_msg) if return_error_msg else False
        except Exception as e:
            error_msg = f"Unexpected error inserting rows: {e}"
            logging.error(error_msg, exc_info=True)
            return (False, error_msg) if return_error_msg else False

    def _execute_chunked_insert(
        self,
        cursor: snowflake.connector.cursor.SnowflakeCursor,
        qualified_table: str,
        columns: list[str],
        prepared_rows: list[tuple[Any, ...]],
        variant_cols: set[str],
        chunk_size: int = 500,
    ) -> None:
        """Execute chunked inserts to reduce round trips when executemany rewrite fails."""
        quoted_cols = ", ".join(self._quote_identifier(col) for col in columns)
        row_placeholder = f"({', '.join(['%s'] * len(columns))})"
        total_chunks = (len(prepared_rows) + chunk_size - 1) // chunk_size

        if variant_cols:
            value_aliases = [f"c{i}" for i in range(len(columns))]
            aliased_cols = ", ".join(value_aliases)
            select_exprs = ", ".join(
                f"PARSE_JSON({alias})" if col in variant_cols else alias
                for alias, col in zip(value_aliases, columns)
            )

        for chunk_index, start in enumerate(range(0, len(prepared_rows), chunk_size), start=1):
            chunk = prepared_rows[start:start + chunk_size]
            flat_params = [value for row in chunk for value in row]

            if variant_cols:
                values_clause = ", ".join([row_placeholder] * len(chunk))
                insert_query = (
                    f"INSERT INTO {qualified_table} ({quoted_cols}) "
                    f"SELECT {select_exprs} "
                    f"FROM VALUES {values_clause} AS src({aliased_cols})"
                )
            else:
                values_clause = ", ".join([row_placeholder] * len(chunk))
                insert_query = f"INSERT INTO {qualified_table} ({quoted_cols}) VALUES {values_clause}"

            cursor.execute(insert_query, flat_params)

            if chunk_index == 1 or chunk_index == total_chunks or chunk_index % 10 == 0:
                logging.info(
                    "Inserted chunk %s/%s into %s (%s rows).",
                    chunk_index,
                    total_chunks,
                    qualified_table,
                    len(chunk),
                )

    def _build_values_source_query(
        self,
        columns: list[str],
        row_count: int,
        variant_cols: set[str],
    ) -> str:
        """Build a SELECT over VALUES that preserves VARIANT columns."""
        row_placeholder = f"({', '.join(['%s'] * len(columns))})"
        values_clause = ", ".join([row_placeholder] * row_count)
        value_aliases = [f"c{i}" for i in range(len(columns))]
        aliased_cols = ", ".join(value_aliases)
        select_exprs = ", ".join(
            f"PARSE_JSON(src.{alias}) AS {self._quote_identifier(col)}"
            if col in variant_cols
            else f"src.{alias} AS {self._quote_identifier(col)}"
            for alias, col in zip(value_aliases, columns)
        )
        return f"SELECT {select_exprs} FROM VALUES {values_clause} AS src({aliased_cols})"

    def _execute_chunked_merge(
        self,
        cursor: snowflake.connector.cursor.SnowflakeCursor,
        qualified_table: str,
        columns: list[str],
        prepared_rows: list[tuple[Any, ...]],
        variant_cols: set[str],
        primary_keys: list[str],
        chunk_size: int = 500,
    ) -> None:
        """Execute chunked MERGE statements so keyed loads upsert efficiently."""
        quoted_cols = ", ".join(self._quote_identifier(col) for col in columns)
        source_cols = ", ".join(
            f"source.{self._quote_identifier(col)}" for col in columns
        )
        on_clause = " AND ".join(
            f"target.{self._quote_identifier(pk)} = source.{self._quote_identifier(pk)}"
            for pk in primary_keys
        )
        update_cols = [col for col in columns if col not in primary_keys]
        total_chunks = (len(prepared_rows) + chunk_size - 1) // chunk_size

        for chunk_index, start in enumerate(range(0, len(prepared_rows), chunk_size), start=1):
            chunk = prepared_rows[start:start + chunk_size]
            flat_params = [value for row in chunk for value in row]
            source_query = self._build_values_source_query(
                columns=columns,
                row_count=len(chunk),
                variant_cols=variant_cols,
            )

            merge_query = (
                f"MERGE INTO {qualified_table} AS target "
                f"USING ({source_query}) AS source "
                f"ON {on_clause} "
            )
            if update_cols:
                set_clause = ", ".join(
                    f"target.{self._quote_identifier(col)} = source.{self._quote_identifier(col)}"
                    for col in update_cols
                )
                merge_query += f"WHEN MATCHED THEN UPDATE SET {set_clause} "
            merge_query += (
                f"WHEN NOT MATCHED THEN INSERT ({quoted_cols}) "
                f"VALUES ({source_cols})"
            )

            cursor.execute(merge_query, flat_params)

            if chunk_index == 1 or chunk_index == total_chunks or chunk_index % 10 == 0:
                logging.info(
                    "Merged chunk %s/%s into %s (%s rows).",
                    chunk_index,
                    total_chunks,
                    qualified_table,
                    len(chunk),
                )

    def get_tables(self) -> dict[str, dict[str, str]]:
        """
        Retrieve all tables and their columns in the current schema.

        Returns:
            dict: {table_name: {column_name: data_type}}
        """
        query = (
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = %s "
            "ORDER BY table_name, ordinal_position"
        )
        try:
            cursor = self.get_cursor()
            cursor.execute(query, (self.schema.upper(),))
            rows = cursor.fetchall()
            cursor.close()

            tables: dict[str, dict[str, str]] = {}
            for table_name, column_name, data_type in rows:
                table_lower = table_name.lower()
                if table_lower not in tables:
                    tables[table_lower] = {}
                tables[table_lower][column_name.lower()] = data_type
            return tables
        except Exception as e:
            logging.error(f"Error retrieving tables: {e}")
            return {}

    def create_table(
        self,
        dict_list: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        table_name: str | None = None,
        delete: bool = False,
    ) -> bool | tuple[bool, Exception]:
        """
        Create a Snowflake table from a list of dictionaries.

        Args:
            dict_list (list): List of dicts containing the data
            primary_keys (list): Primary key columns (informational in Snowflake)
            table_name (str): Table name
            delete (bool): If True, drop and recreate if exists

        Returns:
            bool: True if created successfully
        """
        if not dict_list:
            logging.info(f"No rows provided to create table {table_name}; skipping table creation.")
            return False

        if primary_keys and not isinstance(primary_keys, list):
            raise ValueError("Primary keys should be provided as a list")

        self.validate_identifier(table_name, "table")

        columns = self.get_all_columns(dict_list)
        for col in columns:
            self.validate_identifier(col, "column")

        columns_data: dict[str, list[Any]] = {key: [] for key in columns}
        for dictionary in dict_list:
            for key, value in dictionary.items():
                columns_data[key].append(value)

        columns_data: dict[str, str] = {
            key: self.determine_column_type(values) for key, values in columns_data.items()
        }

        qualified_table = f"{self._quote_identifier(self.database)}.{self._quote_identifier(self.schema)}.{self._quote_identifier(table_name)}"

        if primary_keys:
            for pk in primary_keys:
                self.validate_identifier(pk, "primary key")
            priority_found = [item for item in columns_data if item in primary_keys]
            remaining = [item for item in columns_data if item not in primary_keys]
            ordered_columns = priority_found + remaining
        else:
            ordered_columns = list(columns_data.keys())

        field_defs: list[str] = []
        for col in ordered_columns:
            field_defs.append(f"{self._quote_identifier(col)} {columns_data[col]}")

        pk_clause = ""
        if primary_keys:
            pk_cols = ", ".join(self._quote_identifier(pk) for pk in primary_keys)
            pk_clause = f", PRIMARY KEY ({pk_cols})"

        create_query = f"CREATE TABLE IF NOT EXISTS {qualified_table} ({', '.join(field_defs)}{pk_clause})"

        try:
            table_exists = self.check_table_exists(table_name)
            cursor = self.get_cursor()

            if table_exists:
                logging.info(f"Table '{table_name}' already exists.")
                if delete:
                    cursor.execute(f"DROP TABLE {qualified_table}")
                    logging.info(f"Table '{table_name}' dropped successfully.")
                    cursor.execute(create_query)
                    logging.info(f"Table '{table_name}' created successfully.")
                    cursor.close()
                    return True
                else:
                    cursor.close()
                    return False
            else:
                cursor.execute(create_query)
                logging.info(f"Table '{table_name}' created successfully.")
                cursor.close()
                return True
        except Exception as e:
            logging.error(f"Error creating table: {e}")
            return False, e

    def dump_to_dummy_table(self, dict_list: list[dict[str, Any]], table_name: str) -> bool:
        """
        Dump a list of dicts to a table without primary keys.

        Args:
            dict_list (list): Data to dump
            table_name (str): Target table name

        Returns:
            bool: True if successful
        """
        if not dict_list:
            logging.info(f"No rows provided to dump into {table_name}; skipping dummy table load.")
            return False

        self.validate_identifier(table_name, "table")

        columns = self.get_all_columns(dict_list)
        columns = sorted(columns)

        for col in columns:
            self.validate_identifier(col, "column")

        columns_data: dict[str, list[Any]] = {key: [] for key in columns}
        for dictionary in dict_list:
            for key, value in dictionary.items():
                columns_data[key].append(value)

        columns_data: dict[str, str] = {
            key: self.determine_column_type(values)
            for key, values in columns_data.items()
        }

        qualified_table = f"{self._quote_identifier(self.database)}.{self._quote_identifier(self.schema)}.{self._quote_identifier(table_name)}"

        field_defs = [
            f"{self._quote_identifier(col)} {col_type}"
            for col, col_type in columns_data.items()
        ]
        create_query = f"CREATE TABLE IF NOT EXISTS {qualified_table} ({', '.join(field_defs)})"

        try:
            cursor = self.get_cursor()
            cursor.execute(create_query)
            logging.info(f"Dummy table '{table_name}' created successfully.")

            quoted_cols = ", ".join(self._quote_identifier(col) for col in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert_query = f"INSERT INTO {qualified_table} ({quoted_cols}) VALUES ({placeholders})"

            rows = [tuple(row.get(col) for col in columns) for row in dict_list]
            cursor.executemany(insert_query, rows)
            cursor.close()
            logging.info(f"Data successfully dumped into dummy table '{table_name}'.")
            return True

        except Exception as e:
            logging.error(f"Error dumping data to dummy table: {e}")
            return False

    def close(self) -> None:
        """Close the Snowflake connection."""
        try:
            if hasattr(self, "connection") and self.connection:
                self.connection.close()
                if self.return_logging:
                    logging.info("Connection closed")
        except Exception as e:
            logging.warning(f"Error closing connection: {e}")
