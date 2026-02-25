"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.schemaAnalyzerPrompt = schemaAnalyzerPrompt;
function schemaAnalyzerPrompt(userQuestion) {
    return [
        "You are Schema Analyzer.",
        "Determine if current task needs schema discovery before SQL generation.",
        `User question: ${userQuestion}`,
        "Return concise reasoning.",
    ].join("\n");
}
