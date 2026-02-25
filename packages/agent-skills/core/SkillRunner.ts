import { AgentContext } from "../context/AgentContext";
import { logger } from "./logger";
import { SkillRouter } from "../router/SkillRouter";
import { SkillRegistry } from "../skills/SkillRegistry";
import { McpToolClient } from "../tools/McpToolClient";

export class SkillRunner {
  constructor(
    private readonly registry: SkillRegistry,
    private readonly router: SkillRouter,
    private readonly toolClient: McpToolClient,
    private readonly maxTurns: number = 8,
  ) {}

  async run(context: AgentContext): Promise<AgentContext> {
    // Bounded loop prevents accidental endless chaining.
    for (let turn = 1; turn <= this.maxTurns; turn += 1) {
      const next = await this.router.route(context);
      if (!next) {
        logger.warn({ event: "skill_runner_stop", reason: "no_skill_selected", turn });
        break;
      }

      const skill = this.registry.get(next);
      if (!skill) {
        logger.warn({ event: "skill_runner_stop", reason: "skill_not_found", skill: next, turn });
        break;
      }

      // Router may suggest a skill that is currently inapplicable; skip safely.
      if (!(await skill.canHandle(context))) {
        logger.info({ event: "skill_skip", skill: skill.name, turn });
        context.nextSkillHint = undefined;
        continue;
      }

      const startedAt = Date.now();
      try {
        const output = await skill.execute(context, this.toolClient);
        logger.info({
          event: "skill_execute",
          skill: skill.name,
          turn,
          durationMs: Date.now() - startedAt,
          status: output.status,
        });

        context.appendMessage("system", `[${skill.name}] ${output.message}`);
        context.nextSkillHint = output.suggestedNextSkill;

        if (output.status === "TERMINATE" || output.status === "ERROR") {
          break;
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown skill error";
        context.setVariable("lastError", message);
        context.appendMessage("system", `[${skill.name}] failed: ${message}`);
        logger.error({
          event: "skill_execute_error",
          skill: skill.name,
          turn,
          durationMs: Date.now() - startedAt,
          error: message,
        });
        // Graceful fallback: preserve context and stop chaining instead of crashing caller.
        break;
      }
    }

    return context;
  }
}
