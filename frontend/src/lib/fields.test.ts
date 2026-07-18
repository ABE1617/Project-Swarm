import { describe, expect, it } from 'vitest'
import type { NodeSpec } from '../types'
import { fieldDefaults, fieldVisible, missingRequired } from './fields'

const spec: NodeSpec = {
  type: 'if_condition',
  name: 'If',
  description: '',
  category: 'Logic',
  color: '#fff',
  icon: 'git-branch',
  inputs: ['in'],
  outputs: ['true', 'false'],
  config_fields: [
    { key: 'mode', label: 'Mode', type: 'select', options: ['simple', 'expression'], default: 'simple' },
    { key: 'value1', label: 'Value 1', type: 'string', required: true, showIf: { mode: 'simple' } },
    {
      key: 'value2',
      label: 'Value 2',
      type: 'string',
      showIf: { mode: 'simple', operator: ['==', '!='] },
    },
    { key: 'operator', label: 'Operator', type: 'select', options: ['==', '!=', 'isEmpty'], default: '==' },
    { key: 'expression', label: 'Expression', type: 'string', required: true, showIf: { mode: 'expression' } },
  ],
}

describe('fieldVisible', () => {
  const defaults = fieldDefaults(spec)

  it('uses defaults when config is empty', () => {
    const value2 = spec.config_fields.find((f) => f.key === 'value2')!
    expect(fieldVisible(value2, {}, defaults)).toBe(true)
  })

  it('hides fields when showIf list does not match', () => {
    const value2 = spec.config_fields.find((f) => f.key === 'value2')!
    expect(fieldVisible(value2, { operator: 'isEmpty' }, defaults)).toBe(false)
  })

  it('hides fields for the other mode', () => {
    const expression = spec.config_fields.find((f) => f.key === 'expression')!
    expect(fieldVisible(expression, {}, defaults)).toBe(false)
    expect(fieldVisible(expression, { mode: 'expression' }, defaults)).toBe(true)
  })
})

describe('missingRequired', () => {
  it('only counts visible required fields', () => {
    // simple mode: value1 required (missing), expression hidden
    expect(missingRequired(spec, {})).toEqual(['Value 1'])
    // expression mode: expression required (missing), value1 hidden
    expect(missingRequired(spec, { mode: 'expression' })).toEqual(['Expression'])
  })

  it('treats whitespace as missing', () => {
    expect(missingRequired(spec, { value1: '   ' })).toEqual(['Value 1'])
    expect(missingRequired(spec, { value1: 'x' })).toEqual([])
  })
})
