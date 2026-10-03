import type { ChatMessage, ChatHistoryPage, ChatResponse } from '../types/chat'
import type { PdfDocument } from '../types/document'

// Temporary in-memory service. Reloading the page clears uploaded documents.
// A filename ending in .fail.pdf simulates an ingestion failure.
const documents: PdfDocument[] = []
const processingEnds = new Map<string, number>()
const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export async function listDocuments(): Promise<PdfDocument[]> {
  await delay(250)
  for (const document of documents) {
    const ends = processingEnds.get(document.id)
    if (document.status === 'processing' && ends !== undefined && Date.now() >= ends) {
      document.status = document.name.toLowerCase().endsWith('.fail.pdf') ? 'failed' : 'ready'
      if (document.status === 'failed') document.error = 'Could not process this PDF. Delete it and try another file.'
      processingEnds.delete(document.id)
    }
  }
  return documents.map((document) => ({ ...document }))
}

export async function uploadDocument(file: File): Promise<PdfDocument> {
  if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Choose a PDF file.')
  if (file.size === 0) throw new Error('This file is empty. Choose a PDF with content.')
  await delay(700)
  const document: PdfDocument = { id: crypto.randomUUID(), name: file.name, status: 'processing' }
  documents.unshift(document)
  processingEnds.set(document.id, Date.now() + 3000)
  return { ...document }
}

export async function deleteDocument(id: string): Promise<void> {
  await delay(700)
  const index = documents.findIndex((document) => document.id === id)
  if (index === -1) throw new Error('Document not found. Refresh the document list and try again.')
  documents.splice(index, 1)
  processingEnds.delete(id)
}

const historyKey = 'pdf-rag-demo-chat-v1'
// The mock keeps history across reloads; document storage is still temporary.
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
  const ready = documents.filter((document) => document.status === 'ready')
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
