"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RuleBasedSkillRouter = void 0;
class RuleBasedSkillRouter {
    registry;
    constructor(registry) {
        this.registry = registry;
    }
    async route(context) {
        if (context.terminated) {
            return "TERMINATE";
        }
        // First-match wins: skill registration order is the routing priority.
        const skills = this.registry.list();
        for (const skill of skills) {
            if (await skill.canHandle(context)) {
                return skill.id;
            }
        }
        return "TERMINATE";
    }
}
exports.RuleBasedSkillRouter = RuleBasedSkillRouter;
