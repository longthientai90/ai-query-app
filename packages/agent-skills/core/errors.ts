export class SkillExecutionError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
    this.name = "SkillExecutionError";
  }
}

export class ToolExecutionError extends Error {
  constructor(toolName: string, message: string, public readonly cause?: unknown) {
    super(`[${toolName}] ${message}`);
    this.name = "ToolExecutionError";
  }
}