"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Agent = void 0;
const AgentContext_1 = require("../context/AgentContext");
const SkillRunner_1 = require("./SkillRunner");
const SkillRouter_1 = require("../router/SkillRouter");
class Agent {
    runner;
    constructor(registry, toolClient) {
        const router = new SkillRouter_1.RuleBasedSkillRouter(registry);
        this.runner = new SkillRunner_1.SkillRunner(router, registry, toolClient);
    }
    async handle(input) {
        const context = new AgentContext_1.AgentContext({
            conversationId: input.conversationId,
            maxTurns: input.maxTurns,
        });
        context.appendMessage("user", input.userMessage);
        return this.runner.run(context);
    }
}
exports.Agent = Agent;
