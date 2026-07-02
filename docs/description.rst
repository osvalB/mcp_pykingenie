Overview
========

``mcp_pykingenie`` exposes ``pykingenie`` binding kinetics workflows through
the Model Context Protocol. It provides tools for importing Octet and Gator
experiments, aligning association and dissociation phases, subtracting
reference sensors, preparing fitting datasets, running kinetic fits, plotting
traces, and inspecting fitted parameters.

Basic Workflow
--------------

The typical workflow for binding kinetics analysis is:

1. Import an Octet or Gator experiment.
2. Align the association phase.
3. Align the dissociation phase.
4. Subtract a reference sensor.
5. Inspect the sample information table.
6. Select traces and generate fitting datasets.
7. Run a kinetic fitting model.
8. Plot fitted curves and retrieve fitting results.

MCP Tools
---------

The server keeps a ``pykingenie.KineticsAnalyzer`` instance in memory for the
current MCP session. Generated plots are written to the active data directory,
which defaults to ``~/Desktop/mcp_pykingenie/user_data/<YYYY-MM-DD>/``. Use
the ``print_data_dir`` tool to display the exact folder used by the running
server.

Example Chat Flow
-----------------

Once connected through your MCP client, ask your AI assistant to run a flow
like:

.. code-block:: text

   1. load the Octet example experiment
   2. align the association phase
   3. align the dissociation phase
   4. subtract the sensor H1
   5. plot all the steps
   6. show me the sample information
   7. create a fitting dataset using sample wt - imd
   8. fit the data with a one-to-one model
   9. plot the fitted curves

Local Development
-----------------

For local MCP clients that support the ``mcp.json`` convention, point the
server command at the repository:

.. code-block:: json

   {
     "mcpServers": {
       "mcp_pykingenie": {
         "command": "uv",
         "args": ["run", "--directory", "/absolute/path/to/mcp_pykingenie", "mcp_pykingenie"]
       }
     }
   }

Citation
--------

If you use ``mcp_pykingenie``, please cite it as:

Burastero, O. (2026). ``mcp_pykingenie`` (Version 0.0.1) [Computer software].
GitHub. https://github.com/osvalB/mcp_pykingenie

.. code-block:: bibtex

   @software{burastero_2026_mcp_pykingenie,
     author = {Burastero, Osvaldo},
     title = {mcp_pykingenie},
     version = {0.0.1},
     year = {2026},
     url = {https://github.com/osvalB/mcp_pykingenie}
   }
