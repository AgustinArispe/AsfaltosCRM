export type Product = {
  id: number
  name: string
  is_active: boolean
}

export type ProductUpdatePayload = {
  name?: string
  is_active?: boolean
}
