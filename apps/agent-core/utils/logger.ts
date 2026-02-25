export type LogLevel = "debug" | "info" | "warn" | "error";

export interface LogEntry {
  level: LogLevel;
  event: string;
  conversationId?: string;
  [key: string]: unknown;
}

type LogPayload = {
  event: string;
  conversationId?: string;
  [key: string]: unknown;
};

function emit(entry: LogEntry): void {
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

export const logger = {
  debug(entry: LogPayload): void {
    emit({ ...entry, level: "debug" });
  },
  info(entry: LogPayload): void {
    emit({ ...entry, level: "info" });
  },
  warn(entry: LogPayload): void {
    emit({ ...entry, level: "warn" });
  },
  error(entry: LogPayload): void {
    emit({ ...entry, level: "error" });
  },
};
