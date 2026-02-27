<script setup>
const links = [
  { label: "Home", to: "/" },
  { label: "AI Search", to: "/ai-search" },
  { label: "Insights", to: "/insights" },
];
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-white/60 bg-white/65 backdrop-blur-xl">
    <nav class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-8">
      <RouterLink to="/" class="font-heading text-lg font-bold text-slate-900">
        AI Query App
      </RouterLink>

      <ul class="flex items-center gap-1 rounded-full border border-slate-200/80 bg-white/80 p-1 shadow-sm">
        <li v-for="link in links" :key="link.to">
          <RouterLink
            :to="link.to"
            class="inline-flex rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-brand-700"
            exact-active-class="bg-brand-100 text-brand-800"
          >
            {{ link.label }}
          </RouterLink>
        </li>
      </ul>
    </nav>
  </header>
</template>
