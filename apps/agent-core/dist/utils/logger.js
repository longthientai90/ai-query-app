"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = void 0;
function emit(entry) {
    const record = {
        ts: new Date().toISOString(),
        ...entry,
    };
    const line = JSON.stringify(record);
    if (entry.level === "error") {
        console.error(line);
        return;
    }
    console.log(line);
}
exports.logger = {
    debug(entry) {
        emit({ ...entry, level: "debug" });
    },
    info(entry) {
        emit({ ...entry, level: "info" });
    },
    warn(entry) {
        emit({ ...entry, level: "warn" });
    },
    error(entry) {
        emit({ ...entry, level: "error" });
    },
};
