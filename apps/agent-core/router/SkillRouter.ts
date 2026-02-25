import { AgentContext } from "../context/AgentContext";
import { SkillRegistry } from "../skills/SkillRegistry";

export interface SkillRouter {
  route(context: AgentContext): Promise<string | null>;
}

export class RuleBasedSkillRouter implements SkillRouter {
  constructor(private readonly registry: SkillRegistry) {}

  async route(context: AgentContext): Promise<string | null> {
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
