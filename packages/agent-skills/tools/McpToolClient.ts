import { ToolExecutionError } from "../core/errors";
import { logger } from "../core/logger";

export type ToolParams = Record<string, unknown>;
export type ToolHandler = (params: ToolParams) => Promise<unknown>;

export class McpToolClient {
  // Register tool handlers once at startup; skills stay transport-agnostic.
  private readonly handlers = new Map<string, ToolHandler>();

  registerTool(name: string, handler: ToolHandler): void {
    this.handlers.set(name, handler);
  }

  async callTool<T = unknown>(toolName: string, params: ToolParams = {}): Promise<T> {
    const handler = this.handlers.get(toolName);
    if (!handler) {
      throw new ToolExecutionError(toolName, "No handler registered");
    }

    const startedAt = Date.now();
    try {
      // Unified logging/timing at tool boundary for observability.
      const result = await handler(params);
      logger.info({
        event: "tool_call",
        tool: toolName,
        durationMs: Date.now() - startedAt,
      });
      return result as T;
    } catch (error) {
      logger.error({
        event: "tool_call_error",
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
