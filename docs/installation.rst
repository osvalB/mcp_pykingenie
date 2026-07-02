Installation
============

Requirements
------------

``mcp_pykingenie`` requires Python 3.11 or later. The MCP server depends on
``pykingenie`` and FastMCP, plus the scientific Python stack used for binding
kinetics analysis.

Run with uvx
------------

Run the server directly with ``uvx``:

.. code-block:: bash

   uvx mcp_pykingenie

By default, generated plots and imported relative-path data are stored in a
date-stamped folder under ``~/user_data_mcp_pykingenie/<YYYY-MM-DD>/``. To
choose a different results folder, set ``RESULTS_DIR`` before starting the
server. Use the ``print_data_dir`` MCP tool to inspect the active output
folder.

.. code-block:: bash

   RESULTS_DIR=~/Documents/user_data_mcp_pykingenie uvx mcp_pykingenie

Install from PyPI
-----------------

Install the package with pip:

.. code-block:: bash

   pip install --user mcp_pykingenie

Then run the server with:

.. code-block:: bash

   mcp_pykingenie

If your shell cannot find the command, make sure your user-level Python scripts
directory is on ``PATH``.

You can use the same output-folder setting when running the installed command:

.. code-block:: bash

   RESULTS_DIR=~/Documents/user_data_mcp_pykingenie mcp_pykingenie

Install from Source
-------------------

Clone the repository and install the development environment with ``uv``:

.. code-block:: bash

   git clone https://github.com/osvalB/mcp_pykingenie.git
   cd mcp_pykingenie
   uv sync --extra dev --extra doc --extra test

Run Tests
---------

Verify the development installation by running the test suite:

.. code-block:: bash

   uv run pytest

Build Documentation
-------------------

Create the local documentation build with:

.. code-block:: bash

   uv run --extra doc make -C docs html

The generated HTML documentation is written to ``docs/_build/html/``.
