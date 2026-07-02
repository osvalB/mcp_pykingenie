Local Testing
=============

Prerequisites
-------------

Install dependencies including test extras:

.. code-block:: bash

   cd mcp_pykingenie
   uv sync --extra test

Run all tests
-------------

.. code-block:: bash

   uv run pytest -vv

Run a specific test
-------------------

.. code-block:: bash

   uv run pytest tests/test_app.py::test_mcp_server -vv

Inspect registered MCP tools
----------------------------

To verify which tools are registered on the live ``mcp`` instance:

.. code-block:: bash

   uv run python - <<'PY'
   import asyncio
   from fastmcp import Client
   import mcp_pykingenie

   async def main():
       async with Client(mcp_pykingenie.mcp) as c:
           tools = await c.list_tools()
           print([t.name for t in tools])

   asyncio.run(main())
   PY

Test with MCP Inspector
-----------------------

To launch the MCP Inspector against a local checkout, run:

.. code-block:: bash

   npx @modelcontextprotocol/inspector uv --directory /Users/oburastero/Desktop/arise/mcp_pykingenie run mcp_pykingenie
