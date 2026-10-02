export type DocumentStatus = 'processing' | 'ready' | 'failed' | 'deleting'

export interface PdfDocument {
  id: string
  name: string
  status: DocumentStatus
  error?: string
}
