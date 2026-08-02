#!/usr/bin/env bash
set -euo pipefail

export DATAHUB_GMS_URL="${DATAHUB_GMS_URL:-http://localhost:8080}"
export FASTMCP_PORT="${FASTMCP_PORT:-8001}"
export TOOLS_IS_MUTATION_ENABLED="${TOOLS_IS_MUTATION_ENABLED:-true}"
export SAVE_DOCUMENT_TOOL_ENABLED="${SAVE_DOCUMENT_TOOL_ENABLED:-true}"

MCP_REPO="${DATAHUB_MCP_REPO:-../mcp-server-datahub}"
exec uv --directory "$MCP_REPO" run mcp-server-datahub --transport http
