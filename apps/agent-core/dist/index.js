"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const Agent_1 = require("./core/Agent");
const SkillRegistry_1 = require("./skills/SkillRegistry");
const McpToolClient_1 = require("./tools/McpToolClient");
const DummySkills_1 = require("./skills/DummySkills");
async function main() {
    const registry = new SkillRegistry_1.SkillRegistry();
    registry.register(new DummySkills_1.DataFetchSkill());
    registry.register(new DummySkills_1.SynthesisSkill());
    const toolClient = new McpToolClient_1.McpToolClient();
    toolClient.registerHandler("postgres_query", async () => {
        return [
            { id: "A100", amount: 12000 },
            { id: "A220", amount: 9400 },
            { id: "A130", amount: 8800 },
            { id: "A180", amount: 8100 },
            { id: "A090", amount: 7900 },
        ];
    });
    const agent = new Agent_1.Agent(registry, toolClient);
    const result = await agent.handle({
        conversationId: "demo-conversation",
        userMessage: "Show me the top 5 largest transactions",
    });
    const final = result.variables["finalResponse"];
    console.log("\n=== Agent Final Response ===");
    console.log(final ?? "No final response generated.");
}
if (require.main === module) {
    main().catch((error) => {
        console.error(error);
        process.exitCode = 1;
    });
}
