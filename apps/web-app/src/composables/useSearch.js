import { ref } from "vue";
import { recordSearchMetric } from "./useInsights";

const DEFAULT_API_URL = "http://localhost:8080/api/search";
const API_URL = import.meta.env.VITE_SEARCH_API_URL || DEFAULT_API_URL;

export function useSearch() {
  const isSearching = ref(false);
  const error = ref("");
  const searchResult = ref(null);

  const runSearch = async (question) => {
    if (isSearching.value) {
      return searchResult.value;
    }

    const query = question.trim();
    if (!query) {
      error.value = "Please enter a question before searching.";
      searchResult.value = null;
      return;
    }

    isSearching.value = true;
    error.value = "";

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: query }),
      });

      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        const detail = payload?.detail || "Search request failed.";
        throw new Error(typeof detail === "string" ? detail : "Search request failed.");
      }

      const result = payload?.result;
      if (!result || typeof result !== "object") {
        searchResult.value = null;
        throw new Error("No result data returned from API.");
      }

      const columns = Array.isArray(result.columns) ? result.columns : [];
      const rows = Array.isArray(result.rows) ? result.rows : [];
      const rowCount = Number.isFinite(result.rowCount) ? result.rowCount : rows.length;
      const durationMs = Number.isFinite(result.durationMs) ? result.durationMs : null;

      const normalizedResult = {
        columns,
        rows,
        rowCount,
        durationMs,
      };

      recordSearchMetric({
        question: query,
        rowCount,
        durationMs,
        status: "success",
      });

      searchResult.value = normalizedResult;
      return normalizedResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unexpected error happened.";
      error.value = errorMessage;
      recordSearchMetric({
        question: query,
        rowCount: 0,
        durationMs: null,
        status: "error",
        errorMessage,
      });
      searchResult.value = null;
      return null;
    } finally {
      isSearching.value = false;
    }
  };

  return {
    isSearching,
    error,
    searchResult,
    runSearch,
  };
}
