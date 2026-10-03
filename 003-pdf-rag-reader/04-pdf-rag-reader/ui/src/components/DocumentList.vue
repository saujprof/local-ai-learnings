<template>
  <p v-if="loading" class="empty-state" role="status">Loading documents…</p>
  <div v-else-if="!documents.length" class="empty-state">
    <h3>No documents yet</h3>
    <p>Upload a PDF to get started.</p>
  </div>
  <ul v-else class="document-list" aria-label="Uploaded documents" aria-live="polite">
    <li v-for="document in documents" :key="document.id" class="document-row">
      <div class="document-details">
        <p class="document-name">{{ document.name }}</p>
        <span class="document-status" :class="`status-${deletingIds.has(document.id) ? 'deleting' : document.status}`">
          {{ labels[deletingIds.has(document.id) ? 'deleting' : document.status] }}
        </span>
        <p v-if="document.error" class="document-error">{{ document.error }}</p>
      </div>
      <button type="button" :disabled="deletingIds.has(document.id) || document.status === 'deleting'"
        :aria-label="`Delete ${document.name}`" @click="$emit('delete', document.id)">
        {{ deletingIds.has(document.id) || document.status === 'deleting' ? 'Deleting…' : 'Delete' }}
      </button>
    </li>
  </ul>
</template>

<script setup lang="ts">
import type { PdfDocument, DocumentStatus } from '../types/document'
defineProps<{ documents: PdfDocument[]; deletingIds: Set<string>; loading: boolean }>()
defineEmits<{ delete: [id: string] }>()
const labels: Record<DocumentStatus, string> = {
  processing: 'Processing', ready: 'Ready', failed: 'Failed', deleting: 'Deleting',
}
</script>

