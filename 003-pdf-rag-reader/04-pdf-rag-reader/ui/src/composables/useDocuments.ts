import { onMounted, onUnmounted, ref } from 'vue'
import { deleteDocument, listDocuments, uploadDocument } from '../services/api'
import type { PdfDocument } from '../types/document'

export function useDocuments() {
  const documents = ref<PdfDocument[]>([])
  const loading = ref(true)
  const uploading = ref(false)
  const error = ref('')
  const deletingIds = ref(new Set<string>())
  let timer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  let revision = 0

  function scheduleRefresh() {
    clearTimeout(timer)
    if (!disposed && documents.value.some((document) => document.status === 'processing')) {
      timer = setTimeout(refresh, 1000)
    }
  }

  async function refresh() {
    clearTimeout(timer)
    const startedAt = revision
    try {
      const result = await listDocuments()
      // An upload or deletion may have completed while this request was pending.
      if (!disposed && startedAt === revision) documents.value = result
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Could not load documents.'
    } finally {
      loading.value = false
      scheduleRefresh()
    }
  }

  async function upload(file: File) {
    if (uploading.value) return
    uploading.value = true
    error.value = ''
    try {
      const document = await uploadDocument(file)
      revision++
      documents.value.unshift(document)
      scheduleRefresh()
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Upload failed. Try again.'
    } finally {
      uploading.value = false
    }
  }

  async function remove(id: string) {
    if (deletingIds.value.has(id)) return
    deletingIds.value.add(id)
    error.value = ''
    try {
      await deleteDocument(id)
      revision++
      documents.value = documents.value.filter((document) => document.id !== id)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Deletion failed. Try again.'
    } finally {
      deletingIds.value.delete(id)
      scheduleRefresh()
    }
  }

  onMounted(refresh)
  onUnmounted(() => {
    disposed = true
    clearTimeout(timer)
  })

  return { documents, loading, uploading, deletingIds, error, upload, remove }
}
