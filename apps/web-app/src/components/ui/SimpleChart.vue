<script setup>
import { computed } from "vue";

const props = defineProps({
  chart: {
    type: Object,
    required: true,
  },
});

const width = 760;
const height = 320;
const padding = { top: 24, right: 24, bottom: 72, left: 56 };

const points = computed(() => (Array.isArray(props.chart?.points) ? props.chart.points : []));
const maxValue = computed(() => {
  const values = points.value.map((point) => Number(point.value) || 0);
  return Math.max(1, ...values);
});

const barMetrics = computed(() => {
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const count = Math.max(points.value.length, 1);
  const step = innerWidth / count;
  const barWidth = Math.min(64, step * 0.62);

  return points.value.map((point, index) => {
    const x = padding.left + step * index + (step - barWidth) / 2;
    const barHeight = (Number(point.value) / maxValue.value) * innerHeight;
    const y = padding.top + innerHeight - barHeight;
    return {
      ...point,
      x,
      y,
      width: barWidth,
      height: barHeight,
      labelX: padding.left + step * index + step / 2,
    };
  });
});

const lineMetrics = computed(() => {
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const count = Math.max(points.value.length - 1, 1);

  return points.value.map((point, index) => {
    const x = padding.left + (innerWidth / count) * index;
    const y = padding.top + innerHeight - (Number(point.value) / maxValue.value) * innerHeight;
    return {
      ...point,
      x,
      y,
    };
  });
});

const linePath = computed(() => {
  if (!lineMetrics.value.length) {
    return "";
  }

  return lineMetrics.value
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
});

const yAxisLabels = computed(() => {
  const ticks = 4;
  const innerHeight = height - padding.top - padding.bottom;
  return Array.from({ length: ticks + 1 }, (_, index) => {
    const value = maxValue.value * (1 - index / ticks);
    const y = padding.top + (innerHeight / ticks) * index;
    return {
      value,
      y,
    };
  });
});

const formatTick = (value) => {
  if (Math.abs(value) >= 1000) {
    return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);
  }
  return Number(value).toFixed(value % 1 === 0 ? 0 : 1);
};

const truncateLabel = (value) => {
  const label = String(value ?? "");
  return label.length > 16 ? `${label.slice(0, 13)}...` : label;
};
</script>

<template>
  <div class="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="font-heading text-2xl font-semibold text-slate-900">{{ chart.title }}</h3>
        <p class="mt-1 text-sm text-slate-600">{{ chart.summary }}</p>
      </div>
      <span class="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
        {{ chart.chart_type }}
      </span>
    </div>

    <div class="overflow-x-auto">
      <svg :viewBox="`0 0 ${width} ${height}`" class="min-w-[760px]">
        <g>
          <line
            v-for="tick in yAxisLabels"
            :key="tick.y"
            :x1="padding.left"
            :x2="width - padding.right"
            :y1="tick.y"
            :y2="tick.y"
            stroke="#d8e1ef"
            stroke-dasharray="4 6"
          />
          <text
            v-for="tick in yAxisLabels"
            :key="`${tick.y}-label`"
            :x="padding.left - 12"
            :y="tick.y + 4"
            text-anchor="end"
            font-size="12"
            fill="#64748b"
          >
            {{ formatTick(tick.value) }}
          </text>
        </g>

        <g v-if="chart.chart_type === 'bar'">
          <rect
            v-for="point in barMetrics"
            :key="point.label"
            :x="point.x"
            :y="point.y"
            :width="point.width"
            :height="point.height"
            rx="10"
            fill="url(#barGradient)"
          />
          <text
            v-for="point in barMetrics"
            :key="`${point.label}-value`"
            :x="point.labelX"
            :y="point.y - 8"
            text-anchor="middle"
            font-size="12"
            fill="#0f172a"
          >
            {{ formatTick(point.value) }}
          </text>
          <text
            v-for="point in barMetrics"
            :key="`${point.label}-label`"
            :x="point.labelX"
            :y="height - 32"
            text-anchor="middle"
            font-size="12"
            fill="#475569"
          >
            {{ truncateLabel(point.label) }}
          </text>
        </g>

        <g v-else>
          <path :d="linePath" fill="none" stroke="#0f766e" stroke-linecap="round" stroke-linejoin="round" stroke-width="4" />
          <circle
            v-for="point in lineMetrics"
            :key="point.label"
            :cx="point.x"
            :cy="point.y"
            r="5"
            fill="#14b8a6"
            stroke="#ecfeff"
            stroke-width="3"
          />
          <text
            v-for="point in lineMetrics"
            :key="`${point.label}-value`"
            :x="point.x"
            :y="point.y - 12"
            text-anchor="middle"
            font-size="12"
            fill="#0f172a"
          >
            {{ formatTick(point.value) }}
          </text>
          <text
            v-for="point in lineMetrics"
            :key="`${point.label}-label`"
            :x="point.x"
            :y="height - 32"
            text-anchor="middle"
            font-size="12"
            fill="#475569"
          >
            {{ truncateLabel(point.label) }}
          </text>
        </g>

        <line :x1="padding.left" :x2="padding.left" :y1="padding.top" :y2="height - padding.bottom" stroke="#94a3b8" />
        <line
          :x1="padding.left"
          :x2="width - padding.right"
          :y1="height - padding.bottom"
          :y2="height - padding.bottom"
          stroke="#94a3b8"
        />

        <defs>
          <linearGradient id="barGradient" x1="0%" x2="0%" y1="0%" y2="100%">
            <stop offset="0%" stop-color="#14b8a6" />
            <stop offset="100%" stop-color="#0f766e" />
          </linearGradient>
        </defs>
      </svg>
    </div>

    <div class="mt-4 flex flex-wrap gap-3 text-sm text-slate-600">
      <p>X-axis: <span class="font-medium text-slate-900">{{ chart.x_column }}</span></p>
      <p>Y-axis: <span class="font-medium text-slate-900">{{ chart.y_column }}</span></p>
    </div>
  </div>
</template>
