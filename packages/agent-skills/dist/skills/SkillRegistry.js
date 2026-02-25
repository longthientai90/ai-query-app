"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SkillRegistry = void 0;
class SkillRegistry {
    skills = new Map();
    register(skill) {
        this.skills.set(skill.name, skill);
    }
    get(name) {
        return this.skills.get(name);
    }
    getAll() {
        return Array.from(this.skills.values());
    }
    getAllDescriptions() {
        return this.getAll().map((skill) => ({
            name: skill.name,
            description: skill.description,
        }));
    }
}
exports.SkillRegistry = SkillRegistry;
