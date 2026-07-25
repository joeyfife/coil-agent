# Connecting the Coil MCP server, per client

**Claude Code** (one command):

```bash
claude mcp add --transport http coil https://coil.trade/mcp
```

**Claude Code** (project `.mcp.json`):

```json
{
  "mcpServers": {
    "coil": { "type": "http", "url": "https://coil.trade/mcp" }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`) — Desktop's config file launches local
processes, so a remote HTTP server goes through the `mcp-remote` bridge:

```json
{
  "mcpServers": {
    "coil": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://coil.trade/mcp"]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "coil": { "url": "https://coil.trade/mcp" }
  }
}
```

Free tier needs no key. A Coil Scanner license ($12/mo) upgrades every tool to the live
intraday board — add `"headers": {"X-License-Key": "…"}` where your client supports it,
or use the licensed REST tier instead (see the README).
