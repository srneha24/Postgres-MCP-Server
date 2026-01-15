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

Retrieve columns for all tables in the `public` schema.

Parameters: None

Returns: JSON string of rows with fields `(table_name, column_name, data_type, is_nullable, column_default)`.

### `get_database_schema_with_indexes`

Retrieve schema and indexes for all tables in the `public` schema.

Parameters: None

Returns: JSON string mapping each table to its `columns` and `indexes` (index entries include `index_name`, `columns`, `is_unique`, `is_primary`).

### `get_table_schema`

Retrieve column information for a specific table.

Parameters:

- `table_name` (string): The table name.

Returns: JSON string of rows with fields `(column_order, column_name, data_type, is_nullable, default_value, column_comment)` or an error if the table does not exist.

### `get_table_schema_with_indexes`

Retrieve columns and indexes for a specific table.

Parameters:

- `table_name` (string): The table name.

Returns: JSON string with keys `columns` and `indexes` for the given table, or an error if the table does not exist.

### `get_table_indexes`

Retrieve index information for a specific table.

Parameters:

- `table_name` (string): The table name.

Returns: JSON string of index rows `(index_name, column_name, is_unique, is_primary)` or a message if no indexes are found.

### `list_tables`

List all tables in the `public` schema.

Parameters: None

Returns: JSON string array of table names.

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

1. Choose your preferred installation method:

#### Option A: Using uv (Recommended)

```bash
# Install uv if you haven't already
pip install uv

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

#### Option B: Using Python venv and pip

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Configure the database connection using environment variables:

```bash
export DB_HOST=localhost        # Default: localhost
export DB_PORT=5432            # Default: 5432
export DB_NAME=postgres        # Default: postgres
export DB_USER=postgres        # Default: postgres
export DB_PASSWORD=postgres    # Default: postgres
```

## Usage

### Running Standalone

```bash
python main.py
```

### Using with Claude Desktop

Add this server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### If using uv

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

#### If using Python directly

```json
{
  "mcpServers": {
    "postgres": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/postgres-mcp-server/main.py"],
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

#### If using uv

```bash
claude mcp add postgres --transport stdio --env DB_HOST=localhost --env DB_PORT=5432 --env DB_NAME=your_database_name --env DB_USER=postgres --env DB_PASSWORD=postgres -- uv --directory /ABSOLUTE/PATH/TO/postgres-mcp-server run main.py
```

#### If using Python directly

```bash
claude mcp add postgres --transport stdio --env DB_HOST=localhost --env DB_PORT=5432 --env DB_NAME=your_database_name --env DB_USER=postgres --env DB_PASSWORD=postgres -- python /ABSOLUTE/PATH/TO/postgres-mcp-server/main.py
```

**Note**: Replace `/ABSOLUTE/PATH/TO/postgres-mcp-server` with the actual absolute path to your installation directory. On Windows, use backslashes (e.g., `C:\\Users\\YourName\\postgres-mcp-server`) or forward slashes.

## Security Features

- **Read-only Operations**: The server automatically blocks any queries containing INSERT, UPDATE, DELETE, CREATE, DROP, or ALTER keywords
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Connection Management**: Proper database connection lifecycle management
