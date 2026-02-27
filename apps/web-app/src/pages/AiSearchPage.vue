<script setup>
import { ref } from "vue";
import SearchBar from "../components/ui/SearchBar.vue";
import ResultTable from "../components/ui/ResultTable.vue";
import { useSearch } from "../composables/useSearch";

const { isSearching, error, runSearch } = useSearch();
const tableResult = ref(null);

const onSubmit = async (question) => {
  tableResult.value = await runSearch(question);
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
        />
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
