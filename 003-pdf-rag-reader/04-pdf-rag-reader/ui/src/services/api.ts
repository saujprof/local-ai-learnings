import type { ChatHistoryPage, ChatResponse } from '../types/chat'
import type { PdfDocument } from '../types/document'

import { http } from './http'


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

export async function listChatMessages(limit = 10, offset = 0): Promise<ChatHistoryPage> {
  return (await http.get<ChatHistoryPage>('/chat', { params: { limit, offset }, timeout: 15000 })).data
}

export async function sendQuestion(question: string): Promise<ChatResponse> {
  const trimmed = question.trim()
  if (!trimmed) throw new Error('Enter a question.')
  return (await http.post<ChatResponse>('/chat', { question: trimmed })).data
}
