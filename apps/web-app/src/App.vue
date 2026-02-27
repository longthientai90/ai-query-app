<script setup>
import { RouterView } from "vue-router";
import AppMenu from "./components/layout/AppMenu.vue";
</script>

<template>
  <div class="min-h-screen">
    <AppMenu />
    <RouterView />
  </div>
</template>
