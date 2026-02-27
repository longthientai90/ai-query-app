<script setup>
const cards = [
  {
    title: "AI Search",
    description: "Search your data using natural language and view dynamic tabular results.",
    to: "/ai-search",
    cta: "Open AI Search",
  },
  {
    title: "Insights",
    description: "Track query behavior and usage metrics with summary dashboards.",
    to: "/insights",
    cta: "View Insights",
  },
];
</script>

<template>
  <main class="px-4 py-10 sm:px-8 lg:py-14">
    <div class="mx-auto max-w-6xl">
      <section class="mb-8 rounded-3xl border border-white/70 bg-white/70 p-6 shadow-card backdrop-blur-xl sm:p-8">
        <p class="mb-3 inline-flex rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-brand-700">
          Home
        </p>
        <h1 class="font-heading text-3xl font-bold text-slate-900 sm:text-4xl">
          Query Platform Workspace
        </h1>
        <p class="mt-3 max-w-3xl text-slate-600">
          Each feature is an independent page, organized by functional domain. Choose a module below to get started.
        </p>
      </section>

      <section class="grid gap-5 md:grid-cols-2">
        <article
          v-for="card in cards"
          :key="card.to"
          class="group rounded-3xl border border-white/70 bg-white/80 p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-glow"
        >
          <h2 class="font-heading text-2xl font-semibold text-slate-900">{{ card.title }}</h2>
          <p class="mt-3 text-slate-600">{{ card.description }}</p>
          <RouterLink
            :to="card.to"
            class="mt-6 inline-flex items-center rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            {{ card.cta }}
          </RouterLink>
        </article>
      </section>
    </div>
  </main>
</template>
