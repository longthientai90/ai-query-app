export class AgentCoreError extends Error {
  constructor(message: string, public readonly code: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class SkillNotFoundError extends AgentCoreError {
  constructor(skillId: string) {
    super(`Skill not found: ${skillId}`, "SKILL_NOT_FOUND");
  }
}

export class ToolExecutionError extends AgentCoreError {
  constructor(toolName: string, message: string, public readonly cause?: unknown) {
    super(`Tool execution failed for '${toolName}': ${message}`, "TOOL_EXECUTION_FAILED");
  }
}

export class AgentInternalError extends AgentCoreError {
  constructor(message: string, public readonly cause?: unknown) {
    super(message, "AGENT_INTERNAL_ERROR");
  }
}