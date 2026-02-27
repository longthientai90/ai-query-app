import { createRouter, createWebHistory } from "vue-router";
import HomePage from "../pages/HomePage.vue";
import AiSearchPage from "../pages/AiSearchPage.vue";
import InsightsPage from "../pages/InsightsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomePage,
    },
    {
      path: "/ai-search",
      name: "ai-search",
      component: AiSearchPage,
    },
    {
      path: "/insights",
      name: "insights",
      component: InsightsPage,
    },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
