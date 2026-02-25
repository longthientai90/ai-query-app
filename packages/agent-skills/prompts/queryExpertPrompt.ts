export function queryExpertPrompt(input: {
  userQuestion: string;
  schemaInfo: string;
}): string {
  return [
    "You are Query Expert.",
    "Generate safe read-only SQL based on exact schema fields.",
    "Apply sensible LIMIT when missing.",
    `User question: ${input.userQuestion}`,
    `Schema info: ${input.schemaInfo}`,
  ].join("\n");
}