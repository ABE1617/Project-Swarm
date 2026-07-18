/** Data-mapping helpers: build {{ }} references and find upstream nodes. */

import type { Edge } from '@xyflow/react'

const IDENT = /^[A-Za-z_]\w*$/

/** Build a template reference from a root ('input' or a node id) and a path. */
export function buildTemplate(root: string, path: Array<string | number>): string {
  let expr = root
  for (const seg of path) {
    if (typeof seg === 'number') expr += `[${seg}]`
    else if (IDENT.test(seg)) expr += `.${seg}`
    else expr += `['${String(seg).replace(/'/g, "\\'")}']`
  }
  return `{{ ${expr} }}`
}

/** Unique ids of nodes with an edge directly into nodeId. */
export function directSources(edges: Array<Pick<Edge, 'source' | 'target'>>, nodeId: string): string[] {
  const sources: string[] = []
  for (const e of edges) {
    if (e.target === nodeId && !sources.includes(e.source)) sources.push(e.source)
  }
  return sources
}

/** All upstream node ids, breadth-first (nearest first), excluding nodeId. */
export function ancestorsOf(
  edges: Array<Pick<Edge, 'source' | 'target'>>,
  nodeId: string,
): string[] {
  const result: string[] = []
  const queue = [...directSources(edges, nodeId)]
  while (queue.length) {
    const nid = queue.shift()!
    if (nid === nodeId || result.includes(nid)) continue
    result.push(nid)
    queue.push(...directSources(edges, nid))
  }
  return result
}

/** Insert text into a string at the element's cursor, returning the new value. */
export function insertAtCursor(
  element: HTMLInputElement | HTMLTextAreaElement | null,
  current: string,
  text: string,
): string {
  if (!element || element.selectionStart === null) {
    return current ? `${current}${text}` : text
  }
  const start = element.selectionStart
  const end = element.selectionEnd ?? start
  return current.slice(0, start) + text + current.slice(end)
}
