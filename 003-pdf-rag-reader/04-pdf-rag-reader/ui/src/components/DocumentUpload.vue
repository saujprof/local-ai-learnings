<template>
  <div class="document-upload">
    <label for="pdf-upload">Upload PDF</label>
    <input id="pdf-upload" type="file" accept=".pdf,application/pdf" :disabled="uploading" @change="selectFile" />
    <p role="status">{{ uploading ? 'Uploading PDF…' : 'Choose one PDF at a time.' }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ uploading: boolean }>()
const emit = defineEmits<{ upload: [file: File] }>()

function selectFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('upload', file)
  input.value = ''
}
</script>

