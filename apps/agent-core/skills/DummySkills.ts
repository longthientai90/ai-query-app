import { AgentContext } from "../context/AgentContext";
import { BaseSkill, SkillResult } from "./BaseSkill";
import { ToolClient } from "../tools/McpToolClient";

export class DataFetchSkill extends BaseSkill {
  readonly id = "data_fetch";
  readonly description = "Fetches top transaction data from tool layer";

  canHandle(context: AgentContext): boolean {
    // Run once at the beginning: only when result set does not exist yet.
    return !context.variables["lastQueryResult"];
  }

  async execute(context: AgentContext, toolClient: ToolClient): Promise<SkillResult> {
    const rows = await toolClient.callTool<Array<Record<string, unknown>>>("postgres_query", {
      sql: "SELECT id, amount FROM tx ORDER BY amount DESC LIMIT 5",
    });

    context.mergeVariables({
      lastQueryResult: rows,
    });
    context.appendMessage("tool", `Fetched ${rows.length} rows from postgres_query`);
    return { done: false };
  }
}

export class SynthesisSkill extends BaseSkill {
  readonly id = "synthesis";
  readonly description = "Composes final user-facing answer from fetched data";

  canHandle(context: AgentContext): boolean {
    // Run after fetch: synthesize final answer from shared variable.
    return Boolean(context.variables["lastQueryResult"] && !context.variables["finalResponse"]);
  }

  async execute(context: AgentContext): Promise<SkillResult> {
    const rows = (context.variables["lastQueryResult"] as Array<Record<string, unknown>>) ?? [];
    const response = rows
      .map((row, index) => `${index + 1}. tx #${row.id} - amount ${row.amount}`)
      .join("\n");

    context.mergeVariables({ finalResponse: response || "No data found." });
    context.appendMessage("agent", response || "No data found.");
    return { done: true };
  }
}
