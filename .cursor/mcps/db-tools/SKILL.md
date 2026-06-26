---
name: db-tools
description: Database tools for MySQL and MongoDB with multi-environment support. Execute queries, switch environments, explore schemas. Use when user asks to query database, check table structure, explore MySQL or MongoDB data, switch environments (local/dev/prod), or run SQL/MongoDB commands.
---

# Database Tools MCP

## Environment Variables

The server maintains an in-memory environment configuration. Switch between environments using the `switch_env` tool.

## Environment Management

| Tool | Description |
|------|-------------|
| `switch_env` | Switch to local/dev/prod |
| `list_envs` | List available environments |
| `current_env` | Show current environment |

## MySQL Operations

| Tool | Description |
|------|-------------|
| `query` | Execute SQL query |
| `list_tables` | Show all tables |
| `describe_table` | Show table structure |

## MongoDB Operations

| Tool | Description |
|------|-------------|
| `query_mongodb` | Query collection |
| `list_collections` | Show all collections |

## Usage Examples

```python
# Check current environment
current_env()

# Switch to dev environment
switch_env(env="dev")

# Switch to production (be careful!)
switch_env(env="prod")

# Query MySQL
query(sql="SELECT * FROM llm_agent_instance LIMIT 10")

# List tables
list_tables()

# Describe table
describe_table(table="llm_agent_instance")

# Query MongoDB
query_mongodb(collection="user_actions", filter={"userId": "123"}, limit=50)

# List collections
list_collections()
```

## Environment Configuration

To modify environment settings, edit `ENVIRONMENTS` dict in `db_tools_server.py`:

```python
ENVIRONMENTS = {
    "local": {
        "MYSQL_URL": "jdbc:mysql://localhost:3306/llm_agent",
        "MYSQL_USR": "dev",
        "MYSQL_PWD": "xxx",
        "MONGODB_URL": "mongodb://...",
    },
    "dev": {
        # dev environment config
    },
    "prod": {
        # production config
    }
}
```

**Note**: After editing, restart Cursor to reload the server.
