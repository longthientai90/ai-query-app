"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SkillRunner = void 0;
const errors_1 = require("../utils/errors");
const logger_1 = require("../utils/logger");
class SkillRunner {
    router;
    registry;
    toolClient;
    constructor(router, registry, toolClient) {
        this.router = router;
        this.registry = registry;
        this.toolClient = toolClient;
    }
    async run(context) {
        // Main orchestration loop: route -> execute skill -> update lifecycle state.
        while (context.turnCount < context.maxTurns) {
            const nextSkillId = await this.router.route(context);
            // Router can explicitly stop the chain by returning TERMINATE/null.
            if (!nextSkillId || nextSkillId === "TERMINATE") {
                break;
            }
            const skill = this.registry.get(nextSkillId);
            const startedAt = Date.now();
            try {
                const result = await skill.execute(context, this.toolClient);
                logger_1.logger.info({
                    event: "skill_execute",
                    conversationId: context.conversationId,
                    skill: skill.id,
                    durationMs: Date.now() - startedAt,
                    status: "success",
                });
                if (result.done) {
                    // Skill requests early stop (e.g., final answer already produced).
                    context.terminate();
                    break;
                }
            }
            catch (error) {
                logger_1.logger.error({
                    event: "skill_execute",
                    conversationId: context.conversationId,
                    skill: skill.id,
                    durationMs: Date.now() - startedAt,
                    status: "error",
                    error: error instanceof Error ? error.message : String(error),
                });
                context.appendMessage("system", "An internal error occurred while processing your request.");
                throw new errors_1.AgentInternalError(`Failed executing skill '${skill.id}'`, error);
            }
            // Count only successful turns to enforce max loop budget.
            context.turnCount += 1;
            if (context.terminated) {
                break;
            }
        }
        return context;
    }
}
exports.SkillRunner = SkillRunner;
