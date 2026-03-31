import { computed, ref } from "vue";

const STORAGE_KEY = "ai-query-app:insights";
const MAX_EVENTS = 50;

const metrics = ref(loadMetrics());

function loadMetrics() {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY);
    if (!rawValue) {
      return [];
    }

    const parsedValue = JSON.parse(rawValue);
    return Array.isArray(parsedValue) ? parsedValue : [];
  } catch {
    return [];
  }
}

function persistMetrics(nextMetrics) {
  metrics.value = nextMetrics;

  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextMetrics));
}

export function recordSearchMetric({ question, rowCount, durationMs, status, errorMessage = "" }) {
  const nextEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    question: String(question || "").trim(),
    rowCount: Number.isFinite(rowCount) ? rowCount : 0,
    durationMs: Number.isFinite(durationMs) ? durationMs : null,
    status: status === "error" ? "error" : "success",
    errorMessage: errorMessage ? String(errorMessage) : "",
    createdAt: new Date().toISOString(),
  };

  persistMetrics([nextEntry, ...metrics.value].slice(0, MAX_EVENTS));
}

export function clearSearchMetrics() {
  persistMetrics([]);
}

export function useInsights() {
  const entries = computed(() => metrics.value);
  const successfulEntries = computed(() => entries.value.filter((entry) => entry.status === "success"));

  const totalQueries = computed(() => entries.value.length);
  const successfulQueries = computed(() => successfulEntries.value.length);
  const totalRowsReturned = computed(() => successfulEntries.value.reduce((sum, entry) => sum + entry.rowCount, 0));
  const averageRowsReturned = computed(() => {
    if (!successfulQueries.value) {
      return 0;
    }

    return totalRowsReturned.value / successfulQueries.value;
  });

  const successfulDurations = computed(() =>
    successfulEntries.value
      .map((entry) => entry.durationMs)
      .filter((durationMs) => Number.isFinite(durationMs)),
  );

  const averageResponseTimeMs = computed(() => {
    if (!successfulDurations.value.length) {
      return 0;
    }

    const totalDuration = successfulDurations.value.reduce((sum, durationMs) => sum + durationMs, 0);
    return totalDuration / successfulDurations.value.length;
  });

  const maxResponseTimeMs = computed(() => {
    if (!successfulDurations.value.length) {
      return 0;
    }

    return Math.max(...successfulDurations.value);
  });

  return {
    entries,
    totalQueries,
    successfulQueries,
    totalRowsReturned,
    averageRowsReturned,
    averageResponseTimeMs,
    maxResponseTimeMs,
    clearSearchMetrics,
  };
}
