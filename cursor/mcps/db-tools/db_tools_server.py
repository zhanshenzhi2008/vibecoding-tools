"""
Database Tools MCP Server
Supports MySQL and MongoDB with multi-environment configuration.
Usage: switch_env(env_name) - env_name: local, dev, uat, prod
"""

import os
import re
import json
from typing import Any

try:
    import mysql.connector
    from pymongo import MongoClient
    MYSQL_AVAILABLE = True
    MONGO_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MONGO_AVAILABLE = False

# Environment configuration directory
ENV_DIR = "F:/gientech-repository/env"


def parse_env_file(file_path: str) -> dict:
    """Parse .env file and return key-value pairs"""
    config = {}
    if not os.path.exists(file_path):
        return config
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Match KEY="value" or KEY=value
            match = re.match(r'^([A-Z_][A-Z0-9_]*)="?([^"]*)"?$', line)
            if match:
                key, value = match.groups()
                config[key] = value.strip()
    return config


def load_environments() -> dict:
    """Load all environments from env directory"""
    envs = {}
    
    env_files = {
        "local": ".env-local",
        "dev": ".env-dev",
        "uat": ".env-uat",
    }
    
    for env_name, filename in env_files.items():
        file_path = os.path.join(ENV_DIR, filename)
        config = parse_env_file(file_path)
        if config:
            envs[env_name] = {
                "MYSQL_URL": config.get("MYSQL_URL", ""),
                "MYSQL_USR": config.get("MYSQL_USR", ""),
                "MYSQL_PWD": config.get("MYSQL_PWD", ""),
                "MONGODB_URL": config.get("MONGODB_URL", ""),
                "MONGODB_DATABASE": _extract_mongo_db(config.get("MONGODB_URL", "")),
                "REDIS_HOST": config.get("REDIS_HOST", ""),
                "REDIS_PORT": config.get("REDIS_PORT", ""),
            }
    
    # Add prod placeholder if not exists
    if "prod" not in envs:
        envs["prod"] = {
            "MYSQL_URL": "jdbc:mysql://prod-host:3306/llm_agent",
            "MYSQL_USR": "prod_user",
            "MYSQL_PWD": "prod_password",
            "MONGODB_URL": "mongodb://prod-mongo:27017/llm_agent",
            "MONGODB_DATABASE": "llm_agent",
            "REDIS_HOST": "prod-redis",
            "REDIS_PORT": "6379",
        }
    
    return envs


def _extract_mongo_db(mongo_url: str) -> str:
    """Extract database name from MongoDB URL"""
    if not mongo_url:
        return "llm_agent"
    # mongodb://...@host:port/database?...
    match = re.search(r'/([^/?]+)(\?|$)', mongo_url)
    return match.group(1) if match else "llm_agent"


# Load environments from env directory
ENVIRONMENTS = load_environments()


class DatabaseTools:
    def __init__(self):
        self.current_env = "local"
        self._apply_env("local")

    def _apply_env(self, env_name: str):
        if env_name not in ENVIRONMENTS:
            return f"Unknown environment: {env_name}. Available: {list(ENVIRONMENTS.keys())}"
        
        env_config = ENVIRONMENTS[env_name]
        for key, value in env_config.items():
            os.environ[key] = value
        self.current_env = env_name
        return None

    def get_mysql_connection(self):
        if not MYSQL_AVAILABLE:
            return None, "MySQL driver not installed. Run: pip install mysql-connector-python"
        
        url = os.environ.get("MYSQL_URL")
        user = os.environ.get("MYSQL_USR")
        password = os.environ.get("MYSQL_PWD")
        
        if not all([url, user, password]):
            return None, "MySQL not configured. Run: switch_env('local'|'dev'|'uat'|'prod')"
        
        try:
            conn = mysql.connector.connect(
                host=self._extract_host(url),
                port=self._extract_port(url),
                database=self._extract_database(url),
                user=user,
                password=password
            )
            return conn, None
        except Exception as e:
            return None, str(e)

    def get_mongo_client(self):
        if not MONGO_AVAILABLE:
            return None, "MongoDB driver not installed. Run: pip install pymongo"
        
        url = os.environ.get("MONGODB_URL")
        if not url:
            return None, "MongoDB not configured. Run: switch_env('local'|'dev'|'uat'|'prod')"
        
        try:
            client = MongoClient(url, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            return client, None
        except Exception as e:
            return None, str(e)

    def _extract_host(self, jdbc_url: str) -> str:
        parts = jdbc_url.split("//")[1].split("/")[0]
        return parts.split(":")[0] if ":" in parts else parts

    def _extract_port(self, jdbc_url: str) -> int:
        parts = jdbc_url.split("//")[1].split("/")[0]
        return int(parts.split(":")[1].split("?")[0]) if ":" in parts else 3306

    def _extract_database(self, jdbc_url: str) -> str:
        return jdbc_url.split("?")[0].split("/")[-1]

    # === Environment Management ===

    def list_envs(self) -> dict:
        return {
            "success": True,
            "current": self.current_env,
            "available": list(ENVIRONMENTS.keys()),
            "message": "Use switch_env(env) to switch environment"
        }

    def switch_env(self, env_name: str) -> dict:
        if env_name not in ENVIRONMENTS:
            return {
                "success": False,
                "error": f"Unknown environment: {env_name}",
                "available": list(ENVIRONMENTS.keys())
            }
        
        error = self._apply_env(env_name)
        if error:
            return {"success": False, "error": error}
        
        return {
            "success": True,
            "message": f"Switched to {env_name}",
            "config": {
                "MYSQL_HOST": self._extract_host(ENVIRONMENTS[env_name]["MYSQL_URL"]),
                "MYSQL_DATABASE": self._extract_database(ENVIRONMENTS[env_name]["MYSQL_URL"]),
                "MONGODB_DATABASE": ENVIRONMENTS[env_name]["MONGODB_DATABASE"],
                "REDIS_HOST": ENVIRONMENTS[env_name].get("REDIS_HOST", ""),
                "REDIS_PORT": ENVIRONMENTS[env_name].get("REDIS_PORT", ""),
            }
        }

    def current_env_info(self) -> dict:
        return {
            "success": True,
            "current_env": self.current_env,
            "mysql_host": self._extract_host(os.environ.get("MYSQL_URL", "")),
            "mysql_database": self._extract_database(os.environ.get("MYSQL_URL", "")),
            "mongodb_database": os.environ.get("MONGODB_DATABASE", "")
        }

    # === MySQL Operations ===

    def query_mysql(self, sql: str, params: list = None) -> dict:
        conn, error = self.get_mysql_connection()
        if error:
            return {"success": False, "error": error}
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or [])
            
            if sql.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "DESC")):
                results = cursor.fetchall()
                return {
                    "success": True,
                    "columns": [desc[0] for desc in cursor.description] if cursor.description else [],
                    "rows": results,
                    "rowCount": len(results)
                }
            else:
                conn.commit()
                return {"success": True, "affectedRows": cursor.rowcount}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            cursor.close()
            conn.close()

    def list_tables(self) -> dict:
        return self.query_mysql("SHOW TABLES")

    def describe_table(self, table: str) -> dict:
        return self.query_mysql(f"DESCRIBE `{table}`")

    # === MongoDB Operations ===

    def query_mongodb(self, collection: str, filter: dict = None, projection: dict = None, limit: int = 100) -> dict:
        client, error = self.get_mongo_client()
        if error:
            return {"success": False, "error": error}
        
        try:
            db_name = os.environ.get("MONGODB_DATABASE", "llm_agent")
            coll = client[db_name][collection]
            cursor = coll.find(filter or {}, projection or {}).limit(limit)
            results = list(cursor)
            for doc in results:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
            return {"success": True, "documents": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            client.close()

    def list_mongo_collections(self) -> dict:
        client, error = self.get_mongo_client()
        if error:
            return {"success": False, "error": error}
        
        try:
            db_name = os.environ.get("MONGODB_DATABASE", "llm_agent")
            collections = client[db_name].list_collection_names()
            return {"success": True, "collections": collections, "count": len(collections)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            client.close()

    # === Request Handler ===

    def handle_request(self, tool_name: str, arguments: dict) -> Any:
        handlers = {
            # Environment
            "switch_env": lambda: self.switch_env(arguments.get("env", "")),
            "list_envs": self.list_envs,
            "current_env": self.current_env_info,
            # MySQL
            "query": lambda: self.query_mysql(arguments.get("sql", ""), arguments.get("params")),
            "list_tables": self.list_tables,
            "describe_table": lambda: self.describe_table(arguments.get("table", "")),
            # MongoDB
            "query_mongodb": lambda: self.query_mongodb(
                arguments.get("collection", ""),
                arguments.get("filter"),
                arguments.get("projection"),
                arguments.get("limit", 100)
            ),
            "list_collections": self.list_mongo_collections,
        }
        
        handler = handlers.get(tool_name)
        if handler:
            return handler()
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


db_tools = DatabaseTools()


def main():
    import sys
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            tool_name = request.get("tool", "")
            arguments = request.get("arguments", {})
            
            result = db_tools.handle_request(tool_name, arguments)
            print(json.dumps({"result": result}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
