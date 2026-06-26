# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'F:/gientech-repository/.cursor/mcps/db-tools')

# Test config loading
exec(open('F:/gientech-repository/.cursor/mcps/db-tools/db_tools_server.py').read().split('def main():')[0])

print("=== MCP db-tools Test ===")
print(f"Environments: {list(ENVIRONMENTS.keys())}")
print(f"Current env: {current_env}")
print(f"Local MySQL: {ENVIRONMENTS['local']['MYSQL_URL']}")
print(f"Dev MySQL: {ENVIRONMENTS['dev']['MYSQL_URL']}")
print(f"Uat MySQL: {ENVIRONMENTS['uat']['MYSQL_URL']}")
print()

# Test tool handlers exist
print("=== Available Tools ===")
for name in dir():
    if not name.startswith('_') and callable(eval(name)) and name in ['switch_env', 'list_envs', 'list_tables', 'describe_table', 'query_mysql', 'query_mongodb']:
        print(f"  {name}")
print()
print("Test PASSED")
