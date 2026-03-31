<script setup>
import { computed, ref, watch } from "vue";

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

const emit = defineEmits(["view-chart"]);

const allRows = ref([]);
const sortKey = ref("");
const sortDirection = ref("asc");
const currentPage = ref(1);
const pageSize = ref(10);

const formatColumnLabel = (name) => {
  if (!name) return "";
  return String(name)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const columns = computed(() => props.result?.columns || []);

watch(
  () => props.result,
  (value) => {
    const nextRows = Array.isArray(value?.rows) ? value.rows : [];
    allRows.value = [...nextRows];
    currentPage.value = 1;
  },
  { immediate: true },
);

watch(
  columns,
  (nextColumns) => {
    if (!nextColumns.length) {
      sortKey.value = "";
      return;
    }

    if (!nextColumns.includes(sortKey.value)) {
      sortKey.value = nextColumns[0];
      sortDirection.value = "asc";
    }
  },
  { immediate: true },
);

watch(pageSize, () => {
  currentPage.value = 1;
});

const compareValues = (leftValue, rightValue) => {
  const toComparable = (value) => {
    if (value === null || value === undefined) return "";
    if (typeof value === "number") return value;
    if (typeof value === "string") {
      const numeric = Number(value);
      if (value.trim() !== "" && Number.isFinite(numeric)) return numeric;
      return value.toLowerCase();
    }
    return String(value).toLowerCase();
  };

  const left = toComparable(leftValue);
  const right = toComparable(rightValue);

  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }

  return String(left).localeCompare(String(right), undefined, {
    numeric: true,
    sensitivity: "base",
  });
};

const sortedRows = computed(() => {
  if (!sortKey.value) return [...allRows.value];

  const sorted = [...allRows.value];
  sorted.sort((leftRow, rightRow) => {
    const result = compareValues(leftRow?.[sortKey.value], rightRow?.[sortKey.value]);
    return sortDirection.value === "asc" ? result : -result;
  });
  return sorted;
});

const totalRows = computed(() => sortedRows.value.length);
const totalPages = computed(() => {
  if (!totalRows.value) return 1;
  return Math.ceil(totalRows.value / pageSize.value);
});

watch(totalPages, (value) => {
  if (currentPage.value > value) {
    currentPage.value = value;
  }
});

const paginatedRows = computed(() => {
  const startIndex = (currentPage.value - 1) * pageSize.value;
  const endIndex = startIndex + pageSize.value;
  return sortedRows.value.slice(startIndex, endIndex);
});

const rangeStart = computed(() => {
  if (!totalRows.value) return 0;
  return (currentPage.value - 1) * pageSize.value + 1;
});

const rangeEnd = computed(() => {
  if (!totalRows.value) return 0;
  return Math.min(currentPage.value * pageSize.value, totalRows.value);
});

const totalResultRows = computed(() => {
  const value = props.result?.rowCount;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return allRows.value.length;
});

const toggleSort = (column) => {
  if (sortKey.value === column) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
    return;
  }
  sortKey.value = column;
  sortDirection.value = "asc";
  currentPage.value = 1;
};

const goToPreviousPage = () => {
  if (currentPage.value <= 1) return;
  currentPage.value -= 1;
};

const goToNextPage = () => {
  if (currentPage.value >= totalPages.value) return;
  currentPage.value += 1;
};

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
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-700"
          @click="emit('view-chart')"
        >
          View Chart
        </button>
        <p class="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-800">
          {{ totalResultRows }} rows | {{ durationText }} ms
        </p>
      </div>
    </div>

    <div class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/70 bg-white/80 px-3 py-2">
      <p class="text-sm text-slate-600">Showing {{ rangeStart }} - {{ rangeEnd }} of {{ totalRows }} rows</p>
      <label class="inline-flex items-center gap-2 text-sm text-slate-600">
        Rows per page
        <select
          v-model.number="pageSize"
          class="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 outline-none focus:border-brand-500"
        >
          <option :value="5">5</option>
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
        </select>
      </label>
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
              <button
                type="button"
                class="inline-flex items-center gap-2 transition hover:text-brand-200"
                @click="toggleSort(column)"
              >
                <span>{{ formatColumnLabel(column) }}</span>
                <span v-if="sortKey === column" class="text-xs">
                  {{ sortDirection === "asc" ? "▲" : "▼" }}
                </span>
                <span v-else class="text-[10px] text-slate-400">↕</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody class="bg-white/70 text-slate-700">
          <tr
            v-for="(row, rowIndex) in paginatedRows"
            :key="`${currentPage}-${rowIndex}`"
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

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Page {{ currentPage }} / {{ totalPages }}</p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition hover:border-brand-400 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-45"
          :disabled="currentPage <= 1"
          @click="goToPreviousPage"
        >
          Previous
        </button>
        <button
          type="button"
          class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 transition hover:border-brand-400 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-45"
          :disabled="currentPage >= totalPages"
          @click="goToNextPage"
        >
          Next
        </button>
      </div>
    </div>

    <p
      v-if="!allRows.length && !loading"
      class="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
    >
      No rows returned for this query.
    </p>
  </section>
</template>
