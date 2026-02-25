"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SkillRunner = void 0;
const logger_1 = require("./logger");
class SkillRunner {
    registry;
    router;
    toolClient;
    maxTurns;
    constructor(registry, router, toolClient, maxTurns = 8) {
        this.registry = registry;
        this.router = router;
        this.toolClient = toolClient;
        this.maxTurns = maxTurns;
    }
    async run(context) {
        // Bounded loop prevents accidental endless chaining.
        for (let turn = 1; turn <= this.maxTurns; turn += 1) {
            const next = await this.router.route(context);
            if (!next) {
                logger_1.logger.warn({ event: "skill_runner_stop", reason: "no_skill_selected", turn });
                break;
            }
            const skill = this.registry.get(next);
            if (!skill) {
                logger_1.logger.warn({ event: "skill_runner_stop", reason: "skill_not_found", skill: next, turn });
                break;
            }
            // Router may suggest a skill that is currently inapplicable; skip safely.
            if (!(await skill.canHandle(context))) {
                logger_1.logger.info({ event: "skill_skip", skill: skill.name, turn });
                context.nextSkillHint = undefined;
                continue;
            }
            const startedAt = Date.now();
            try {
                const output = await skill.execute(context, this.toolClient);
                logger_1.logger.info({
                    event: "skill_execute",
                    skill: skill.name,
                    turn,
                    durationMs: Date.now() - startedAt,
                    status: output.status,
                });
                context.appendMessage("system", `[${skill.name}] ${output.message}`);
                context.nextSkillHint = output.suggestedNextSkill;
                if (output.status === "TERMINATE" || output.status === "ERROR") {
                    break;
                }
            }
            catch (error) {
                const message = error instanceof Error ? error.message : "Unknown skill error";
                context.setVariable("lastError", message);
                context.appendMessage("system", `[${skill.name}] failed: ${message}`);
                logger_1.logger.error({
                    event: "skill_execute_error",
                    skill: skill.name,
                    turn,
                    durationMs: Date.now() - startedAt,
                    error: message,
                });
                // Graceful fallback: preserve context and stop chaining instead of crashing caller.
                break;
            }
        }
        return context;
    }
}
exports.SkillRunner = SkillRunner;
