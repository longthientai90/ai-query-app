import { BaseSkill } from "./BaseSkill";
import { SkillNotFoundError } from "../utils/errors";

export class SkillRegistry {
  private readonly skills = new Map<string, BaseSkill>();

  register(skill: BaseSkill): void {
    this.skills.set(skill.id, skill);
  }

  get(skillId: string): BaseSkill {
    const skill = this.skills.get(skillId);
    if (!skill) {
      throw new SkillNotFoundError(skillId);
    }
    return skill;
  }

  list(): BaseSkill[] {
    return [...this.skills.values()];
  }

  describe(): Array<{ id: string; description: string }> {
    return this.list().map((skill) => ({
      id: skill.id,
      description: skill.description,
    }));
  }
}