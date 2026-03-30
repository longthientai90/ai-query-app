<script setup>
import { computed } from "vue";
import { clearSearchMetrics, useInsights } from "../composables/useInsights";

const {
  entries,
  totalQueries,
  successfulQueries,
  totalRowsReturned,
  averageRowsReturned,
  averageResponseTimeMs,
  maxResponseTimeMs,
} = useInsights();

const cards = computed(() => [
  {
    label: "Query Volume",
    value: totalQueries.value,
    helper: `${successfulQueries.value} successful queries`,
  },
  {
    label: "Avg Response Time",
    value: `${averageResponseTimeMs.value.toFixed(2)} ms`,
    helper: `Slowest query ${maxResponseTimeMs.value.toFixed(2)} ms`,
  },
  {
    label: "Rows Returned",
    value: totalRowsReturned.value,
    helper: "Total rows from successful queries",
  },
  {
    label: "Avg Rows / Query",
    value: averageRowsReturned.value.toFixed(1),
    helper: "Average rows per successful query",
  },
]);

const recentEntries = computed(() => entries.value.slice(0, 10));

const formatTime = (isoString) => {
  if (!isoString) {
    return "n/a";
  }

  const parsedTime = new Date(isoString);
  if (Number.isNaN(parsedTime.getTime())) {
    return "n/a";
  }

  return parsedTime.toLocaleString();
};
</script>

<template>
  <main class="px-4 py-10 sm:px-8 lg:py-14">
    <div class="mx-auto max-w-6xl">
      <section class="rounded-[2rem] border border-white/70 bg-white/80 p-8 shadow-card backdrop-blur-xl">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p
              class="mb-2 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600"
            >
              Insights
            </p>
            <h1 class="font-heading text-3xl font-bold text-slate-900">Search Insights</h1>
            <p class="mt-3 max-w-2xl text-slate-600">
              Track query volume and search performance from recent activity in this browser.
            </p>
          </div>

          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
            @click="clearSearchMetrics"
          >
            Clear History
          </button>
        </div>

        <section class="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article
            v-for="card in cards"
            :key="card.label"
            class="rounded-3xl border border-slate-200/80 bg-gradient-to-br from-white to-slate-50 p-5 shadow-sm"
          >
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">{{ card.label }}</p>
            <p class="mt-4 font-heading text-3xl font-bold text-slate-900">{{ card.value }}</p>
            <p class="mt-2 text-sm text-slate-600">{{ card.helper }}</p>
          </article>
        </section>

        <section class="mt-8 rounded-3xl border border-slate-200/80 bg-white/85 shadow-sm">
          <div class="flex items-center justify-between border-b border-slate-200/80 px-5 py-4">
            <div>
              <h2 class="font-heading text-xl font-semibold text-slate-900">Recent Queries</h2>
              <p class="mt-1 text-sm text-slate-600">Latest executions with response time and returned rows.</p>
            </div>
          </div>

          <div v-if="recentEntries.length" class="overflow-x-auto">
            <table class="min-w-full border-collapse text-left">
              <thead class="bg-slate-900 text-xs uppercase tracking-[0.2em] text-slate-100">
                <tr>
                  <th class="px-5 py-4 font-semibold">Time</th>
                  <th class="px-5 py-4 font-semibold">Query</th>
                  <th class="px-5 py-4 font-semibold">Status</th>
                  <th class="px-5 py-4 font-semibold">Response</th>
                  <th class="px-5 py-4 font-semibold">Rows</th>
                </tr>
              </thead>
              <tbody class="bg-white/80 text-sm text-slate-700">
                <tr
                  v-for="entry in recentEntries"
                  :key="entry.id"
                  class="border-b border-slate-200/80 align-top"
                >
                  <td class="px-5 py-4 text-slate-500">{{ formatTime(entry.createdAt) }}</td>
                  <td class="px-5 py-4">
                    <p class="font-medium text-slate-900">{{ entry.question }}</p>
                    <p v-if="entry.errorMessage" class="mt-1 text-xs text-red-600">{{ entry.errorMessage }}</p>
                  </td>
                  <td class="px-5 py-4">
                    <span
                      class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide"
                      :class="
                        entry.status === 'success'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                      "
                    >
                      {{ entry.status }}
                    </span>
                  </td>
                  <td class="px-5 py-4">{{ entry.durationMs === null ? "n/a" : `${entry.durationMs.toFixed(2)} ms` }}</td>
                  <td class="px-5 py-4">{{ entry.rowCount }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-else
            class="px-5 py-12 text-center text-sm text-slate-500"
          >
            No query activity yet. Run a search from AI Search to start collecting insights.
          </div>
        </section>
      </section>
    </div>
  </main>
</template>
