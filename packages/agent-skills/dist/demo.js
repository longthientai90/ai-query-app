"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const AgentContext_1 = require("./context/AgentContext");
const SkillRunner_1 = require("./core/SkillRunner");
const SkillRouter_1 = require("./router/SkillRouter");
const SkillRegistry_1 = require("./skills/SkillRegistry");
const QueryExpertSkill_1 = require("./skills/queryExpert/QueryExpertSkill");
const SchemaAnalyzerSkill_1 = require("./skills/schemaAnalyzer/SchemaAnalyzerSkill");
const PerformanceTunerSkill_1 = require("./skills/performanceTuner/PerformanceTunerSkill");
const McpToolClient_1 = require("./tools/McpToolClient");
async function main() {
    const registry = new SkillRegistry_1.SkillRegistry();
    registry.register(new SchemaAnalyzerSkill_1.SchemaAnalyzerSkill());
    registry.register(new QueryExpertSkill_1.QueryExpertSkill());
    registry.register(new PerformanceTunerSkill_1.PerformanceTunerSkill());
    const toolClient = new McpToolClient_1.McpToolClient();
    toolClient.registerTool("postgres_get_schema", async () => {
        return "transactions(id, amount, created_at)";
    });
    toolClient.registerTool("postgres_explain", async ({ sql }) => {
        return `Seq Scan on transactions for sql: ${String(sql)}`;
    });
    toolClient.registerTool("postgres_query", async ({ sql }) => {
        return {
            sql,
            rows: [
                { id: "TX001", amount: 12000 },
                { id: "TX002", amount: 9700 },
            ],
        };
    });
    const context = new AgentContext_1.AgentContext();
    context.appendMessage("user", "Show me the top 5 largest transactions");
    const router = new SkillRouter_1.SkillRouter(registry);
    const runner = new SkillRunner_1.SkillRunner(registry, router, toolClient, 8);
    const result = await runner.run(context);
    console.log("\n=== Skill System Result ===");
    console.log(JSON.stringify(result.variables, null, 2));
}
if (require.main === module) {
    main().catch((error) => {
        console.error(error);
        process.exitCode = 1;
    });
}
