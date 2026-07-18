import { describe, expect, it } from 'vitest'
import { timeAgo } from './time'

describe('timeAgo', () => {
  const now = new Date('2026-07-18T12:00:00Z')

  it('formats recent times compactly', () => {
    expect(timeAgo('2026-07-18T11:59:40Z', now)).toBe('just now')
    expect(timeAgo('2026-07-18T11:55:00Z', now)).toBe('5m ago')
    expect(timeAgo('2026-07-18T09:00:00Z', now)).toBe('3h ago')
    expect(timeAgo('2026-07-16T12:00:00Z', now)).toBe('2d ago')
  })

  it('falls back to a date for old timestamps', () => {
    expect(timeAgo('2026-01-01T00:00:00Z', now)).not.toContain('ago')
  })

  it('handles invalid input', () => {
    expect(timeAgo('not-a-date', now)).toBe('')
  })
})
