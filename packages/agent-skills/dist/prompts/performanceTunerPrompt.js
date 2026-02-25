"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.performanceTunerPrompt = performanceTunerPrompt;
function performanceTunerPrompt(targetQuery, explainPlan) {
    return [
        "You are Performance Tuner.",
        "Inspect explain plan and propose better SQL text.",
        `Target query: ${targetQuery}`,
        `Explain: ${explainPlan}`,
    ].join("\n");
}
