"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SkillRegistry = void 0;
const errors_1 = require("../utils/errors");
class SkillRegistry {
    skills = new Map();
    register(skill) {
        this.skills.set(skill.id, skill);
    }
    get(skillId) {
        const skill = this.skills.get(skillId);
        if (!skill) {
            throw new errors_1.SkillNotFoundError(skillId);
        }
        return skill;
    }
    list() {
        return [...this.skills.values()];
    }
    describe() {
        return this.list().map((skill) => ({
            id: skill.id,
            description: skill.description,
        }));
    }
}
exports.SkillRegistry = SkillRegistry;
