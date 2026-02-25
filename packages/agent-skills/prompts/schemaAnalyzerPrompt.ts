export function schemaAnalyzerPrompt(userQuestion: string): string {
  return [
    "You are Schema Analyzer.",
    "Determine if current task needs schema discovery before SQL generation.",
    `User question: ${userQuestion}`,
    "Return concise reasoning.",
  ].join("\n");
}