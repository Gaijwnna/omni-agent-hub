import asyncio,json
from pathlib import Path
from sqlalchemy.schema import CreateTable,CreateIndex
from sqlalchemy.dialects import postgresql
from app.db import Base
from app.main import app
from app.mcp_server import mcp
root=Path(__file__).resolve().parents[1]
(root/'docs/openapi.json').write_text(json.dumps(app.openapi(),indent=2)+'\n')
async def export():
    tools=await mcp.list_tools()
    (root/'docs/mcp-tools.json').write_text(json.dumps([t.model_dump(mode='json',exclude_none=True) for t in tools],indent=2)+'\n')
asyncio.run(export())
sql=['-- Initial PostgreSQL schema. Generated from app/db.py; do not run against an already initialised database.','BEGIN;']
for table in Base.metadata.sorted_tables:
    sql.append(str(CreateTable(table).compile(dialect=postgresql.dialect()))+';')
    sql.extend(str(CreateIndex(i).compile(dialect=postgresql.dialect()))+';' for i in table.indexes)
sql.append('COMMIT;')
(root/'migrations/001_initial.sql').write_text('\n\n'.join(sql)+'\n')
print('Exported OpenAPI, MCP tool schemas and PostgreSQL DDL.')
