export function performanceTunerPrompt(targetQuery: string, explainPlan: string): string {
  return [
    "You are Performance Tuner.",
    "Inspect explain plan and propose better SQL text.",
    `Target query: ${targetQuery}`,
    `Explain: ${explainPlan}`,
  ].join("\n");
}