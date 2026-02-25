"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.McpToolClient = void 0;
const errors_1 = require("../core/errors");
const logger_1 = require("../core/logger");
class McpToolClient {
    // Register tool handlers once at startup; skills stay transport-agnostic.
    handlers = new Map();
    registerTool(name, handler) {
        this.handlers.set(name, handler);
    }
    async callTool(toolName, params = {}) {
        const handler = this.handlers.get(toolName);
        if (!handler) {
            throw new errors_1.ToolExecutionError(toolName, "No handler registered");
        }
        const startedAt = Date.now();
        try {
            // Unified logging/timing at tool boundary for observability.
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
                event: "tool_call_error",
                tool: toolName,
                durationMs: Date.now() - startedAt,
                error: error instanceof Error ? error.message : String(error),
            });
            throw new errors_1.ToolExecutionError(toolName, error instanceof Error ? error.message : "Unknown tool error", error);
        }
    }
}
exports.McpToolClient = McpToolClient;
