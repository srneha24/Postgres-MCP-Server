# Postgres MCP Server

A Model Context Protocol (MCP) server that provides secure read-only access to PostgreSQL databases. This server enables AI assistants and other MCP clients to query database schemas and execute SELECT queries on PostgreSQL databases.

## Features

- **Read-only Database Access**: Execute SELECT queries safely with automatic blocking of INSERT, UPDATE, DELETE, CREATE, DROP, and ALTER statements
- **Schema Inspection**: Retrieve complete database schema including tables, columns, data types, and indexes
- **JSON Serialization**: Automatic conversion of PostgreSQL data types (UUIDs, decimals, dates, etc.) to JSON-compatible formats
- **Environment-based Configuration**: Flexible database connection configuration via environment variables

## Tools

The server exposes the following MCP tools (defined in `main.py`):

### `query_database`

Execute a SQL SELECT query on the PostgreSQL database.

Parameters:

- `sql_query` (string): The SQL query to execute (only SELECT queries are allowed).

Returns: JSON string with query results or an error object.

### `get_database_schema`

Retrieve columns for all tables in a schema (defaults to `public`).

Parameters:

- `schema` (string, optional): Schema name to inspect. Default: `public`.

Returns: JSON string of rows with fields `(table_name, column_name, data_type, is_nullable, column_default)`.

### `get_database_schema_with_indexes`

Retrieve schema and indexes for all tables in a schema (defaults to `public`).

Parameters:

- `schema` (string, optional): Schema name to inspect. Default: `public`.

Returns: JSON string mapping each table to its `columns` and `indexes` (index entries include `index_name`, `columns`, `is_unique`, `is_primary`).

### `get_table_schema`

Retrieve column information for a specific table.

Parameters:

- `table_name` (string): The table name.
- `schema` (string, optional): Schema name to inspect. Default: `public`.

Returns: JSON string of rows with fields `(column_order, column_name, data_type, is_nullable, default_value, column_comment)` or an error if the table does not exist.

### `get_table_schema_with_indexes`

Retrieve columns and indexes for a specific table.

Parameters:

- `table_name` (string): The table name.
- `schema` (string, optional): Schema name to inspect. Default: `public`.

Returns: JSON string with keys `columns` and `indexes` for the given table, or an error if the table does not exist.

### `get_table_indexes`

Retrieve index information for a specific table.

Parameters:

- `table_name` (string): The table name.
- `schema` (string, optional): Schema name to inspect. Default: `public`.

Returns: JSON string of index rows `(index_name, column_name, is_unique, is_primary)` or a message if no indexes are found.

### `list_tables`

List all tables in the specified schema (defaults to `public`).

Parameters:

- `schema` (string, optional): Schema name to list tables from. Default: `public`.

Returns: JSON string array of table names.

### `ping_database`

Health-check tool to verify connectivity to the Postgres database.

Parameters: None

Returns: JSON object with `status` ("success" or "error") and a `message` describing the result.

### `list_database_schemas`

List all non-system schemas in the connected Postgres database.

Parameters: None

Returns: JSON string array of schema names (system schemas like `pg_catalog` and `information_schema` are excluded).

## Installation

### Prerequisites

- Python 3.13 or higher
- PostgreSQL database (local or remote)

### Setup

1. Clone this repository:

    ```bash
    git clone <repository-url>
    cd Postgres-MCP-Server
    ```

2. Install uv if you haven't already:

    ```bash
    pip install uv
    ```

3. Create a virtual environment and install dependencies

    ```bash
    uv venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    uv sync
    ```

## Usage

### Using with Claude Desktop

Add this server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/postgres-mcp-server",
        "run",
        "main.py"
      ],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "your_database",
        "DB_USER": "your_username",
        "DB_PASSWORD": "your_password"
      }
    }
  }
}
```

**Note**: Replace `/ABSOLUTE/PATH/TO/postgres-mcp-server` with the actual absolute path to your installation directory. On Windows, use backslashes (e.g., `C:\\Users\\YourName\\postgres-mcp-server`) or forward slashes.

### Using with Claude Code

Open up your preferred terminal and run the following command to add the MCP to Claude Code.

```bash
claude mcp add postgres --transport stdio --env DB_HOST=localhost --env DB_PORT=5432 --env DB_NAME=your_database_name --env DB_USER=postgres --env DB_PASSWORD=postgres -- uv --directory /ABSOLUTE/PATH/TO/postgres-mcp-server run main.py
```

You can also add the MCP just for your current project using the following command -

```bash
claude mcp add postgres --transport stdio --env DB_HOST=localhost --env DB_PORT=5432 --env DB_NAME=your_database_name --env DB_USER=postgres --env DB_PASSWORD=postgres --scope local -- uv --directory /ABSOLUTE/PATH/TO/postgres-mcp-server run main.py
```

### Using with ChatGPT Codex

Open up your preferred terminal and run the following command to add the MCP to ChatGPT Codex.

```bash
codex mcp add postgres --env DB_HOST=localhost --env DB_PORT=5432 --env DB_NAME=your_database_name --env DB_USER=postgres --env DB_PASSWORD=postgres -- uv --directory /ABSOLUTE/PATH/TO/postgres-mcp-server run main.py
```

You can also add the following config directly into the `C:\Users\YourName\.codex\config.toml` file, or to your project's `YourProjectPath/.codex/config.toml` file to add the MCP only for that project.

```toml
[mcp_servers.postgres]
command = "uv"
args = ["--directory", "/ABSOLUTE/PATH/TO/postgres-mcp-server", "run", "main.py"]

[mcp_servers.postgres.env]
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres'
```

**Note**: Replace `/ABSOLUTE/PATH/TO/postgres-mcp-server` with the actual absolute path to your installation directory. On Windows, use backslashes (e.g., `C:\\Users\\YourName\\postgres-mcp-server`) or forward slashes.

## Security Features

- **Read-only Operations**: The server automatically blocks any queries containing INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, TRUNCATE, GRANT, REVOKE, COPY, or MERGE keywords
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Connection Management**: Proper database connection lifecycle management
