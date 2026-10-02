<template>
  <div class="app-shell">
    <header class="app-header">
      <p class="eyebrow">PDF RAG Reader</p>
      <h1>Ask your documents.</h1>
      <p>Find answers in your PDFs, with sources you can trace.</p>
    </header>

    <main class="workspace">
      <section class="panel documents-panel" aria-labelledby="documents-title">
        <header class="panel-header">
          <h2 id="documents-title">Documents</h2>
          <p>Your PDFs provide the context for each answer.</p>
        </header>
        <p class="mock-notice">Demo mode · PDFs are simulated and cleared on reload.</p>
        <DocumentUpload :uploading="uploading" @upload="upload" />
        <p v-if="error" class="document-error api-error" role="alert">{{ error }}</p>
        <DocumentList :documents="documents" :loading="loading" :deleting-ids="deletingIds" @delete="remove" />
      </section>

      <section class="panel chat-panel" aria-labelledby="chat-title">
        <header class="panel-header">
          <h2 id="chat-title">Chat</h2>
          <p>Explore your documents one question at a time.</p>
        </header>
        <div class="empty-state chat-empty-state">
          <span class="empty-symbol" aria-hidden="true">?</span>
          <h3>Start with a question</h3>
          <p>Once a PDF is ready, ask about its contents. Answers and PDF page references will appear here.</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import DocumentUpload from './components/DocumentUpload.vue'
import DocumentList from './components/DocumentList.vue'
import { useDocuments } from './composables/useDocuments'

const { documents, loading, uploading, deletingIds, error, upload, remove } = useDocuments()
</script>

