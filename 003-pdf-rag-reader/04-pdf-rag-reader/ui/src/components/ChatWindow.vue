<template>
  <div ref="viewport" class="chat-window" role="log" aria-label="Conversation" aria-live="polite" tabindex="0">
    <div v-if="!messages.length" class="empty-state chat-empty-state">
      <span class="empty-symbol" aria-hidden="true">?</span>
      <h3>Start with a question</h3>
      <p>Once a PDF is ready, ask about its contents. Answers and PDF page references will appear here.</p>
    </div>
    <ChatMessage v-for="message in messages" :key="message.id" :message="message" />
    <p v-if="sending" class="chat-waiting" role="status">Preparing an answer…</p>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage as Message } from '../types/chat'
import ChatMessage from './ChatMessage.vue'
const props = defineProps<{ messages: Message[]; sending: boolean }>()
const viewport = ref<HTMLDivElement | null>(null)
watch(() => [props.messages.length, props.sending], async () => {
  await nextTick()
  if (viewport.value) viewport.value.scrollTop = viewport.value.scrollHeight
})
</script>
