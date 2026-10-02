import { ref } from 'vue'
import { sendQuestion } from '../services/api'
import type { ChatMessage } from '../types/chat'

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const question = ref('')
  const sending = ref(false)
  const error = ref('')

  async function send() {
    const text = question.value.trim()
    if (!text || sending.value) return
    sending.value = true
    error.value = ''
    const pending: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    messages.value.push(pending)
    try {
      const response = await sendQuestion(text)
      messages.value.push({ id: crypto.randomUUID(), role: 'assistant', content: response.answer, sources: response.sources })
      question.value = ''
    } catch (cause) {
      // Keep the draft for retry, without duplicating a failed turn in the conversation.
      messages.value = messages.value.filter((message) => message.id !== pending.id)
      error.value = cause instanceof Error ? cause.message : 'Could not get an answer. Try again.'
    } finally {
      sending.value = false
    }
  }

  return { messages, question, sending, error, send }
}
