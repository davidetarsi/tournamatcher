import { z } from 'zod'
import type { SchemaField } from '@/types/schema'

export function generateZodSchema(
  fields: SchemaField[]
): z.ZodObject<Record<string, z.ZodTypeAny>> {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of fields) {
    let base: z.ZodTypeAny
    switch (f.type) {
      case 'text':   base = z.string().max(f.max_length ?? 200); break
      case 'email':  base = z.string().email(); break
      case 'number': base = z.number(); break
      case 'date':   base = z.string().date(); break
      default:       continue
    }
    shape[f.key] = f.required ? base : base.optional()
  }
  return z.object(shape)
}
