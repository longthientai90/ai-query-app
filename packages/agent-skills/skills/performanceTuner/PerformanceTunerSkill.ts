import { AgentContext } from "../../context/AgentContext";
import { performanceTunerPrompt } from "../../prompts/performanceTunerPrompt";
import { McpToolClient } from "../../tools/McpToolClient";
import { BaseSkill, SkillOutput } from "../BaseSkill";

function optimizeSql(sql: string): string {
  if (!sql.toLowerCase().includes("limit")) {
    return `${sql} LIMIT 100`;
  }
  return sql.replace("SELECT *", "SELECT id, amount");
}

export class PerformanceTunerSkill extends BaseSkill {
  public readonly name = "performance_tuner";
  public readonly description = "Analyzes explain plan and tunes SQL text before execution.";

  public canHandle(context: AgentContext): boolean {
    // Tuning requires an existing SQL draft from query expert.
    return Boolean(context.getVariable("targetQuery"));
  }

  public async execute(context: AgentContext, toolClient: McpToolClient): Promise<SkillOutput> {
    const targetQuery = context.getVariable<string>("targetQuery");
    if (!targetQuery) {
      return {
        status: "ERROR",
        message: "No targetQuery available for tuning.",
      };
    }

    const explain = await toolClient.callTool<string>("postgres_explain", { sql: targetQuery });
    const prompt = performanceTunerPrompt(targetQuery, explain);
    const optimized = optimizeSql(targetQuery);

    // Persist plan + tuned SQL, then chain back for execution.
    context.setVariable("queryExplainPlan", explain);
    context.setVariable("targetQuery", optimized);
    context.setVariable("performanceReasoning", prompt);
    context.nextSkillHint = "query_expert";

    return {
      status: "CONTINUE",
      message: "Query tuned and routed back to query expert.",
      suggestedNextSkill: "query_expert",
    };
  }
}
