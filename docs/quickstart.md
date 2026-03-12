# Quickstart

`mcp_pykingenie` is an MCP server that provides tools for the analysis of binding kinetics data from **Octet** (Biolayer Interferometry) and **Gator** instruments.

## Requirements

- Python 3.11 or newer
- [`uv`](https://github.com/astral-sh/uv) (recommended)

## Installation

### From PyPI

```bash
pip install mcp_pykingenie
```

### From source (development)

```bash
git clone https://github.com/osvalB/mcp_pykingenie.git
cd mcp_pykingenie
uv sync
```

## Running the server

### stdio (default, for Claude Desktop / VS Code / Cursor)

```bash
mcp_pykingenie
```

### HTTP transport

```bash
mcp_pykingenie -t http -p 8000
```

## MCP client configuration

### Claude Desktop / Cursor / VS Code (`mcp.json`)

If installed from PyPI:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uvx",
      "args": ["mcp_pykingenie"]
    }
  }
}
```

From a local repo:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp_pykingenie", "mcp_pykingenie"]
    }
  }
}
```

## Loading example data

Once connected through your MCP client, ask your AI assistant:

> "Load the Octet example experiment"

This calls `load_octet_example` and loads the bundled BLI example dataset — no files needed.

## Typical chat flow

```
1. load the octet folder in path/to/ocet/data          
2. align the association phase   
3. align the dissociation phase  
4. subtract the sensor H1
5. plot all the steps
6. show me the sample information
7. create a dataset for fitting using the sample wt - imd
8. fit the data with a one-to-one model
9. plot the fitted curves
```