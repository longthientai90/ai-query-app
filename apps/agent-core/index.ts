import { Agent } from "./core/Agent";
import { SkillRegistry } from "./skills/SkillRegistry";
import { McpToolClient } from "./tools/McpToolClient";
import { DataFetchSkill, SynthesisSkill } from "./skills/DummySkills";

async function main(): Promise<void> {
  const registry = new SkillRegistry();
  registry.register(new DataFetchSkill());
  registry.register(new SynthesisSkill());

  const toolClient = new McpToolClient();
  toolClient.registerHandler("postgres_query", async () => {
    return [
      { id: "A100", amount: 12000 },
      { id: "A220", amount: 9400 },
      { id: "A130", amount: 8800 },
      { id: "A180", amount: 8100 },
      { id: "A090", amount: 7900 },
    ];
  });

  const agent = new Agent(registry, toolClient);
  const result = await agent.handle({
    conversationId: "demo-conversation",
    userMessage: "Show me the top 5 largest transactions",
  });

  const final = result.variables["finalResponse"] as string | undefined;
  console.log("\n=== Agent Final Response ===");
  console.log(final ?? "No final response generated.");
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
