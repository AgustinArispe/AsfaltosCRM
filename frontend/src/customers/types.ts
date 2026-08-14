export type CustomerSummary = {
  id: number
  name: string
  company: string | null
  email: string | null
  phone: string | null
  province: string | null
  legendary_historical_override: boolean
  /** Effective server-provided legendary qualification for operational surfaces. */
  is_legendary?: boolean
  updated_at?: string
}

export type CustomerDetail = CustomerSummary & {
  created_at: string
}

export type CustomerImportIssue = {
  field_name: string | null
  code: string
  message: string
}

export type CustomerImportRow = {
  row_number: number
  name: string
  company: string | null
  email: string | null
  phone: string | null
  province: string | null
  action: 'CREATE' | 'ENRICH' | 'UNCHANGED' | 'ERROR'
  resolved_customer_id: number | null
  issues: CustomerImportIssue[]
}

export type CustomerImportReport = {
  id: number
  client_import_id: string
  file_sha256: string
  source_filename: string
  status: 'VALID' | 'INVALID' | 'COMMITTED'
  version: number
  row_count: number
  create_count: number
  enrich_count: number
  unchanged_count: number
  error_count: number
  rows: CustomerImportRow[]
  created_at: string
  committed_at: string | null
}

export type CustomerImportCommitResult = {
  batch_id: number
  status: 'COMMITTED'
  created_count: number
  enriched_count: number
  unchanged_count: number
  customer_ids: number[]
  committed_at: string
}

export type CustomerFormValues = {
  name: string
  company: string
  email: string
  phone: string
  province: string
  legendary_historical_override: boolean
}

export type CustomerWritePayload = {
  name: string
  company: string | null
  email: string | null
  phone: string | null
  province: string | null
  legendary_historical_override?: boolean
}

export type CustomerUpdatePayload = Partial<CustomerWritePayload> & {
  expected_updated_at: string
}
