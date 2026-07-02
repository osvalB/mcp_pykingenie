"""Stdio helpers for running the MCP server."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from io import TextIOWrapper
from typing import Any

import anyio
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.stdio import stdio_server


async def _non_empty_lines(stdin: AsyncIterator[str]) -> AsyncIterator[str]:
    """
    Yield only non-empty JSON-RPC lines from an async stdin iterator.

    Parameters
    ----------
    stdin : AsyncIterator[str]
        Async iterator providing raw stdin lines.

    Yields
    ------
    str
        Non-empty stdin lines.
    """
    async for line in stdin:
        if line.strip():
            yield line


@asynccontextmanager
async def stdio_server_ignoring_empty_lines(
    stdin: AsyncIterator[str] | None = None,
    stdout: Any | None = None,
):
    """
    Create an MCP stdio transport that ignores blank inbound lines.

    Parameters
    ----------
    stdin : AsyncIterator[str] | None
        Optional stdin stream. If None, the process stdin is used.
    stdout : Any | None
        Optional stdout stream. If None, the process stdout is used.
    """
    if stdin is None:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))

    async with stdio_server(stdin=_non_empty_lines(stdin), stdout=stdout) as streams:
        yield streams


async def run_stdio_ignoring_empty_lines(
    server: Any,
    show_banner: bool = True,
    log_level: str | None = None,
    stateless: bool = False,
    stdio_context: Any | None = None,
) -> None:
    """
    Run a FastMCP server over stdio while ignoring blank inbound lines.

    Parameters
    ----------
    server : Any
        FastMCP server instance to run.
    show_banner : bool
        Whether to display the FastMCP server banner.
    log_level : str | None
        Temporary log level to use while the server runs.
    stateless : bool
        Whether to run without session initialization state.
    stdio_context : Any | None
        Optional async context manager factory that yields read/write streams.
    """
    from fastmcp.server.context import reset_transport, set_transport
    from fastmcp.utilities.cli import log_server_banner
    from fastmcp.utilities.logging import get_logger, temporary_log_level

    if stdio_context is None:
        stdio_context = stdio_server_ignoring_empty_lines

    if show_banner:
        log_server_banner(server=server)

    logger = get_logger(__name__)
    token = set_transport("stdio")
    try:
        with temporary_log_level(log_level):
            async with server._lifespan_manager():
                async with stdio_context() as (
                    read_stream,
                    write_stream,
                ):
                    mode = " (stateless)" if stateless else ""
                    logger.info(
                        f"Starting MCP server {server.name!r} with transport 'stdio'{mode}"
                    )

                    await server._mcp_server.run(
                        read_stream,
                        write_stream,
                        server._mcp_server.create_initialization_options(
                            notification_options=NotificationOptions(
                                tools_changed=True
                            ),
                        ),
                        stateless=stateless,
                    )
    finally:
        reset_transport(token)


def run_stdio(server: Any, **kwargs: Any) -> None:
    """
    Synchronously run a FastMCP server with the hardened stdio transport.

    Parameters
    ----------
    server : Any
        FastMCP server instance to run.
    **kwargs : Any
        Keyword arguments forwarded to ``run_stdio_ignoring_empty_lines``.
    """
    anyio.run(partial(run_stdio_ignoring_empty_lines, server, **kwargs))
