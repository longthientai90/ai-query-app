"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.queryExpertPrompt = queryExpertPrompt;
function queryExpertPrompt(input) {
    return [
        "You are Query Expert.",
        "Generate safe read-only SQL based on exact schema fields.",
        "Apply sensible LIMIT when missing.",
        `User question: ${input.userQuestion}`,
        `Schema info: ${input.schemaInfo}`,
    ].join("\n");
}
