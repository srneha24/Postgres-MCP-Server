import os
import json
import psycopg2
import logging
from psycopg2 import OperationalError, ProgrammingError, DatabaseError, InterfaceError
from mcp.server.fastmcp import FastMCP
from decimal import Decimal
from datetime import datetime, date, time
from uuid import UUID
from typing import Optional

logging.basicConfig(level=logging.INFO)


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


mcp = FastMCP("Postgres MCP Server")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def simplify_json(obj):
    """Converts objects in a dict/list that are not JSON encodable into JSON encodable objects"""

    def convert_to_basic(o):
        if isinstance(o, dict):
            return {k: convert_to_basic(v) for k, v in o.items()}
        elif isinstance(o, list):
            return [convert_to_basic(e) for e in o]
        elif isinstance(o, datetime) or isinstance(o, date) or isinstance(o, time):
            return o.isoformat()
        elif isinstance(o, UUID) or isinstance(o, bytes):
            return str(o)
        elif isinstance(o, Decimal):
            return float(o)
        else:
            return o

    return convert_to_basic(obj)


@mcp.tool()
def query_database(sql_query: str) -> str:
    """
    Execute a SQL query on a Postgres database and return the results.

    Args:
        sql_query (str): The SQL query to execute.
    Returns:
        str: The results of the query as a JSON string.
    """

    BLOCKED_KEYWORDS = (
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "CREATE ",
        "DROP ",
        "ALTER ",
        "TRUNCATE ",
        "GRANT ",
        "REVOKE ",
        "COPY ",
        "MERGE ",
    )
    upper_query = sql_query.upper()
    if any(keyword in upper_query for keyword in BLOCKED_KEYWORDS):
        logging.warning("Write/DDL queries are not allowed.")
        return json.dumps(
            {
                "error": "Write and DDL queries are not allowed. Only read queries are permitted."
            }
        )

    logging.info(f"Executing query: {sql_query}")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"})
    except ProgrammingError as e:
        logging.error(f"SQL query error: {e}")
        return json.dumps({"error": f"SQL query error: {e}"})
    except DatabaseError as e:
        logging.error(f"Database error: {e}")
        return json.dumps({"error": f"Database error: {e}"})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return json.dumps(simplify_json(rows), indent=2)


@mcp.tool()
def get_database_schema(schema: Optional[str] = "public") -> str:
    """
    Get the database schema including all tables, their columns, and indexes.

    Args:
        schema (str): Optional. The database schema to query. Defaults to "public".

    Returns:
        str: A JSON string containing tables with their columns, data types, and indexes.
    """
    logging.info("Fetching database schema...")

    schema_query = f"""
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM
        information_schema.columns
    WHERE
        table_schema = '{schema}'
    ORDER BY
        table_name, ordinal_position;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(schema_query)
        column_rows = cursor.fetchall()

        return json.dumps(column_rows, indent=2)
    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"})
    except ProgrammingError as e:
        logging.error(f"SQL error fetching schema: {e}")
        return json.dumps({"error": f"SQL error fetching schema: {e}"})
    except DatabaseError as e:
        logging.error(f"Database error fetching schema: {e}")
        return json.dumps({"error": f"Database error fetching schema: {e}"})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def get_database_schema_with_indexes(schema: Optional[str] = "public") -> str:
    """
    Get the database schema including all tables, their columns, and indexes.

    Args:
        schema (str): Optional. The database schema to query. Defaults to "public".

    Returns:
        str: A JSON string containing tables with their columns, data types, and indexes.
    """
    logging.info("Fetching database schema...")

    schema_query = f"""
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM
        information_schema.columns
    WHERE
        table_schema = '{schema}'
    ORDER BY
        table_name, ordinal_position;
    """

    indexes_query = f"""
    SELECT
        t.relname AS table_name,
        i.relname AS index_name,
        a.attname AS column_name,
        ix.indisunique AS is_unique,
        ix.indisprimary AS is_primary
    FROM
        pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE
        n.nspname = '{schema}'
    ORDER BY
        t.relname, i.relname, a.attnum;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(schema_query)
        column_rows = cursor.fetchall()

        schema = {}
        for row in column_rows:
            table_name, column_name, data_type, is_nullable, column_default = row

            if table_name not in schema:
                schema[table_name] = {"columns": [], "indexes": []}

            schema[table_name]["columns"].append(
                {
                    "column_name": column_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable,
                    "column_default": column_default,
                }
            )

        cursor.execute(indexes_query)
        index_rows = cursor.fetchall()

        for row in index_rows:
            table_name, index_name, column_name, is_unique, is_primary = row

            if table_name not in schema:
                continue

            # Check if this is a new index or continuation of previous
            existing_index = next(
                (
                    idx
                    for idx in schema[table_name]["indexes"]
                    if idx["index_name"] == index_name
                ),
                None,
            )

            if existing_index:
                existing_index["columns"].append(column_name)
            else:
                schema[table_name]["indexes"].append(
                    {
                        "index_name": index_name,
                        "columns": [column_name],
                        "is_unique": is_unique,
                        "is_primary": is_primary,
                    }
                )

        return json.dumps(schema, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"})
    except ProgrammingError as e:
        logging.error(f"SQL error fetching schema: {e}")
        return json.dumps({"error": f"SQL error fetching schema: {e}"})
    except DatabaseError as e:
        logging.error(f"Database error fetching schema: {e}")
        return json.dumps({"error": f"Database error fetching schema: {e}"})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def get_table_schema(table_name: str, schema: Optional[str] = "public") -> str:
    """
    Get the schema of a specific table including its columns.

    Args:
        table_name (str): The name of the table.
        schema (str): Optional. The database schema to query. Defaults to "public".
    Returns:
        str: A JSON string containing the table's columns, data types.
    """
    logging.info(f"Fetching schema for table: {table_name}")

    schema_query = f"""
    SELECT
        a.attnum AS column_order,
        a.attname AS column_name,
        pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
        NOT a.attnotnull AS is_nullable,
        pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
        col_description(a.attrelid, a.attnum) AS column_comment
    FROM pg_attribute a
    JOIN pg_class t ON a.attrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
    WHERE n.nspname = '{schema}'
    AND t.relname = %s
    AND a.attnum > 0
    AND NOT a.attisdropped
    ORDER BY a.attnum;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(schema_query, (table_name,))
        column_rows = cursor.fetchall()

        if not column_rows:
            logging.warning(f"Table {table_name} does not exist.")
            return json.dumps({"error": f"Table {table_name} does not exist."})

        logging.info(f"Found schema for table: {table_name}")
        return json.dumps(column_rows, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"}, indent=2)
    except ProgrammingError as e:
        logging.error(f"SQL error fetching schema for table {table_name}: {e}")
        return json.dumps(
            {"error": f"SQL error fetching schema for table {table_name}: {e}"},
            indent=2,
        )
    except DatabaseError as e:
        logging.error(f"Database error fetching schema for table {table_name}: {e}")
        return json.dumps(
            {"error": f"Database error fetching schema for table {table_name}: {e}"},
            indent=2,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def get_table_schema_with_indexes(
    table_name: str, schema: Optional[str] = "public"
) -> str:
    """
    Get the schema of a specific table including its columns and indexes.

    Args:
        table_name (str): The name of the table.
        schema (str): Optional. The database schema to query. Defaults to "public".
    Returns:
        str: A JSON string containing the table's columns, data types.
    """
    logging.info(f"Fetching schema for table: {table_name}")

    schema_query = f"""
    SELECT
        a.attnum AS column_order,
        a.attname AS column_name,
        pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
        NOT a.attnotnull AS is_nullable,
        pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
        col_description(a.attrelid, a.attnum) AS column_comment
    FROM pg_attribute a
    JOIN pg_class t ON a.attrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
    WHERE n.nspname = '{schema}'
    AND t.relname = %s
    AND a.attnum > 0
    AND NOT a.attisdropped
    ORDER BY a.attnum;
    """

    index_query = f"""
    SELECT
        i.relname AS index_name,
        a.attname AS column_name,
        ix.indisunique AS is_unique,
        ix.indisprimary AS is_primary
    FROM pg_class t
    JOIN pg_index ix ON t.oid = ix.indrelid
    JOIN pg_class i ON i.oid = ix.indexrelid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = '{schema}'
    AND t.relname = %s
    ORDER BY i.relname, a.attnum;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        table_schema = {"columns": [], "indexes": []}

        cursor.execute(schema_query, (table_name,))
        column_rows = cursor.fetchall()

        if not column_rows:
            logging.warning(f"Table {table_name} does not exist.")
            return json.dumps({"error": f"Table {table_name} does not exist."})

        table_schema["columns"] = column_rows

        cursor.execute(index_query, (table_name,))
        index_rows = cursor.fetchall()
        for row in index_rows:
            index_name, column_name, is_unique, is_primary = row

            # Check if this is a new index or continuation of previous
            existing_index = next(
                (
                    idx
                    for idx in table_schema["indexes"]
                    if idx["index_name"] == index_name
                ),
                None,
            )

            if existing_index:
                existing_index["columns"].append(column_name)
            else:
                table_schema["indexes"].append(
                    {
                        "index_name": index_name,
                        "columns": [column_name],
                        "is_unique": is_unique,
                        "is_primary": is_primary,
                    }
                )

        return json.dumps(table_schema, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"}, indent=2)
    except ProgrammingError as e:
        logging.error(f"SQL error fetching schema for table {table_name}: {e}")
        return json.dumps(
            {"error": f"SQL error fetching schema for table {table_name}: {e}"},
            indent=2,
        )
    except DatabaseError as e:
        logging.error(f"Database error fetching schema for table {table_name}: {e}")
        return json.dumps(
            {"error": f"Database error fetching schema for table {table_name}: {e}"},
            indent=2,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def get_table_indexes(table_name: str, schema: Optional[str] = "public") -> str:
    """
    Get the indexes of a specific table.

    Args:
        table_name (str): The name of the table.
        schema (str): Optional. The database schema to query. Defaults to "public".
    Returns:
        str: A JSON string containing the table's indexes.
    """
    logging.info(f"Fetching indexes for table: {table_name}")

    indexes_query = f"""
    SELECT
        i.relname AS index_name,
        a.attname AS column_name,
        ix.indisunique AS is_unique,
        ix.indisprimary AS is_primary
    FROM pg_class t
    JOIN pg_index ix ON t.oid = ix.indrelid
    JOIN pg_class i ON i.oid = ix.indexrelid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = '{schema}'
    AND t.relname = %s
    ORDER BY i.relname, a.attnum;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(indexes_query, (table_name,))
        index_rows = cursor.fetchall()

        if not index_rows:
            logging.warning(f"No indexes found for table {table_name}.")
            return json.dumps({"message": f"No indexes found for table {table_name}."})

        return json.dumps(index_rows, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"}, indent=2)
    except ProgrammingError as e:
        logging.error(f"SQL error fetching indexes for table {table_name}: {e}")
        return json.dumps(
            {"error": f"SQL error fetching indexes for table {table_name}: {e}"},
            indent=2,
        )
    except DatabaseError as e:
        logging.error(f"Database error fetching indexes for table {table_name}: {e}")
        return json.dumps(
            {"error": f"Database error fetching indexes for table {table_name}: {e}"},
            indent=2,
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def list_tables(schema: Optional[str] = "public") -> str:
    """
    List all tables in the specified schema of the database.

    Args:
        schema (str): Optional. The database schema to query. Defaults to "public".

    Returns:
        str: A JSON string containing the list of table names.
    """
    logging.info(f"Listing all tables in the {schema} schema...")

    tables_query = f"""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = '{schema}'
    AND table_type = 'BASE TABLE';
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(tables_query)
        table_rows = cursor.fetchall()
        table_names = [row[0] for row in table_rows]

        logging.info(f"Found {len(table_names)} tables.")
        return json.dumps(table_names, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"})
    except ProgrammingError as e:
        logging.error(f"SQL error listing tables: {e}")
        return json.dumps({"error": f"SQL error listing tables: {e}"})
    except DatabaseError as e:
        logging.error(f"Database error listing tables: {e}")
        return json.dumps({"error": f"Database error listing tables: {e}"})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@mcp.tool()
def ping_database() -> str:
    """
    Ping the Postgres database to check connectivity.

    Returns:
        str: A message indicating the status of the connection.
    """
    logging.info("Pinging the database...")

    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        conn.close()
        return json.dumps(
            {"status": "success", "message": "Database connection successful."}
        )
    except OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        return json.dumps(
            {"status": "error", "message": f"Database connection failed: {e}"}
        )
    except InterfaceError as e:
        logging.error(f"Database interface error: {e}")
        return json.dumps(
            {"status": "error", "message": f"Database interface error: {e}"}
        )


@mcp.tool()
def list_database_schemas() -> str:
    """
    List all schemas in the Postgres database.

    Returns:
        str: A JSON string containing the list of schema names.
    """
    logging.info("Listing all database schemas...")

    schemas_query = """
    SELECT schema_name
    FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schema_name;
    """

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        cursor.execute(schemas_query)
        schema_rows = cursor.fetchall()
        schema_names = [row[0] for row in schema_rows]

        logging.info(f"Found {len(schema_names)} schemas.")
        return json.dumps(schema_names, indent=2)

    except OperationalError as e:
        logging.error(f"Database connection error: {e}")
        return json.dumps({"error": f"Database connection error: {e}"})
    except ProgrammingError as e:
        logging.error(f"SQL error listing schemas: {e}")
        return json.dumps({"error": f"SQL error listing schemas: {e}"})
    except DatabaseError as e:
        logging.error(f"Database error listing schemas: {e}")
        return json.dumps({"error": f"Database error listing schemas: {e}"})
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    logging.info("Starting Postgres MCP Server...")
    mcp.run(transport="stdio")
