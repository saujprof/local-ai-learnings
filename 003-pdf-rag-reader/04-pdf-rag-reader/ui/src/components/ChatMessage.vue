<template>
  <article class="chat-message" :class="`message-${message.role}`" :aria-label="message.role === 'user' ? 'Your question' : 'Assistant answer'">
    <p class="message-author">{{ message.role === 'user' ? 'You' : 'Assistant' }}</p>
    <div v-if="message.role === 'assistant'" class="message-content markdown-content" v-html="renderedContent" />
    <p v-else class="message-content">{{ message.content }}</p>
    <SourceList v-if="message.sources" :sources="message.sources" />
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import type { ChatMessage } from '../types/chat'
import SourceList from './SourceList.vue'
const props = defineProps<{ message: ChatMessage }>()
const renderedContent = computed(() => props.message.role === 'assistant' ? renderMarkdown(props.message.content) : '')
</script>
