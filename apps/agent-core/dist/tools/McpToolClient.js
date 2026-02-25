"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.McpToolClient = void 0;
const errors_1 = require("../utils/errors");
const logger_1 = require("../utils/logger");
class McpToolClient {
    // In-memory tool registry so skills are decoupled from concrete MCP transport details.
    handlers = new Map();
    registerHandler(toolName, handler) {
        this.handlers.set(toolName, handler);
    }
    async callTool(toolName, params) {
        const handler = this.handlers.get(toolName);
        if (!handler) {
            throw new errors_1.ToolExecutionError(toolName, "No handler registered");
        }
        // Standardize timing + logs for every tool call boundary.
        const startedAt = Date.now();
        try {
            const result = await handler(params);
            logger_1.logger.info({
                event: "tool_call",
                tool: toolName,
                durationMs: Date.now() - startedAt,
            });
            return result;
        }
        catch (error) {
            logger_1.logger.error({
                event: "tool_call_failed",
                tool: toolName,
                durationMs: Date.now() - startedAt,
                error: error instanceof Error ? error.message : String(error),
            });
            throw new errors_1.ToolExecutionError(toolName, error instanceof Error ? error.message : "Unknown tool error", error);
        }
    }
}
exports.McpToolClient = McpToolClient;
