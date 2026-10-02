<template>
  <div v-if="sources.length" class="sources">
    <p class="sources-label">Sources</p>
    <ul>
      <li v-for="(source, index) in sources" :key="`${source.document_id}-${source.page_start}-${source.page_end}-${index}`">
        {{ source.document_name }} —
        {{ source.page_start === source.page_end ? `Page ${source.page_start}` : `Pages ${source.page_start}–${source.page_end}` }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { Source } from '../types/chat'
defineProps<{ sources: Source[] }>()
</script>
