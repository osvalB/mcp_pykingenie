# mcp_pykingenie

<!--
[![BioContextAI - Registry](https://img.shields.io/badge/Registry-package?style=flat&label=BioContextAI&labelColor=%23fff&color=%233555a1&link=https%3A%2F%2Fbiocontext.ai%2Fregistry)](https://biocontext.ai/registry)
[![Tests][badge-tests]][tests]
[![Documentation][badge-docs]][documentation]
-->
[badge-tests]: https://img.shields.io/github/actions/workflow/status/osvalB/mcp_pykingenie/test.yaml?branch=main
[badge-docs]: https://img.shields.io/readthedocs/mcp_pykingenie

This repository contains a local MCP server for the analysis of binding kinetics data from Octet and Gator experiments.
It is based on the Python package [pykingenie](https://github.com/osvalB/pykingenie).

## Demo videos

- [Example with Visual Studio Code](https://drive.google.com/file/d/1PtUdFNThLG6F2T55cUc4p69JeCwhSrNs/view?usp=drive_link)
- [Example with Claude](https://drive.google.com/file/d/1iXqUMakI-m5Vrpya-cI7e0YT6krsfvbn/view?usp=drive_link)

## Installation

We recommend running mcp_pykingenie with [uv][].

### Run from the command line

```bash
uvx mcp_pykingenie
```

By default, generated plots and relative-path input data are stored in
`~/user_data_mcp_pykingenie/<YYYY-MM-DD>/`. To choose a different results
folder, set `RESULTS_DIR` before starting the server. Use the `print_data_dir`
MCP tool to inspect the active output folder for a running server.

```bash
RESULTS_DIR=~/Documents/user_data_mcp_pykingenie uvx mcp_pykingenie
```

### Configure an MCP client

Add the server to any MCP-compatible client that supports the `mcpServers`
configuration format:

```json
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
```

After updating the configuration, restart the MCP client so it can launch the
server.

If you want to run directly from the Git repository:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uvx",
      "args": ["git+https://github.com/osvalB/mcp_pykingenie.git@main"]
    }
  }
}
```

#### Claude Desktop

In Claude Desktop, open **Settings**, go to **Developer**, and click
**Edit Config**. Add `mcp_pykingenie` to `claude_desktop_config.json`:

```json
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
```

Claude Desktop stores this file at:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Save the file, then fully quit and reopen Claude Desktop.

### Local development

To run the server from a local checkout, use an absolute path to the repository:

```json
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
```

If you want to reuse the checkout's existing environment, run it through `uv`:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mcp_pykingenie", "mcp_pykingenie"]
    }
  }
}
```

For HTTP transport during development:

```bash
uv run mcp_pykingenie -t http -p 8000
```

### Install with pip

```bash
pip install --user mcp_pykingenie
```

Then run the server with:

```bash
mcp_pykingenie
```

If your shell cannot find the command, make sure your user-level Python scripts
directory is on `PATH`.

### Install from source

```bash
git clone https://github.com/osvalB/mcp_pykingenie.git
cd mcp_pykingenie
uv sync --extra dev --extra doc --extra test
```

Run tests with:

```bash
uv run pytest
```

Build the documentation with:

```bash
uv run --extra doc make -C docs html
```

## Example workflow

Once connected through your MCP client, ask your AI assistant to run a flow like:

```text
1. load the Octet example experiment
2. align the association phase
3. align the dissociation phase
4. subtract the sensor H1
5. plot all the steps
6. show me the sample information
7. create a fitting dataset using sample wt - imd
8. fit the data with a one-to-one model
9. plot the fitted curves
```

## Contact

If you found a bug, please use the [issue tracker][].

## Citation

If you use `mcp_pykingenie`, please cite it as:

Burastero, O. (2026). `mcp_pykingenie` (Version 1.0) [Computer software].
GitHub. https://github.com/osvalB/mcp_pykingenie

```bibtex
@software{burastero_2026_mcp_pykingenie,
  author = {Burastero, Osvaldo},
  title = {mcp_pykingenie},
  version = {1.0},
  year = {2026},
  url = {https://github.com/osvalB/mcp_pykingenie}
}
```

[uv]: https://github.com/astral-sh/uv
[issue tracker]: https://github.com/osvalB/mcp_pykingenie/issues
[tests]: https://github.com/osvalB/mcp_pykingenie/actions/workflows/test.yaml
[documentation]: https://mcp_pykingenie.readthedocs.io
[api documentation]: https://mcp_pykingenie.readthedocs.io/en/latest/modules.html
[pypi]: https://pypi.org/project/mcp_pykingenie
