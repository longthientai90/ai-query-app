import { AgentContext } from "../context/AgentContext";
import { SkillRegistry } from "../skills/SkillRegistry";

export interface SkillSelector {
  chooseSkill(context: AgentContext, skills: { name: string; description: string }[]): Promise<string | null>;
}

export class HeuristicSkillSelector implements SkillSelector {
  async chooseSkill(context: AgentContext, skills: { name: string; description: string }[]): Promise<string | null> {
    const userText = (context.getLatestUserMessage()?.content ?? "").toLowerCase();
    const hasSchema = Boolean(context.getVariable("dbSchemaInfo"));
    const hasTargetQuery = Boolean(context.getVariable("targetQuery"));
    const hasResults = Boolean(context.getVariable("queryResults"));

    // Route to tuner only when there is a query to tune.
    if (userText.includes("optimize") || userText.includes("performance") || userText.includes("slow")) {
      if (hasTargetQuery && !hasResults) {
        return skills.find((item) => item.name === "performance_tuner")?.name ?? null;
      }
    }

    // If schema exists and query result is not produced yet, move to execution stage.
    if (hasSchema && !hasResults) {
      return skills.find((item) => item.name === "query_expert")?.name ?? null;
    }

    // Default bootstrap step: collect schema first.
    return skills.find((item) => item.name === "schema_analyzer")?.name ?? null;
  }
}

export class SkillRouter {
  constructor(
    private readonly registry: SkillRegistry,
    private readonly selector: SkillSelector = new HeuristicSkillSelector(),
  ) {}

  async route(context: AgentContext): Promise<string | null> {
    // Highest-priority routing signal is explicit chaining hint from previous skill.
    if (context.nextSkillHint) {
      const hinted = this.registry.get(context.nextSkillHint);
      if (hinted) {
        return hinted.name;
      }
    }

    const descriptions = this.registry.getAllDescriptions();
    const selected = await this.selector.chooseSkill(context, descriptions);
    if (!selected || !this.registry.get(selected)) {
      return null;
    }
    return selected;
  }
}
