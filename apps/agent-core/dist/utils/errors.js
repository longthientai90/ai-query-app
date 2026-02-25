"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentInternalError = exports.ToolExecutionError = exports.SkillNotFoundError = exports.AgentCoreError = void 0;
class AgentCoreError extends Error {
    code;
    constructor(message, code) {
        super(message);
        this.code = code;
        this.name = this.constructor.name;
    }
}
exports.AgentCoreError = AgentCoreError;
class SkillNotFoundError extends AgentCoreError {
    constructor(skillId) {
        super(`Skill not found: ${skillId}`, "SKILL_NOT_FOUND");
    }
}
exports.SkillNotFoundError = SkillNotFoundError;
class ToolExecutionError extends AgentCoreError {
    cause;
    constructor(toolName, message, cause) {
        super(`Tool execution failed for '${toolName}': ${message}`, "TOOL_EXECUTION_FAILED");
        this.cause = cause;
    }
}
exports.ToolExecutionError = ToolExecutionError;
class AgentInternalError extends AgentCoreError {
    cause;
    constructor(message, cause) {
        super(message, "AGENT_INTERNAL_ERROR");
        this.cause = cause;
    }
}
exports.AgentInternalError = AgentInternalError;
