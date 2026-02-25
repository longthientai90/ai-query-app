"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentContext = void 0;
class AgentContext {
    // Stable identifier for tracing one conversation across logs and components.
    conversationId;
    // Ordered conversation timeline shared by runner/router/skills.
    history;
    // Shared scratchpad for passing data between chained skills.
    variables;
    turnCount;
    maxTurns;
    terminated;
    constructor(params) {
        this.conversationId = params.conversationId;
        this.history = params.history ? [...params.history] : [];
        this.variables = params.variables ? { ...params.variables } : {};
        this.turnCount = params.turnCount ?? 0;
        this.maxTurns = params.maxTurns ?? 10;
        this.terminated = params.terminated ?? false;
    }
    appendMessage(role, content) {
        // Keep message creation centralized to guarantee consistent timestamps.
        this.history.push({
            role,
            content,
            createdAt: new Date().toISOString(),
        });
    }
    mergeVariables(next) {
        // Shallow merge avoids accidental full replacement of existing state.
        this.variables = {
            ...this.variables,
            ...next,
        };
    }
    getLatestUserMessage() {
        // Reverse scan returns the latest user input in O(n) without extra indexing.
        for (let i = this.history.length - 1; i >= 0; i -= 1) {
            const item = this.history[i];
            if (item.role === "user") {
                return item;
            }
        }
        return undefined;
    }
    terminate() {
        this.terminated = true;
    }
}
exports.AgentContext = AgentContext;
