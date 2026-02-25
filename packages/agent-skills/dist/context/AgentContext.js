"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentContext = void 0;
class AgentContext {
    // Conversation timeline shared across all skills.
    history = [];
    // Shared whiteboard for cross-skill data handoff.
    variables = {};
    // Optional explicit next step chosen by current skill.
    nextSkillHint;
    appendMessage(role, content) {
        this.history.push({ role, content, createdAt: new Date().toISOString() });
    }
    setVariable(key, value) {
        this.variables[key] = value;
    }
    getVariable(key) {
        return this.variables[key];
    }
    getLatestUserMessage() {
        for (let i = this.history.length - 1; i >= 0; i -= 1) {
            if (this.history[i].role === "user") {
                return this.history[i];
            }
        }
        return undefined;
    }
}
exports.AgentContext = AgentContext;
