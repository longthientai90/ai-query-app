import { ref } from "vue";

const DEFAULT_SUGGEST_API_URL = "http://localhost:8080/api/chart/suggest";
const SUGGEST_API_URL = import.meta.env.VITE_CHART_SUGGEST_API_URL || DEFAULT_SUGGEST_API_URL;

export function useChartSuggestions() {
  const isLoading = ref(false);
  const error = ref("");
  const suggestions = ref([]);
  const summary = ref("");
  const canChart = ref(false);

  const suggestCharts = async ({ question, result }) => {
    const columns = Array.isArray(result?.columns) ? result.columns : [];
    const rows = Array.isArray(result?.rows) ? result.rows : [];
    const rowCount = Number.isFinite(result?.rowCount) ? result.rowCount : rows.length;

    if (!question?.trim() || !columns.length || !rows.length) {
      error.value = "This result does not have enough data to suggest a chart.";
      suggestions.value = [];
      summary.value = "";
      canChart.value = false;
      return null;
    }

    isLoading.value = true;
    error.value = "";

    try {
      const response = await fetch(SUGGEST_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question.trim(),
          columns,
          rows,
          row_count: rowCount,
        }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = payload?.detail || "Chart suggestion request failed.";
        throw new Error(typeof detail === "string" ? detail : "Chart suggestion request failed.");
      }

      const nextSuggestions = Array.isArray(payload?.suggestions) ? payload.suggestions : [];
      suggestions.value = nextSuggestions;
      summary.value = typeof payload?.summary === "string" ? payload.summary : "";
      canChart.value = Boolean(payload?.can_chart);
      return payload;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Unexpected error happened.";
      suggestions.value = [];
      summary.value = "";
      canChart.value = false;
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const reset = () => {
    error.value = "";
    suggestions.value = [];
    summary.value = "";
    canChart.value = false;
  };

  return {
    isLoading,
    error,
    suggestions,
    summary,
    canChart,
    suggestCharts,
    reset,
  };
}
