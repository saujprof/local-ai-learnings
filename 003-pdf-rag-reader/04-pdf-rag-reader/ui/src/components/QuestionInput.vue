<template>
  <form class="question-form" @submit.prevent="$emit('send')">
    <label for="question">Your question</label>
    <textarea id="question" :value="modelValue" :disabled="sending || !canSend" rows="3" maxlength="10000"
      placeholder="Ask about your PDFs…" aria-describedby="question-help"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" />
    <div class="question-actions">
      <p id="question-help">{{ canSend ? 'Casual messages work directly. Document answers include PDF sources.' : 'Chat history must load first. Resolve any errors above to continue.' }}</p>
      <button type="submit" :disabled="sending || !canSend || !modelValue.trim()">{{ sending ? 'Sending…' : 'Send' }}</button>
    </div>
  </form>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string; sending: boolean; canSend: boolean }>()
defineEmits<{ 'update:modelValue': [value: string]; send: [] }>()
</script>
