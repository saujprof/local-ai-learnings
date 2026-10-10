import type { ChatMessage, ChatHistoryPage, ChatResponse } from '../types/chat'
import type { PdfDocument } from '../types/document'

import { http } from './http'

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export async function listDocuments(): Promise<PdfDocument[]> {
  return (await http.get<PdfDocument[]>('/docs', { timeout: 15000 })).data
}

export async function uploadDocument(file: File): Promise<PdfDocument> {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a PDF file.')
  if (!file.size) throw new Error('This file is empty. Choose a PDF with content.')
  const body = new FormData()
  body.append('file', file)
  return (await http.post<PdfDocument>('/docs', body)).data
}

export async function deleteDocument(id: string): Promise<void> {
  await http.delete(`/docs/${encodeURIComponent(id)}`)
}

const historyKey = 'pdf-rag-demo-chat-v1'
// Chat remains mocked until integration unit 12.3.
function readHistory(): ChatMessage[] {
  const raw = localStorage.getItem(historyKey)
  return raw ? JSON.parse(raw) : []
}

export async function listChatMessages(limit = 10, offset = 0): Promise<ChatHistoryPage> {
  await delay(250)
  const history = readHistory()
  const end = Math.max(0, history.length - offset)
  const start = Math.max(0, end - limit)
  return { messages: history.slice(start, end), hasMore: start > 0 }
}

// Mock answers and page numbers demonstrate presentation only; no PDF is read.
export async function sendQuestion(question: string): Promise<ChatResponse> {
  const trimmed = question.trim()
  if (!trimmed) throw new Error('Enter a question.')
  await delay(1200)
  if (trimmed.toLowerCase() === '/fail') throw new Error('Simulated chat failure. Edit your question and send again.')
  const ready = (await listDocuments()).filter((document) => document.status === 'ready')
  if (!ready.length) throw new Error('Upload a PDF and wait until it is ready before asking a question.')
  const response: ChatResponse = {
    question: trimmed,
    answer: `**Demo answer**\n\nThis is a demo response to “${trimmed}”. In the connected application, an answer will be generated from your indexed PDFs. The references below use example page numbers and are not evidence from your files.`,
    sources: ready.slice(0, 2).map((document, index) => ({
      document_id: document.id,
      document_name: document.name,
      page_start: index === 0 ? 1 : 2,
      page_end: index === 0 ? 1 : 3,
    })),
  }
  const history = readHistory()
  history.push(
    { id: crypto.randomUUID(), role: 'user', content: trimmed },
    { id: crypto.randomUUID(), role: 'assistant', content: response.answer, sources: response.sources },
  )
  localStorage.setItem(historyKey, JSON.stringify(history))
  return response
}
