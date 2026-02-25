export type MessageRole = "user" | "agent" | "system" | "tool";

export interface Message {
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface AgentContextParams {
  conversationId: string;
  history?: Message[];
  variables?: Record<string, unknown>;
  turnCount?: number;
  maxTurns?: number;
  terminated?: boolean;
}

export class AgentContext {
  // Stable identifier for tracing one conversation across logs and components.
  public readonly conversationId: string;
  // Ordered conversation timeline shared by runner/router/skills.
  public history: Message[];
  // Shared scratchpad for passing data between chained skills.
  public variables: Record<string, unknown>;
  public turnCount: number;
  public maxTurns: number;
  public terminated: boolean;

  constructor(params: AgentContextParams) {
    this.conversationId = params.conversationId;
    this.history = params.history ? [...params.history] : [];
    this.variables = params.variables ? { ...params.variables } : {};
    this.turnCount = params.turnCount ?? 0;
    this.maxTurns = params.maxTurns ?? 10;
    this.terminated = params.terminated ?? false;
  }

  appendMessage(role: MessageRole, content: string): void {
    // Keep message creation centralized to guarantee consistent timestamps.
    this.history.push({
      role,
      content,
      createdAt: new Date().toISOString(),
    });
  }

  mergeVariables(next: Record<string, unknown>): void {
    // Shallow merge avoids accidental full replacement of existing state.
    this.variables = {
      ...this.variables,
      ...next,
    };
  }

  getLatestUserMessage(): Message | undefined {
    // Reverse scan returns the latest user input in O(n) without extra indexing.
    for (let i = this.history.length - 1; i >= 0; i -= 1) {
      const item = this.history[i];
      if (item.role === "user") {
        return item;
      }
    }
    return undefined;
  }

  terminate(): void {
    this.terminated = true;
  }
}
