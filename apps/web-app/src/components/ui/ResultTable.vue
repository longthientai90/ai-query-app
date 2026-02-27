<script setup>
import { computed } from "vue";

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const formatColumnLabel = (name) => {
  if (!name) return "";
  return String(name)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const rows = computed(() => props.result?.rows || []);
const columns = computed(() => props.result?.columns || []);

const durationText = computed(() => {
  const value = props.result?.durationMs;
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return value.toFixed(2);
});
</script>

<template>
  <section class="animate-rise rounded-3xl border border-white/70 bg-white/75 p-5 shadow-card backdrop-blur-xl sm:p-6">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h2 class="font-heading text-xl font-semibold text-slate-800">Query Result</h2>
      <p class="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-800">
        {{ result.rowCount }} rows · {{ durationText }} ms
      </p>
    </div>

    <div class="overflow-x-auto rounded-2xl border border-slate-200/70">
      <table class="min-w-full border-collapse text-left">
        <thead class="bg-slate-900 text-sm uppercase tracking-wide text-slate-100">
          <tr>
            <th
              v-for="column in columns"
              :key="column"
              class="px-4 py-3 font-semibold"
            >
              {{ formatColumnLabel(column) }}
            </th>
          </tr>
        </thead>
        <tbody class="bg-white/70 text-slate-700">
          <tr
            v-for="(row, rowIndex) in rows"
            :key="rowIndex"
            class="border-b border-slate-200/80 transition hover:bg-brand-50/70"
          >
            <td
              v-for="column in columns"
              :key="`${rowIndex}-${column}`"
              class="px-4 py-3 align-top"
            >
              {{ row?.[column] ?? "-" }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p
      v-if="!rows.length && !loading"
      class="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
    >
      No rows returned for this query.
    </p>
  </section>
</template>
