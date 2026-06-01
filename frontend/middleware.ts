import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const session = request.cookies.get('session')
  if (!session?.value) {
    return NextResponse.redirect(new URL('/admin', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/new', '/admin/:id*'],
}
