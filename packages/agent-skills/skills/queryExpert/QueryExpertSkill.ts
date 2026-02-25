import { AgentContext } from "../../context/AgentContext";
import { queryExpertPrompt } from "../../prompts/queryExpertPrompt";
import { McpToolClient } from "../../tools/McpToolClient";
import { BaseSkill, SkillOutput } from "../BaseSkill";

function buildSql(question: string): string {
  const normalized = question.toLowerCase();
  if (normalized.includes("top") || normalized.includes("largest")) {
    return "SELECT id, amount FROM transactions ORDER BY amount DESC LIMIT 20";
  }
  return "SELECT * FROM transactions LIMIT 100";
}

function isComplexQuery(sql: string): boolean {
  const normalized = sql.toLowerCase();
  return normalized.includes(" join ") || normalized.includes(" group by ");
}

export class QueryExpertSkill extends BaseSkill {
  public readonly name = "query_expert";
  public readonly description = "Builds secure SQL from context and executes read-only DB queries.";

  public canHandle(context: AgentContext): boolean {
    // Query generation depends on schema awareness.
    return Boolean(context.getVariable("dbSchemaInfo"));
  }

  public async execute(context: AgentContext, toolClient: McpToolClient): Promise<SkillOutput> {
    const question = context.getLatestUserMessage()?.content ?? "";
    const schemaInfo = context.getVariable<string>("dbSchemaInfo") ?? "";
    const prompt = queryExpertPrompt({ userQuestion: question, schemaInfo });

    // Reuse tuned query from tuner when available; otherwise build initial SQL.
    const sql = context.getVariable<string>("targetQuery") ?? buildSql(question);
    context.setVariable("targetQuery", sql);

    const wasTuned = Boolean(context.getVariable("queryExplainPlan"));
    if (!wasTuned && isComplexQuery(sql)) {
      context.nextSkillHint = "performance_tuner";
      return {
        status: "CONTINUE",
        message: "Query generated and flagged for performance tuning.",
        suggestedNextSkill: "performance_tuner",
      };
    }

    const rows = await toolClient.callTool<unknown>("postgres_query", {
      sql,
      reasoning: prompt,
    });

    // Query execution is terminal in this baseline flow.
    context.setVariable("queryResults", rows);
    context.nextSkillHint = undefined;

    return {
      status: "TERMINATE",
      message: "Query executed successfully.",
    };
  }
}
