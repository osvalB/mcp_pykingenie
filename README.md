# mcp_pykingenie

[![BioContextAI - Registry](https://img.shields.io/badge/Registry-package?style=flat&label=BioContextAI&labelColor=%23fff&color=%233555a1&link=https%3A%2F%2Fbiocontext.ai%2Fregistry)](https://biocontext.ai/registry)
[![Tests][badge-tests]][tests]
[![Documentation][badge-docs]][documentation]

[badge-tests]: https://img.shields.io/github/actions/workflow/status/osvalB/mcp_pykingenie/test.yaml?branch=main
[badge-docs]: https://img.shields.io/readthedocs/mcp_pykingenie

The mcp_pykingenie is a [MCP-server](https://github.com/modelcontextprotocol) that provides tools for the analysis of binding kinetics data.
It is based on the [pykingenie](https://github.com/osvalB/pykingenie) Python package .


## Demo Videos

- [Video 1 – Example with Visual Studio Code](https://drive.google.com/file/d/1PtUdFNThLG6F2T55cUc4p69JeCwhSrNs/view?usp=drive_link)  
- [Video 2 – Example with Claude](https://drive.google.com/file/d/1iXqUMakI-m5Vrpya-cI7e0YT6krsfvbn/view?usp=drive_link)

## Getting started

Please refer to the [documentation][],
in particular, the [API documentation][].

<!--
You can also find the project on [BioContextAI](https://biocontext.ai), the community-hub for biomedical MCP servers: [mcp_pykingenie on BioContextAI](https://biocontext.ai/registry/osvalB/mcp_pykingenie).
-->

## Installation

You need to have Python 3.10 or newer installed on your system.
If you don't have Python installed, we recommend installing [uv][].

There are several alternative options to install mcp_pykingenie:

### 1. Use `uvx` to run it immediately
After publication to PyPI:
```bash
uvx mcp_pykingenie
```

Or from a Git repository:

```bash
uvx git+https://github.com/osvalB/mcp_pykingenie.git@main
```

### 2. Include it in one of various clients that supports the `mcp.json` standard

If your MCP server is published to PyPI, use the following configuration:

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
In case the MCP server is not yet published to PyPI, use this configuration:

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

For purely local development (e.g., in Cursor or VS Code), use the following configuration:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--from",
        "path/to/repository",
        "mcp_pykingenie"
      ]
    }
  }
}
```

If you want to reuse and existing environment for local development, use the following configuration:

```json
{
  "mcpServers": {
    "mcp_pykingenie": {
      "command": "uv",
      "args": ["run", "--directory", "path/to/repository", "mcp_pykingenie"]
    }
  }
}
```

### 3. Install it through `pip`:

```bash
pip install --user mcp_pykingenie
```

### 4. Install the latest development version:

```bash
pip install git+https://github.com/osvalB/mcp_pykingenie.git@main
```

## Contact

If you found a bug, please use the [issue tracker][].

## Citation

> t.b.a

[uv]: https://github.com/astral-sh/uv
[issue tracker]: https://github.com/osvalB/mcp_pykingenie/issues
[tests]: https://github.com/osvalB/mcp_pykingenie/actions/workflows/test.yaml
[documentation]: https://mcp_pykingenie.readthedocs.io
[changelog]: https://mcp_pykingenie.readthedocs.io/en/latest/changelog.html
[api documentation]: https://mcp_pykingenie.readthedocs.io/en/latest/api.html
[pypi]: https://pypi.org/project/mcp_pykingenie
