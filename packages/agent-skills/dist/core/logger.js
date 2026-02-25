"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = void 0;
function write(level, payload) {
    const line = JSON.stringify({ ts: new Date().toISOString(), level, ...payload });
    if (level === "error") {
        console.error(line);
        return;
    }
    console.log(line);
}
exports.logger = {
    info(payload) {
        write("info", payload);
    },
    warn(payload) {
        write("warn", payload);
    },
    error(payload) {
        write("error", payload);
    },
};
