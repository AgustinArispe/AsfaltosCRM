export type CustomerSummary = {
  id: number
  name: string
  company: string | null
  email: string | null
  phone: string | null
  province: string | null
  legendary_historical_override: boolean
}

export type CustomerDetail = CustomerSummary & {
  created_at: string
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

export type CustomerUpdatePayload = Partial<CustomerWritePayload>
