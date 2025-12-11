import os
import json
import psycopg2
import logging
from mcp.server.fastmcp import FastMCP
from decimal import Decimal
from datetime import datetime, date, time
from uuid import UUID

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
def query_data(sql_query: str) -> str:
    """
    Execute a SQL query on a Postgres database and return the results.

    Args:
        sql_query (str): The SQL query to execute.
    Returns:
        str: The results of the query as a JSON string.
    """

    if any(
        keyword in sql_query.upper()
        for keyword in ["INSERT ", "UPDATE ", "DELETE ", "CREATE ", "DROP ", "ALTER "]
    ):
        logging.warning("Only SELECT queries are allowed.")
        return json.dumps({"error": "Only SELECT queries are allowed."})

    logging.info(f"Executing query: {sql_query}")

    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return json.dumps({"error": str(e)})
    finally:
        cursor.close()
        conn.close()

    return json.dumps(simplify_json(rows), indent=2)


@mcp.tool()
def get_schema() -> str:
    """
    Get the database schema including all tables, their columns, and indexes.

    Returns:
        str: A JSON string containing tables with their columns, data types, and indexes.
    """
    logging.info("Fetching database schema...")

    schema_query = """
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM
        information_schema.columns
    WHERE
        table_schema = 'public'
    ORDER BY
        table_name, ordinal_position;
    """

    indexes_query = """
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
        n.nspname = 'public'
    ORDER BY
        t.relname, i.relname, a.attnum;
    """

    try:
        conn = get_db_connection()
        logging.info("Database connection established.")
        cursor = conn.cursor()

        # Fetch columns
        cursor.execute(schema_query)
        column_rows = cursor.fetchall()

        # Organize columns by table
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

        # Fetch indexes
        cursor.execute(indexes_query)
        index_rows = cursor.fetchall()

        # Organize indexes by table
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

        logging.info(f"Found {len(schema)} tables in schema.")
        return json.dumps(schema, indent=2)

    except Exception as e:
        logging.error(f"Error fetching schema: {e}")
        return json.dumps({"error": str(e)})
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    logging.info("Starting Postgres MCP Server...")
    mcp.run(transport="stdio")
