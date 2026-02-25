import { AgentContext } from "../../context/AgentContext";
import { schemaAnalyzerPrompt } from "../../prompts/schemaAnalyzerPrompt";
import { McpToolClient } from "../../tools/McpToolClient";
import { BaseSkill, SkillOutput } from "../BaseSkill";

export class SchemaAnalyzerSkill extends BaseSkill {
  public readonly name = "schema_analyzer";
  public readonly description = "Analyzes whether schema data is needed and fetches DB schema metadata.";

  public canHandle(context: AgentContext): boolean {
    // Only fetch schema when it has not been discovered in current context.
    return !context.getVariable("dbSchemaInfo");
  }

  public async execute(context: AgentContext, toolClient: McpToolClient): Promise<SkillOutput> {
    const question = context.getLatestUserMessage()?.content ?? "";
    const reasoning = schemaAnalyzerPrompt(question);

    const schema = await toolClient.callTool<string>("postgres_get_schema", {
      mode: "compact",
      reasoning,
    });

    // Pass schema forward so query skill can generate accurate SQL.
    context.setVariable("dbSchemaInfo", schema);
    context.nextSkillHint = "query_expert";

    return {
      status: "CONTINUE",
      message: "Schema analyzed and loaded.",
      suggestedNextSkill: "query_expert",
    };
  }
}
