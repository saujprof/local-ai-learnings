<template>
  <article class="chat-message" :class="`message-${message.role}`" :aria-label="message.role === 'user' ? 'Your question' : 'Assistant answer'">
    <p class="message-author">{{ message.role === 'user' ? 'You' : 'Assistant' }}</p>
    <p class="message-content">{{ message.content }}</p>
    <SourceList v-if="message.sources" :sources="message.sources" />
  </article>
</template>

<script setup lang="ts">
import type { ChatMessage } from '../types/chat'
import SourceList from './SourceList.vue'
defineProps<{ message: ChatMessage }>()
</script>
