import { ref } from "vue";

const DEFAULT_RENDER_API_URL = "http://localhost:8080/api/chart/render";
const RENDER_API_URL = import.meta.env.VITE_CHART_RENDER_API_URL || DEFAULT_RENDER_API_URL;
const MAX_SAMPLE_ROWS = 20;

export function useChartRender() {
  const isLoading = ref(false);
  const error = ref("");
  const chart = ref(null);

  const renderChart = async ({ question, result, suggestion }) => {
    const rows = Array.isArray(result?.rows) ? result.rows.slice(0, MAX_SAMPLE_ROWS) : [];
    const columns = Array.isArray(result?.columns) ? result.columns : [];

    if (!question?.trim() || !suggestion || !rows.length) {
      error.value = "This result does not have enough data to render a chart.";
      chart.value = null;
      return null;
    }

    isLoading.value = true;
    error.value = "";

    try {
      const response = await fetch(RENDER_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question.trim(),
          chart_type: suggestion.type,
          x_column: suggestion.x_column,
          y_column: suggestion.y_column,
          columns,
          rows,
        }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = payload?.detail || "Chart render request failed.";
        throw new Error(typeof detail === "string" ? detail : "Chart render request failed.");
      }

      chart.value = payload;
      return payload;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Unexpected error happened.";
      chart.value = null;
      return null;
    } finally {
      isLoading.value = false;
    }
  };

  const reset = () => {
    error.value = "";
    chart.value = null;
  };

  return {
    isLoading,
    error,
    chart,
    renderChart,
    reset,
  };
}
