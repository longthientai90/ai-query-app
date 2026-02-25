"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PerformanceTunerSkill = void 0;
const performanceTunerPrompt_1 = require("../../prompts/performanceTunerPrompt");
const BaseSkill_1 = require("../BaseSkill");
function optimizeSql(sql) {
    if (!sql.toLowerCase().includes("limit")) {
        return `${sql} LIMIT 100`;
    }
    return sql.replace("SELECT *", "SELECT id, amount");
}
class PerformanceTunerSkill extends BaseSkill_1.BaseSkill {
    name = "performance_tuner";
    description = "Analyzes explain plan and tunes SQL text before execution.";
    canHandle(context) {
        // Tuning requires an existing SQL draft from query expert.
        return Boolean(context.getVariable("targetQuery"));
    }
    async execute(context, toolClient) {
        const targetQuery = context.getVariable("targetQuery");
        if (!targetQuery) {
            return {
                status: "ERROR",
                message: "No targetQuery available for tuning.",
            };
        }
        const explain = await toolClient.callTool("postgres_explain", { sql: targetQuery });
        const prompt = (0, performanceTunerPrompt_1.performanceTunerPrompt)(targetQuery, explain);
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
exports.PerformanceTunerSkill = PerformanceTunerSkill;
