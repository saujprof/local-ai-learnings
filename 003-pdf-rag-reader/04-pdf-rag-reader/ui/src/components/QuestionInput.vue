<template>
  <form class="question-form" @submit.prevent="$emit('send')">
    <label for="question">Your question</label>
    <textarea id="question" :value="modelValue" :disabled="sending || !canSend" rows="3"
      placeholder="Ask about your PDFs…" aria-describedby="question-help"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" />
    <div class="question-actions">
      <p id="question-help">{{ canSend ? 'Answers and citations are simulated in demo mode.' : 'Upload a PDF and wait until it is ready to ask questions.' }}</p>
      <button type="submit" :disabled="sending || !canSend || !modelValue.trim()">{{ sending ? 'Sending…' : 'Send' }}</button>
    </div>
  </form>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string; sending: boolean; canSend: boolean }>()
defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()
</script>
