"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.QueryExpertSkill = void 0;
const queryExpertPrompt_1 = require("../../prompts/queryExpertPrompt");
const BaseSkill_1 = require("../BaseSkill");
function buildSql(question) {
    const normalized = question.toLowerCase();
    if (normalized.includes("top") || normalized.includes("largest")) {
        return "SELECT id, amount FROM transactions ORDER BY amount DESC LIMIT 20";
    }
    return "SELECT * FROM transactions LIMIT 100";
}
function isComplexQuery(sql) {
    const normalized = sql.toLowerCase();
    return normalized.includes(" join ") || normalized.includes(" group by ");
}
class QueryExpertSkill extends BaseSkill_1.BaseSkill {
    name = "query_expert";
    description = "Builds secure SQL from context and executes read-only DB queries.";
    canHandle(context) {
        // Query generation depends on schema awareness.
        return Boolean(context.getVariable("dbSchemaInfo"));
    }
    async execute(context, toolClient) {
        const question = context.getLatestUserMessage()?.content ?? "";
        const schemaInfo = context.getVariable("dbSchemaInfo") ?? "";
        const prompt = (0, queryExpertPrompt_1.queryExpertPrompt)({ userQuestion: question, schemaInfo });
        // Reuse tuned query from tuner when available; otherwise build initial SQL.
        const sql = context.getVariable("targetQuery") ?? buildSql(question);
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
        const rows = await toolClient.callTool("postgres_query", {
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
exports.QueryExpertSkill = QueryExpertSkill;
