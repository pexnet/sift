"""stdio MCP server entry point.

Usage: Hermes config:
  mcp_servers:
    sift:
      command: "sift-mcp"
      env:
        SIFT_MCP_TOKEN: "sft_..."
        SIFT_DATABASE_URL: "postgresql+asyncpg://..."

Auth: SIFT_MCP_TOKEN env var (raw API token, validated against DB).
"""

import asyncio
import os
import sys

from sqlalchemy import select

from sift.db.models import User
from sift.db.session import SessionLocal
from sift.mcp.server import mcp_server, set_mcp_user_id
from sift.services.token_service import token_service


async def _resolve_user_from_env_token() -> User:
    raw_token = os.environ.get("SIFT_MCP_TOKEN")
    if not raw_token:
        print("SIFT_MCP_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    async with SessionLocal() as session:
        token = await token_service.validate_token(session, raw_token)
        if token is None:
            print("Invalid or expired SIFT_MCP_TOKEN", file=sys.stderr)
            sys.exit(1)

        stmt = select(User).where(User.id == token.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            print("Token user not found", file=sys.stderr)
            sys.exit(1)
        return user


async def main() -> None:
    from mcp.server.stdio import stdio_server

    user = await _resolve_user_from_env_token()
    set_mcp_user_id(user.id)

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()