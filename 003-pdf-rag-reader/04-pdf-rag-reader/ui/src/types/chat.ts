export interface Source {
  document_id: string
  document_name: string
  page_start: number
  page_end: number
}

export interface ChatResponse {
  question: string
  answer: string
  sources: Source[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export interface ChatHistoryPage {
  messages: ChatMessage[]
  hasMore: boolean
}
