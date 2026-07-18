import { describe, expect, it } from 'vitest'
import { ancestorsOf, buildTemplate, directSources, insertAtCursor } from './mapping'

describe('buildTemplate', () => {
  it('builds dotted paths for identifier keys', () => {
    expect(buildTemplate('input', ['subject'])).toBe('{{ input.subject }}')
    expect(buildTemplate('gmail_read_1', ['messages', 0, 'from'])).toBe(
      '{{ gmail_read_1.messages[0].from }}',
    )
  })

  it('quotes non-identifier keys with subscripts', () => {
    expect(buildTemplate('input', ['weird key'])).toBe("{{ input['weird key'] }}")
    expect(buildTemplate('input', ["o'brien"])).toBe("{{ input['o\\'brien'] }}")
  })

  it('handles the root itself', () => {
    expect(buildTemplate('input', [])).toBe('{{ input }}')
  })
})

describe('upstream discovery', () => {
  const edges = [
    { source: 'trigger', target: 'gmail' },
    { source: 'gmail', target: 'calendar' },
    { source: 'trigger', target: 'other' },
  ]

  it('finds direct sources', () => {
    expect(directSources(edges, 'calendar')).toEqual(['gmail'])
    expect(directSources(edges, 'gmail')).toEqual(['trigger'])
    expect(directSources(edges, 'trigger')).toEqual([])
  })

  it('finds all ancestors nearest-first', () => {
    expect(ancestorsOf(edges, 'calendar')).toEqual(['gmail', 'trigger'])
    expect(ancestorsOf(edges, 'other')).toEqual(['trigger'])
  })

  it('ignores unrelated branches', () => {
    expect(ancestorsOf(edges, 'calendar')).not.toContain('other')
  })
})

describe('insertAtCursor', () => {
  it('appends when no element is available', () => {
    expect(insertAtCursor(null, 'Hello ', '{{ input.name }}')).toBe('Hello {{ input.name }}')
    expect(insertAtCursor(null, '', '{{ input.name }}')).toBe('{{ input.name }}')
  })
})
