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
        <ChatWindow :messages="messages" :sending="sending" />
        <p v-if="chatError" class="document-error api-error" role="alert">{{ chatError }}</p>
        <QuestionInput v-model="question" :sending="sending" :can-send="canSend" @send="sendIfReady" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ChatWindow from './components/ChatWindow.vue'
import QuestionInput from './components/QuestionInput.vue'
import { useChat } from './composables/useChat'
import DocumentUpload from './components/DocumentUpload.vue'
import DocumentList from './components/DocumentList.vue'
import { useDocuments } from './composables/useDocuments'

const { documents, loading, uploading, deletingIds, error, upload, remove } = useDocuments()
const { messages, question, sending, error: chatError, send } = useChat()
const canSend = computed(() => documents.value.some((document) => document.status === 'ready' && !deletingIds.value.has(document.id)))
function sendIfReady() {
  if (canSend.value) void send()
}
</script>

