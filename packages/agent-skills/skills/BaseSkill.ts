import { AgentContext } from "../context/AgentContext";
import { McpToolClient } from "../tools/McpToolClient";

export type SkillStatus = "CONTINUE" | "TERMINATE" | "ERROR";

export interface SkillOutput {
  status: SkillStatus;
  message: string;
  suggestedNextSkill?: string;
}

export abstract class BaseSkill {
  public abstract readonly name: string;
  public abstract readonly description: string;

  public abstract canHandle(context: AgentContext): Promise<boolean> | boolean;

  public abstract execute(context: AgentContext, toolClient: McpToolClient): Promise<SkillOutput>;
}
