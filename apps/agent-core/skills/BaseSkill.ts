import { AgentContext } from "../context/AgentContext";
import { ToolClient } from "../tools/McpToolClient";

export interface SkillResult {
  done?: boolean;
  metadata?: Record<string, unknown>;
}

export abstract class BaseSkill {
  abstract readonly id: string;
  abstract readonly description: string;

  abstract canHandle(context: AgentContext): Promise<boolean> | boolean;

  abstract execute(context: AgentContext, toolClient: ToolClient): Promise<SkillResult>;
}