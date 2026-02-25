export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface AgentContextVariables {
  dbSchemaInfo?: string;
  targetQuery?: string;
  queryExplainPlan?: string;
  queryResults?: unknown;
  lastError?: string;
  [key: string]: unknown;
}

export class AgentContext {
  // Conversation timeline shared across all skills.
  public history: Message[] = [];
  // Shared whiteboard for cross-skill data handoff.
  public variables: AgentContextVariables = {};
  // Optional explicit next step chosen by current skill.
  public nextSkillHint?: string;

  appendMessage(role: MessageRole, content: string): void {
    this.history.push({ role, content, createdAt: new Date().toISOString() });
  }

  setVariable(key: keyof AgentContextVariables | string, value: unknown): void {
    this.variables[key] = value;
  }

  getVariable<T = unknown>(key: keyof AgentContextVariables | string): T | undefined {
    return this.variables[key] as T | undefined;
  }

  getLatestUserMessage(): Message | undefined {
    for (let i = this.history.length - 1; i >= 0; i -= 1) {
      if (this.history[i].role === "user") {
        return this.history[i];
      }
    }
    return undefined;
  }
}
