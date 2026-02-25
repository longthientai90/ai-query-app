import { AgentContext } from "../context/AgentContext";
import { SkillRunner } from "./SkillRunner";
import { SkillRegistry } from "../skills/SkillRegistry";
import { RuleBasedSkillRouter } from "../router/SkillRouter";
import { ToolClient } from "../tools/McpToolClient";

export interface AgentRunInput {
  conversationId: string;
  userMessage: string;
  maxTurns?: number;
}

export class Agent {
  private readonly runner: SkillRunner;

  constructor(registry: SkillRegistry, toolClient: ToolClient) {
    const router = new RuleBasedSkillRouter(registry);
    this.runner = new SkillRunner(router, registry, toolClient);
  }

  async handle(input: AgentRunInput): Promise<AgentContext> {
    const context = new AgentContext({
      conversationId: input.conversationId,
      maxTurns: input.maxTurns,
    });
    context.appendMessage("user", input.userMessage);
    return this.runner.run(context);
  }
}