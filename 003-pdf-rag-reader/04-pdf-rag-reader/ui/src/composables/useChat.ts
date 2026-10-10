import { onMounted, ref } from 'vue'
import { listChatMessages, sendQuestion } from '../services/api'
import { ApiError } from '../services/http'
import type { ChatMessage } from '../types/chat'

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const question = ref('')
  const sending = ref(false)
  const error = ref('')
  const historyError = ref('')
  const loadingHistory = ref(false)
  const historyReady = ref(false)
  const hasMore = ref(false)
  const needsReconciliation = ref(false)
  let offset = 0

  async function refreshHistory() {
    if (loadingHistory.value || sending.value) return
    loadingHistory.value = true
    historyError.value = ''
    try {
      const page = await listChatMessages(10, 0)
      messages.value = page.messages
      offset = page.messages.length
      hasMore.value = page.hasMore
      historyReady.value = true
      if (needsReconciliation.value) {
        error.value = 'History refreshed. Check whether your question was saved before sending again. An earlier request may still be processing.'
      }
      needsReconciliation.value = false
    } catch (cause) {
      historyError.value = cause instanceof Error ? cause.message : 'Could not refresh history.'
    } finally {
      loadingHistory.value = false
    }
  }

  async function loadHistory() {
    if (needsReconciliation.value) return refreshHistory()
    if (loadingHistory.value || sending.value || (historyReady.value && !hasMore.value)) return
    loadingHistory.value = true
    historyError.value = ''
    try {
      const page = await listChatMessages(10, offset)
      const existing = new Set(messages.value.map((message) => message.id))
      messages.value.unshift(...page.messages.filter((message) => !existing.has(message.id)))
      offset += page.messages.length
      hasMore.value = page.hasMore
      historyReady.value = true
    } catch (cause) {
      historyError.value = cause instanceof Error ? cause.message : 'Could not load chat history.'
    } finally {
      loadingHistory.value = false
    }
  }

  onMounted(loadHistory)

  async function send() {
    const text = question.value.trim()
    if (!text || sending.value || loadingHistory.value || !historyReady.value || needsReconciliation.value) return
    sending.value = true
    error.value = ''
    const pending: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    messages.value.push(pending)
    try {
      const response = await sendQuestion(text)
      messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: response.answer, sources: response.sources })
      offset += 2
      question.value = ''
    } catch (cause) {
      // Keep the draft for retry, without duplicating a failed turn in the conversation.
      messages.value = messages.value.filter((message) => message.id !== pending.id)
      error.value = cause instanceof Error ? cause.message : 'Could not get an answer. Try again.'
      if (cause instanceof ApiError && (cause.ambiguous || (cause.status !== undefined && cause.status >= 500))) {
        needsReconciliation.value = true
        error.value += ' Refresh history before sending again; the previous request may have completed.'
      }
    } finally {
      sending.value = false
    }
  }

  return { messages, question, sending, error, send, historyError, loadingHistory, historyReady, hasMore, loadHistory, refreshHistory, needsReconciliation }
}
