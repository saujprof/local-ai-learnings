<template>
  <div ref="viewport" class="chat-window" role="log" aria-label="Conversation" aria-live="polite" tabindex="0" @scroll="onScroll">
    <div class="history-controls">
      <p v-if="loadingHistory" role="status">Loading messages…</p>
      <template v-else-if="historyError">
        <p role="alert">{{ historyError }}</p>
        <button type="button" :disabled="sending" @click="$emit('loadOlder')">Retry history</button>
      </template>
      <button v-else-if="hasMore" type="button" :disabled="sending" @click="$emit('loadOlder')">Load older messages</button>
      <p v-else-if="historyReady && messages.length">Beginning of conversation</p>
    </div>
    <div v-if="historyReady && !messages.length" class="empty-state chat-empty-state">
      <span class="empty-symbol" aria-hidden="true">?</span>
      <h3>Start with a question</h3>
      <p>Once a PDF is ready, ask about its contents. Answers and PDF page references will appear here.</p>
    </div>
    <div v-for="message in messages" :key="message.id" :data-message-id="message.id">
      <ChatMessage :message="message" />
    </div>
    <p v-if="sending" class="chat-waiting" role="status">Preparing an answer…</p>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage as Message } from '../types/chat'
import ChatMessage from './ChatMessage.vue'
const props = defineProps<{
  messages: Message[]; sending: boolean; loadingHistory: boolean
  historyReady: boolean; hasMore: boolean; historyError: string
}>()
const emit = defineEmits<{ loadOlder: [] }>()
const viewport = ref<HTMLDivElement | null>(null)
let adjusting = false
function onScroll() {
  if (!adjusting && viewport.value && viewport.value.scrollTop <= 24 && props.hasMore && !props.loadingHistory && !props.historyError && !props.sending) {
    emit('loadOlder')
  }
}
watch(() => [props.messages.length, props.sending, props.loadingHistory], async () => {
  const element = viewport.value
  if (!element) return
  // Capture a visible message before DOM updates, including changes to the loader.
  const anchor = Array.from(element.querySelectorAll<HTMLElement>('[data-message-id]'))
    .find((node) => node.getBoundingClientRect().bottom > element.getBoundingClientRect().top)
  const top = anchor?.getBoundingClientRect().top
  const nearBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 80
  adjusting = true
  await nextTick()
  if (anchor && top !== undefined && !nearBottom) {
    element.scrollTop += anchor.getBoundingClientRect().top - top
  } else {
    element.scrollTop = element.scrollHeight
  }
  requestAnimationFrame(() => { adjusting = false })
})
</script>
