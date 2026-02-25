"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SynthesisSkill = exports.DataFetchSkill = void 0;
const BaseSkill_1 = require("./BaseSkill");
class DataFetchSkill extends BaseSkill_1.BaseSkill {
    id = "data_fetch";
    description = "Fetches top transaction data from tool layer";
    canHandle(context) {
        // Run once at the beginning: only when result set does not exist yet.
        return !context.variables["lastQueryResult"];
    }
    async execute(context, toolClient) {
        const rows = await toolClient.callTool("postgres_query", {
            sql: "SELECT id, amount FROM tx ORDER BY amount DESC LIMIT 5",
        });
        context.mergeVariables({
            lastQueryResult: rows,
        });
        context.appendMessage("tool", `Fetched ${rows.length} rows from postgres_query`);
        return { done: false };
    }
}
exports.DataFetchSkill = DataFetchSkill;
class SynthesisSkill extends BaseSkill_1.BaseSkill {
    id = "synthesis";
    description = "Composes final user-facing answer from fetched data";
    canHandle(context) {
        // Run after fetch: synthesize final answer from shared variable.
        return Boolean(context.variables["lastQueryResult"] && !context.variables["finalResponse"]);
    }
    async execute(context) {
        const rows = context.variables["lastQueryResult"] ?? [];
        const response = rows
            .map((row, index) => `${index + 1}. tx #${row.id} - amount ${row.amount}`)
            .join("\n");
        context.mergeVariables({ finalResponse: response || "No data found." });
        context.appendMessage("agent", response || "No data found.");
        return { done: true };
    }
}
exports.SynthesisSkill = SynthesisSkill;
