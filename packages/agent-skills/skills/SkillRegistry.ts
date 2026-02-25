import { BaseSkill } from "./BaseSkill";

export class SkillRegistry {
  private readonly skills: Map<string, BaseSkill> = new Map();

  public register(skill: BaseSkill): void {
    this.skills.set(skill.name, skill);
  }

  public get(name: string): BaseSkill | undefined {
    return this.skills.get(name);
  }

  public getAll(): BaseSkill[] {
    return Array.from(this.skills.values());
  }

  public getAllDescriptions(): { name: string; description: string }[] {
    return this.getAll().map((skill) => ({
      name: skill.name,
      description: skill.description,
    }));
  }
}