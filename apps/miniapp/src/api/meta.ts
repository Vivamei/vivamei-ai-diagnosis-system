import { apiRequest } from './client'

export interface PublicConfig {
  analyzeEtaSeconds?: number
  analyzeTitlePreparing?: string
  analyzeTitleAnalyzing?: string
  analyzeSubtitle?: string
  analyzeWaitHints?: string[]
  analyzeWaitNote?: string
}

export const getPublicConfig = () =>
  apiRequest<PublicConfig>('/api/config', { anonymous: true })
