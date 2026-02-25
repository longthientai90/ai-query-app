import { AgentContext } from "../context/AgentContext";
import { SkillRegistry } from "../skills/SkillRegistry";
import { SkillRouter } from "../router/SkillRouter";
import { ToolClient } from "../tools/McpToolClient";
import { AgentInternalError } from "../utils/errors";
import { logger } from "../utils/logger";

export class SkillRunner {
  constructor(
    private readonly router: SkillRouter,
    private readonly registry: SkillRegistry,
    private readonly toolClient: ToolClient,
  ) {}

  async run(context: AgentContext): Promise<AgentContext> {
    // Main orchestration loop: route -> execute skill -> update lifecycle state.
    while (context.turnCount < context.maxTurns) {
      const nextSkillId = await this.router.route(context);
      // Router can explicitly stop the chain by returning TERMINATE/null.
      if (!nextSkillId || nextSkillId === "TERMINATE") {
        break;
      }

      const skill = this.registry.get(nextSkillId);
      const startedAt = Date.now();
      try {
        const result = await skill.execute(context, this.toolClient);
        logger.info({
          event: "skill_execute",
          conversationId: context.conversationId,
          skill: skill.id,
          durationMs: Date.now() - startedAt,
          status: "success",
        });

        if (result.done) {
          // Skill requests early stop (e.g., final answer already produced).
          context.terminate();
          break;
        }
      } catch (error) {
        logger.error({
          event: "skill_execute",
          conversationId: context.conversationId,
          skill: skill.id,
          durationMs: Date.now() - startedAt,
          status: "error",
          error: error instanceof Error ? error.message : String(error),
        });
        context.appendMessage("system", "An internal error occurred while processing your request.");
        throw new AgentInternalError(
          `Failed executing skill '${skill.id}'`,
          error,
        );
      }

      // Count only successful turns to enforce max loop budget.
      context.turnCount += 1;
      if (context.terminated) {
        break;
      }
    }

    return context;
  }
}
