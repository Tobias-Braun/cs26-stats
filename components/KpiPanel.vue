<script setup lang="ts">
defineProps<{
  idx: string
  label: string
  hot?: boolean
  class?: string
}>()
</script>

<template>
  <div class="panel" :class="[$props.class, { hot }]">
    <span class="corner tl" />
    <span class="corner tr" />
    <span class="corner bl" />
    <span class="corner br" />

    <div class="k-label">
      <span class="ix">{{ idx }}</span>
      {{ label }}
    </div>

    <slot />
  </div>
</template>
