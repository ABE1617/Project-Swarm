/** Hand-drawn node icon set — one style: 24 grid, 1.7 rounded strokes,
    hex motifs where they carry meaning. currentColor throughout. */

import type { ReactElement } from 'react'

const HEX_SMALL = 'M12 4.5 L18.5 8.25 V15.75 L12 19.5 L5.5 15.75 V8.25 Z'

const ICONS: Record<string, ReactElement> = {
  // trigger: the cell that starts the flow
  play: (
    <>
      <path d={HEX_SMALL} />
      <path d="M10.2 9 L15.4 12 L10.2 15 Z" fill="currentColor" stroke="none" />
    </>
  ),
  // http: a ringed planet — reach anywhere
  globe: (
    <>
      <circle cx="12" cy="12" r="5.8" />
      <ellipse cx="12" cy="12" rx="10" ry="3.4" transform="rotate(-18 12 12)" />
    </>
  ),
  // if: the branch, same motif as the logo
  'git-branch': (
    <>
      <path d="M6.5 12 L16 7 M6.5 12 L16 17" />
      <circle cx="6" cy="12" r="2.1" fill="currentColor" stroke="none" />
      <circle cx="17.6" cy="6.3" r="1.9" fill="currentColor" stroke="none" />
      <circle cx="17.6" cy="17.7" r="1.9" fill="currentColor" stroke="none" />
    </>
  ),
  // set variables: braces holding a cell
  variable: (
    <>
      <path d="M8.8 4.2 C6.4 4.2 8 9.6 5 12 C8 14.4 6.4 19.8 8.8 19.8" />
      <path d="M15.2 4.2 C17.6 4.2 16 9.6 19 12 C16 14.4 17.6 19.8 15.2 19.8" />
      <path d="M12 9.9 L13.9 11 V13.2 L12 14.3 L10.1 13.2 V11 Z" fill="currentColor" stroke="none" />
    </>
  ),
  // transform: square reshaped into a hex
  shuffle: (
    <>
      <rect x="3.5" y="8.6" width="6" height="6.8" rx="1.2" />
      <path d="M11.5 12 H14" />
      <path d="M13 10.6 L14.6 12 L13 13.4" />
      <path d="M18.7 8.4 L21.5 10 V13.9 L18.7 15.6 L15.9 13.9 V10 Z" />
    </>
  ),
  // llm: a spark with a hex satellite
  sparkles: (
    <>
      <path d="M11 5.5 C11.7 9.3 13.9 11.5 17.7 12.2 C13.9 12.9 11.7 15.1 11 18.9 C10.3 15.1 8.1 12.9 4.3 12.2 C8.1 11.5 10.3 9.3 11 5.5 Z" />
      <path d="M18.6 3.6 L20.4 4.65 V6.75 L18.6 7.8 L16.8 6.75 V4.65 Z" fill="currentColor" stroke="none" />
    </>
  ),
  // read file: page with data flowing in
  'file-input': (
    <>
      <path d="M13.5 3.8 H8 a1.6 1.6 0 0 0 -1.6 1.6 V18.6 a1.6 1.6 0 0 0 1.6 1.6 H16 a1.6 1.6 0 0 0 1.6 -1.6 V8 Z" />
      <path d="M13.5 3.8 V8 H17.6" />
      <path d="M2.6 13 H10" />
      <path d="M8.2 11.2 L10 13 L8.2 14.8" />
    </>
  ),
  // write file: page with data flowing out
  'file-output': (
    <>
      <path d="M13.5 3.8 H8 a1.6 1.6 0 0 0 -1.6 1.6 V18.6 a1.6 1.6 0 0 0 1.6 1.6 H16 a1.6 1.6 0 0 0 1.6 -1.6 V8 Z" />
      <path d="M13.5 3.8 V8 H17.6" />
      <path d="M11.5 13 H21" />
      <path d="M19.2 11.2 L21 13 L19.2 14.8" />
    </>
  ),
  // delay: a watch face, hand paused
  timer: (
    <>
      <circle cx="12" cy="13.2" r="6.8" />
      <path d="M12 13.2 L14.8 10.4" />
      <path d="M10.3 3.4 H13.7" />
      <path d="M12 3.4 V6.4" />
    </>
  ),
  // fallback / custom nodes: an empty cell
  box: (
    <>
      <path d={HEX_SMALL} />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  // gmail: envelope with the fold
  gmail: (
    <>
      <rect x="3.5" y="5.5" width="17" height="13" rx="2" />
      <path d="M4.5 7.5 L12 13 L19.5 7.5" />
    </>
  ),
  // sheets: page ruled into cells
  sheets: (
    <>
      <rect x="5" y="3.8" width="14" height="16.4" rx="1.6" />
      <path d="M5 9.5 H19 M5 14 H19 M12 9.5 V20.2" />
    </>
  ),
  // calendar: month grid with an event dot
  'calendar-g': (
    <>
      <rect x="4" y="5.5" width="16" height="14.5" rx="2" />
      <path d="M4 10 H20 M8.5 3.5 V7 M15.5 3.5 V7" />
      <circle cx="12" cy="15" r="1.7" fill="currentColor" stroke="none" />
    </>
  ),
  // drive: the tri-fold
  drive: (
    <>
      <path d="M9.3 4.8 H14.7 L21 15.6 L18.2 20.2 H5.8 L3 15.6 Z" />
      <path d="M9.3 4.8 L12.6 15.6 M14.7 4.8 L8.4 15.6 H21" />
    </>
  ),
  // docs: page with text lines
  docs: (
    <>
      <path d="M13.5 3.8 H8 a1.6 1.6 0 0 0 -1.6 1.6 V18.6 a1.6 1.6 0 0 0 1.6 1.6 H16 a1.6 1.6 0 0 0 1.6 -1.6 V8 Z" />
      <path d="M13.5 3.8 V8 H17.6" />
      <path d="M9.2 12 H14.8 M9.2 15 H14.8" />
    </>
  ),
}

export default function NodeIcon({ name, size = 16 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name] ?? ICONS.box}
    </svg>
  )
}
