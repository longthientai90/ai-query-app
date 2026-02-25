import { AgentContext } from "./context/AgentContext";
import { SkillRunner } from "./core/SkillRunner";
import { SkillRouter } from "./router/SkillRouter";
import { SkillRegistry } from "./skills/SkillRegistry";
import { QueryExpertSkill } from "./skills/queryExpert/QueryExpertSkill";
import { SchemaAnalyzerSkill } from "./skills/schemaAnalyzer/SchemaAnalyzerSkill";
import { PerformanceTunerSkill } from "./skills/performanceTuner/PerformanceTunerSkill";
import { McpToolClient } from "./tools/McpToolClient";

async function main(): Promise<void> {
  const registry = new SkillRegistry();
  registry.register(new SchemaAnalyzerSkill());
  registry.register(new QueryExpertSkill());
  registry.register(new PerformanceTunerSkill());

  const toolClient = new McpToolClient();
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

  const context = new AgentContext();
  context.appendMessage("user", "Show me the top 5 largest transactions");

  const router = new SkillRouter(registry);
  const runner = new SkillRunner(registry, router, toolClient, 8);
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
