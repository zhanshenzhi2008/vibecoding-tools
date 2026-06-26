# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'F:/gientech-repository/.cursor/mcps/db-tools')
import db_tools_server

db_tools = db_tools_server.DatabaseTools()
db_tools.switch_env('dev')

req = "019ed462df337596b9d680495f20d6d3"

# 查 chat_message 表结构
print("=== chat_message 表结构 ===")
r = db_tools.describe_table('chat_message')
if r['success']:
    for row in r['rows']:
        print(f"  {row['Field']} ({row['Type']})")

# 查 chat_message
print("\n=== chat_message 详情 ===")
r2 = db_tools.query_mysql("SELECT * FROM chat_message WHERE request_id = '{}' ORDER BY id LIMIT 10".format(req))
if r2['success']:
    print(f"找到 {r2['rowCount']} 条:")
    for row in r2['rows']:
        for k, v in row.items():
            if v is not None:
                print(f"  {k}: {str(v)[:500]}")
        print()
else:
    print(f"失败 - {r2['error']}")

# 查 chat_conversation
print("\n=== chat_conversation 详情 ===")
r3 = db_tools.query_mysql("SELECT * FROM chat_conversation WHERE id IN (SELECT conversation_id FROM chat_message WHERE request_id = '{}')".format(req))
if r3['success']:
    print(f"找到 {r3['rowCount']} 条:")
    for row in r3['rows']:
        for k, v in row.items():
            if v is not None:
                print(f"  {k}: {str(v)[:500]}")
        print()
else:
    print(f"失败 - {r3['error']}")
