/**
 * @jest-environment node
 */
import { middleware } from '@/middleware'
import { NextRequest } from 'next/server'

describe('middleware', () => {
  it('redirects to /admin if no session cookie', () => {
    const req = new NextRequest('http://localhost/admin/new')
    const res = middleware(req)
    expect(res.headers.get('location')).toContain('/admin')
    expect(res.status).toBe(307)
  })

  it('allows request through if session cookie exists', () => {
    const req = new NextRequest('http://localhost/admin/new', {
      headers: { Cookie: 'session=fake.jwt.token' },
    })
    const res = middleware(req)
    expect(res.status).toBe(200)
  })
})
