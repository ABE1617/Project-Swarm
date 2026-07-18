/** Config-field rules: visibility (showIf) and required checks.
    Mirrors backend/app/engine/fields.py — keep the semantics in sync. */

import type { ConfigField, NodeSpec } from '../types'

export function fieldDefaults(spec: NodeSpec): Record<string, unknown> {
  const defaults: Record<string, unknown> = {}
  for (const field of spec.config_fields) defaults[field.key] = field.default
  return defaults
}

export function fieldVisible(
  field: ConfigField,
  config: Record<string, unknown>,
  defaults: Record<string, unknown>,
): boolean {
  if (!field.showIf) return true
  return Object.entries(field.showIf).every(([key, expected]) => {
    let actual = config[key]
    if (actual === undefined || actual === null || actual === '') actual = defaults[key]
    if (Array.isArray(expected)) return expected.map(String).includes(String(actual))
    return String(actual) === String(expected)
  })
}

/** Labels of required, currently-visible fields that have no value. */
export function missingRequired(spec: NodeSpec, config: Record<string, unknown>): string[] {
  const defaults = fieldDefaults(spec)
  const missing: string[] = []
  for (const field of spec.config_fields) {
    if (!field.required) continue
    if (!fieldVisible(field, config, defaults)) continue
    const value = config[field.key] ?? field.default
    if (value === undefined || value === null || (typeof value === 'string' && !value.trim())) {
      missing.push(field.label ?? field.key)
    }
  }
  return missing
}
