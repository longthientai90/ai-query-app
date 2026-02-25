export interface SkillLogPayload {
  event: string;
  [key: string]: unknown;
}

function write(level: "info" | "warn" | "error", payload: SkillLogPayload): void {
  const line = JSON.stringify({ ts: new Date().toISOString(), level, ...payload });
  if (level === "error") {
    console.error(line);
    return;
  }
  console.log(line);
}

export const logger = {
  info(payload: SkillLogPayload): void {
    write("info", payload);
  },
  warn(payload: SkillLogPayload): void {
    write("warn", payload);
  },
  error(payload: SkillLogPayload): void {
    write("error", payload);
  },
};