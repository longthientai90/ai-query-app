"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ToolExecutionError = exports.SkillExecutionError = void 0;
class SkillExecutionError extends Error {
    cause;
    constructor(message, cause) {
        super(message);
        this.cause = cause;
        this.name = "SkillExecutionError";
    }
}
exports.SkillExecutionError = SkillExecutionError;
class ToolExecutionError extends Error {
    cause;
    constructor(toolName, message, cause) {
        super(`[${toolName}] ${message}`);
        this.cause = cause;
        this.name = "ToolExecutionError";
    }
}
exports.ToolExecutionError = ToolExecutionError;
