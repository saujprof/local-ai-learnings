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
