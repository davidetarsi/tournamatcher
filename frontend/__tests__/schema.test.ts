import { generateZodSchema } from '@/lib/schema'
import type { SchemaField } from '@/types/schema'

describe('generateZodSchema', () => {
  it('validates text field with max_length', () => {
    const fields: SchemaField[] = [{ key: 'nome', type: 'text', required: true, max_length: 10 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ nome: 'ok' }).success).toBe(true)
    expect(schema.safeParse({ nome: 'x'.repeat(11) }).success).toBe(false)
  })

  it('validates email field', () => {
    const fields: SchemaField[] = [{ key: 'email', type: 'email', required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ email: 'a@b.com' }).success).toBe(true)
    expect(schema.safeParse({ email: 'not-email' }).success).toBe(false)
  })

  it('validates number field', () => {
    const fields: SchemaField[] = [{ key: 'jersey', type: 'number', required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ jersey: 10 }).success).toBe(true)
    expect(schema.safeParse({ jersey: 'ten' }).success).toBe(false)
  })

  it('makes optional field accept undefined', () => {
    const fields: SchemaField[] = [{ key: 'city', type: 'text', required: false, max_length: 80 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(true)
    expect(schema.safeParse({ city: 'Milano' }).success).toBe(true)
  })

  it('rejects required field when missing', () => {
    const fields: SchemaField[] = [{ key: 'nome', type: 'text', required: true, max_length: 100 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(false)
  })

  it('skips unknown field types without crashing', () => {
    const fields = [{ key: 'x', type: 'unknown' as any, required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(true)
  })
})
