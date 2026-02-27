<script setup>
import { ref } from "vue";

defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit"]);

const question = ref("");

const submit = () => {
  emit("submit", question.value);
};
</script>

<template>
  <form
    class="rounded-3xl border border-white/60 bg-white/75 p-4 shadow-card backdrop-blur-xl transition hover:shadow-glow sm:p-6"
    @submit.prevent="submit"
  >
    <label for="search-input" class="mb-3 block font-heading text-lg font-semibold text-slate-800">
      Ask your data anything
    </label>
    <div class="flex flex-col gap-4 sm:flex-row">
      <textarea
        id="search-input"
        v-model="question"
        rows="3"
        placeholder="Example: Top 5 products with highest price in 2024"
        class="min-h-[120px] w-full resize-y rounded-2xl border border-brand-200 bg-white/95 px-4 py-3 text-base text-slate-800 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
        @keydown.enter.exact.prevent="submit"
      />
      <button
        type="submit"
        :disabled="loading"
        class="inline-flex min-w-[140px] items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-500 px-6 py-3 font-heading font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:-translate-y-0.5 hover:from-brand-500 hover:to-brand-400 disabled:cursor-not-allowed disabled:opacity-70"
      >
        <span
          v-if="loading"
          class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
        />
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          class="h-4 w-4"
          aria-hidden="true"
        >
          <path
            d="M3.478 2.405a.75.75 0 0 1 .798-.107l17.25 7.5a.75.75 0 0 1 0 1.374l-17.25 7.5A.75.75 0 0 1 3.22 18V13.5A.75.75 0 0 1 3.97 12.75h7.5a.75.75 0 0 0 0-1.5h-7.5a.75.75 0 0 1-.75-.75V3a.75.75 0 0 1 .258-.595Z"
          />
        </svg>
        <span>{{ loading ? "Searching..." : "Search" }}</span>
      </button>
    </div>
    <p class="mt-2 text-xs text-slate-500">Press Enter to submit quickly.</p>
  </form>
</template>
