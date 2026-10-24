import { onMounted, onUnmounted, ref } from 'vue'
import { deleteDocument, listDocuments, uploadDocument } from '../services/api'
import type { PdfDocument } from '../types/document'

export function useDocuments() {
  const documents = ref<PdfDocument[]>([])
  const loading = ref(true)
  const uploading = ref(false)
  const error = ref('')
  const refreshError = ref('')
  const refreshing = ref(false)
  const deletingIds = ref(new Set<string>())
  let timer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  let revision = 0

  function scheduleRefresh() {
    clearTimeout(timer)
    if (!disposed && documents.value.some((document) => document.status === 'processing' || document.status === 'deleting')) {
      timer = setTimeout(refresh, 3000)
    }
  }

  async function refresh() {
    if (disposed || refreshing.value) return
    refreshing.value = true
    refreshError.value = ''
    clearTimeout(timer)
    const startedAt = revision
    try {
      const result = await listDocuments()
      // An upload or deletion may have completed while this request was pending.
      if (!disposed && startedAt === revision) documents.value = result
    } catch (cause) {
      if (!disposed) refreshError.value = cause instanceof Error ? cause.message : 'Could not load documents.'
    } finally {
      loading.value = false
      refreshing.value = false
      if (!refreshError.value) scheduleRefresh()
    }
  }

  async function upload(file: File) {
    if (uploading.value) return
    uploading.value = true
    error.value = ''
    try {
      const document = await uploadDocument(file)
      revision++
      if (disposed) return
      documents.value = [document, ...documents.value.filter((item) => item.id !== document.id)]
      scheduleRefresh()
    } catch (cause) {
      error.value = (cause instanceof Error ? cause.message : 'Upload failed.') + ' Refresh the document list before retrying.'
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

  return { documents, loading, uploading, deletingIds, error, refreshError, refreshing, refresh, upload, remove }
}
