<script setup>
import { ref } from "vue";
import SimpleChart from "../components/ui/SimpleChart.vue";
import SearchBar from "../components/ui/SearchBar.vue";
import ResultTable from "../components/ui/ResultTable.vue";
import { useChartRender } from "../composables/useChartRender";
import { useChartSuggestions } from "../composables/useChartSuggestions";
import { useSearch } from "../composables/useSearch";

const { isSearching, error, runSearch } = useSearch();
const {
  isLoading: isSuggestingChart,
  error: chartSuggestionError,
  suggestions: chartSuggestions,
  summary: chartSummary,
  canChart,
  suggestCharts,
  reset: resetChartSuggestions,
} = useChartSuggestions();
const {
  isLoading: isRenderingChart,
  error: chartRenderError,
  chart: renderedChart,
  renderChart,
  reset: resetRenderedChart,
} = useChartRender();
const tableResult = ref(null);
const lastQuestion = ref("");
const isChartPanelOpen = ref(false);
const selectedSuggestionKey = ref("");

const onSubmit = async (question) => {
  lastQuestion.value = question;
  isChartPanelOpen.value = false;
  selectedSuggestionKey.value = "";
  resetChartSuggestions();
  resetRenderedChart();
  tableResult.value = await runSearch(question);
};

const getSuggestionKey = (suggestion) => `${suggestion.type}:${suggestion.x_column}:${suggestion.y_column}`;

const findSelectedSuggestion = () =>
  chartSuggestions.value.find((suggestion) => getSuggestionKey(suggestion) === selectedSuggestionKey.value) || null;

const onViewChart = async () => {
  if (!tableResult.value) {
    return;
  }

  isChartPanelOpen.value = true;
  selectedSuggestionKey.value = "";
  resetRenderedChart();
  const payload = await suggestCharts({
    question: lastQuestion.value,
    result: tableResult.value,
  });

  if (payload?.suggestions?.length) {
    selectedSuggestionKey.value = getSuggestionKey(payload.suggestions[0]);
  }
};

const onRenderSelectedChart = async () => {
  const selectedSuggestion = findSelectedSuggestion();
  if (!selectedSuggestion || !tableResult.value) {
    return;
  }

  await renderChart({
    question: lastQuestion.value,
    result: tableResult.value,
    suggestion: selectedSuggestion,
  });
};
</script>

<template>
  <main class="relative overflow-hidden px-4 py-10 sm:px-8 lg:py-14">
    <div class="mx-auto max-w-6xl">
      <header class="mb-8 animate-rise text-center">
        <p
          class="mx-auto mb-3 inline-flex rounded-full border border-brand-200 bg-brand-50 px-4 py-1 text-xs font-semibold uppercase tracking-wider text-brand-700"
        >
          AI Search Page
        </p>
        <h1 class="font-heading text-3xl font-bold text-slate-900 sm:text-5xl">
          Premium Query Experience for Your Data
        </h1>
        <p class="mx-auto mt-4 max-w-2xl text-base text-slate-600 sm:text-lg">
          Ask naturally, get structured results instantly, and inspect your returned rows with a clean dynamic table.
        </p>
      </header>

      <SearchBar :loading="isSearching" @submit="onSubmit" />

      <transition name="fade-up" mode="out-in">
        <div
          v-if="isSearching"
          key="loading"
          class="mt-6 rounded-3xl border border-white/70 bg-white/70 p-6 shadow-card backdrop-blur-xl"
        >
          <div class="mb-4 h-4 w-44 animate-pulse rounded bg-slate-200/80" />
          <div class="space-y-3">
            <div class="h-12 animate-pulse rounded-xl bg-slate-200/70" />
            <div class="h-12 animate-pulse rounded-xl bg-slate-200/70" />
            <div class="h-12 animate-pulse rounded-xl bg-slate-200/70" />
            <div class="h-12 animate-pulse rounded-xl bg-slate-200/70" />
          </div>
        </div>

        <ResultTable
          v-else-if="tableResult"
          key="table"
          :result="tableResult"
          :loading="isSearching"
          class="mt-6"
          @view-chart="onViewChart"
        />
      </transition>

      <transition name="fade-up">
        <section
          v-if="isChartPanelOpen"
          class="mt-6 rounded-3xl border border-white/70 bg-white/80 p-6 shadow-card backdrop-blur-xl"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p
                class="inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700"
              >
                Chart Suggestions
              </p>
              <h2 class="mt-3 font-heading text-2xl font-semibold text-slate-900">Suggested Charts</h2>
              <p class="mt-2 max-w-2xl text-sm text-slate-600">
                {{ chartSummary || "Check which chart types fit the returned table before rendering a chart." }}
              </p>
            </div>
            <button
              type="button"
              class="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
              @click="isChartPanelOpen = false"
            >
              Close
            </button>
          </div>

          <div
            v-if="isSuggestingChart"
            class="mt-5 rounded-2xl border border-slate-200/80 bg-slate-50 px-4 py-5 text-sm text-slate-600"
          >
            Analyzing table columns to suggest chart types...
          </div>

          <p
            v-else-if="chartSuggestionError"
            class="mt-5 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
          >
            {{ chartSuggestionError }}
          </p>

          <div
            v-else-if="chartSuggestions.length"
            class="mt-5 grid gap-4 md:grid-cols-2"
          >
            <button
              v-for="suggestion in chartSuggestions"
              :key="getSuggestionKey(suggestion)"
              type="button"
              class="rounded-3xl border p-5 text-left transition"
              :class="
                selectedSuggestionKey === getSuggestionKey(suggestion)
                  ? 'border-brand-400 bg-brand-50/80 shadow-sm'
                  : 'border-slate-200/80 bg-white hover:border-brand-300 hover:bg-brand-50/40'
              "
              @click="selectedSuggestionKey = getSuggestionKey(suggestion)"
            >
              <div class="flex items-center justify-between gap-3">
                <h3 class="font-heading text-xl font-semibold text-slate-900">{{ suggestion.title }}</h3>
                <span class="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
                  {{ suggestion.type }}
                </span>
              </div>
              <p class="mt-3 text-sm text-slate-600">{{ suggestion.reason }}</p>
              <p class="mt-4 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                X: {{ suggestion.x_column }} | Y: {{ suggestion.y_column }}
              </p>
            </button>
          </div>

          <div v-if="chartSuggestions.length" class="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              class="rounded-2xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!selectedSuggestionKey || isRenderingChart"
              @click="onRenderSelectedChart"
            >
              {{ isRenderingChart ? "Rendering Chart..." : "Render Selected Chart" }}
            </button>
            <p class="text-sm text-slate-500">
              Azure OpenAI selects the chart option and Chart.js MCP renders the final chart.
            </p>
          </div>

          <div
            v-else
            class="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
          >
            {{ canChart ? "No chart options returned." : "This result is not suitable for a chart suggestion yet." }}
          </div>

          <p
            v-if="chartRenderError"
            class="mt-5 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
          >
            {{ chartRenderError }}
          </p>

          <div v-if="renderedChart" class="mt-6 space-y-4">
            <div
              v-if="renderedChart.html_snippet"
              class="overflow-hidden rounded-3xl border border-slate-200/80 bg-white shadow-sm"
            >
              <iframe
                :srcdoc="renderedChart.html_snippet"
                title="Rendered Chart"
                class="h-[560px] w-full border-0"
                sandbox="allow-scripts"
                referrerpolicy="no-referrer"
              />
            </div>
            <SimpleChart v-else :chart="renderedChart" />
          </div>
        </section>
      </transition>

      <transition name="fade-up">
        <p
          v-if="error"
          class="mt-5 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
        >
          {{ error }}
        </p>
      </transition>
    </div>
  </main>
</template>

<style scoped>
.fade-up-enter-active,
.fade-up-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
