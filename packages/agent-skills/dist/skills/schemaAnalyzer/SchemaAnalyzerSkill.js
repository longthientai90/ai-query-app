"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SchemaAnalyzerSkill = void 0;
const schemaAnalyzerPrompt_1 = require("../../prompts/schemaAnalyzerPrompt");
const BaseSkill_1 = require("../BaseSkill");
class SchemaAnalyzerSkill extends BaseSkill_1.BaseSkill {
    name = "schema_analyzer";
    description = "Analyzes whether schema data is needed and fetches DB schema metadata.";
    canHandle(context) {
        // Only fetch schema when it has not been discovered in current context.
        return !context.getVariable("dbSchemaInfo");
    }
    async execute(context, toolClient) {
        const question = context.getLatestUserMessage()?.content ?? "";
        const reasoning = (0, schemaAnalyzerPrompt_1.schemaAnalyzerPrompt)(question);
        const schema = await toolClient.callTool("postgres_get_schema", {
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
exports.SchemaAnalyzerSkill = SchemaAnalyzerSkill;
