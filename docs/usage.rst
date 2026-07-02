Usage
=====

``mcp_pykingenie`` is intended only for surface-based binding data, such as
Octet and Gator BLI experiments.

Video Demonstrations
--------------------

Two demonstration videos are available:

* `Example with Visual Studio Code <https://drive.google.com/file/d/1PtUdFNThLG6F2T55cUc4p69JeCwhSrNs/view?usp=drive_link>`__
* `Example with Claude <https://drive.google.com/file/d/1iXqUMakI-m5Vrpya-cI7e0YT6krsfvbn/view?usp=drive_link>`__

Common MCP Configuration
------------------------

MCP clients that support an ``mcp.json`` configuration can start
``mcp_pykingenie`` with ``uvx``:

.. code-block:: json

   {
     "mcpServers": {
       "mcp_pykingenie": {
         "command": "uvx",
         "args": ["mcp_pykingenie"],
         "env": {
           "RESULTS_DIR": "/absolute/path/to/results-folder"
         }
       }
     }
   }

``RESULTS_DIR`` is the folder where plots and generated files are stored. The
server creates a date-stamped subfolder inside it for each run.

Claude Desktop
--------------

In Claude Desktop, open **Settings**, go to **Developer**, and click
**Edit Config**. Add ``mcp_pykingenie`` to
``claude_desktop_config.json``:

.. code-block:: json

   {
     "mcpServers": {
       "mcp_pykingenie": {
         "command": "uvx",
         "args": ["mcp_pykingenie"],
         "env": {
           "RESULTS_DIR": "/Users/your-name/Documents/user_data_mcp_pykingenie"
         }
       }
     }
   }

Claude Desktop stores this file at:

* macOS: ``~/Library/Application Support/Claude/claude_desktop_config.json``
* Windows: ``%APPDATA%\Claude\claude_desktop_config.json``

Save the file, then fully quit and reopen Claude Desktop.

For local development, point the client at the repository checkout:

.. code-block:: json

   {
     "mcpServers": {
       "mcp_pykingenie": {
         "command": "uvx",
         "args": [
           "--refresh",
           "--from",
           "/absolute/path/to/mcp_pykingenie",
           "mcp_pykingenie"
         ]
       }
     }
   }

If you want to reuse the checkout's existing environment, run it through
``uv``:

.. code-block:: json

   {
     "mcpServers": {
       "mcp_pykingenie": {
         "command": "uv",
         "args": ["run", "--directory", "/absolute/path/to/mcp_pykingenie", "mcp_pykingenie"]
       }
     }
   }

ChatMCP Desktop
---------------

1. Download the `ChatMCP desktop app <https://github.com/daodao97/chatmcp>`__.
2. Open the app and configure a model provider, such as OpenAI or Ollama.
3. Verify that the chat is working by sending a message to the model.
4. Open the settings and add a new MCP server.
5. Set the server type to ``STDIO``.
6. For a local checkout, set the command to ``uv`` and the arguments to:

.. code-block:: text

   run --directory /absolute/path/to/mcp_pykingenie mcp_pykingenie

VS Code with GitHub Copilot
---------------------------

1. Download and install `Visual Studio Code <https://code.visualstudio.com/>`__.
2. `Set up GitHub Copilot in VS Code <https://code.visualstudio.com/docs/copilot/setup>`__.
3. Edit the VS Code MCP configuration, commonly named ``mcp.json``:

.. code-block:: json

   {
     "servers": {
       "mcp_pykingenie": {
         "command": "uvx",
         "args": ["mcp_pykingenie"],
         "env": {
           "RESULTS_DIR": "/absolute/path/to/results-folder"
         }
       }
     }
   }

4. Start the MCP server from VS Code and use Copilot's agent mode to interact
   with the tools.

Developer Debugging
-------------------

To run the MCP server directly from a local checkout:

.. code-block:: bash

   uv run mcp_pykingenie

To use the HTTP transport:

.. code-block:: bash

   uv run mcp_pykingenie -t http -p 8000

To use the MCP Inspector for interactive debugging against a local checkout:

.. code-block:: bash

   npx @modelcontextprotocol/inspector uv --directory /Users/oburastero/Desktop/arise/mcp_pykingenie run mcp_pykingenie
