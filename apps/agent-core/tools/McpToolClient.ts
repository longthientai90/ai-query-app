import { ToolExecutionError } from "../utils/errors";
import { logger } from "../utils/logger";

export interface ToolClient {
  callTool<T = unknown>(toolName: string, params: Record<string, unknown>): Promise<T>;
}

export type ToolHandler = (params: Record<string, unknown>) => Promise<unknown>;

export class McpToolClient implements ToolClient {
  // In-memory tool registry so skills are decoupled from concrete MCP transport details.
  private readonly handlers = new Map<string, ToolHandler>();

  registerHandler(toolName: string, handler: ToolHandler): void {
    this.handlers.set(toolName, handler);
  }

  async callTool<T = unknown>(toolName: string, params: Record<string, unknown>): Promise<T> {
    const handler = this.handlers.get(toolName);
    if (!handler) {
      throw new ToolExecutionError(toolName, "No handler registered");
    }

    // Standardize timing + logs for every tool call boundary.
    const startedAt = Date.now();
    try {
      const result = await handler(params);
      logger.info({
        event: "tool_call",
        tool: toolName,
        durationMs: Date.now() - startedAt,
      });
      return result as T;
    } catch (error) {
      logger.error({
        event: "tool_call_failed",
        tool: toolName,
        durationMs: Date.now() - startedAt,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new ToolExecutionError(
        toolName,
        error instanceof Error ? error.message : "Unknown tool error",
        error,
      );
    }
  }
}
