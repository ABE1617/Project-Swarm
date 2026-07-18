/** The Swarm mark: a branching flow inside a honeycomb cell. */
export default function Logo({ size = 24, color = '#FFB224' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M16 2.5 L27.7 9.25 V22.75 L16 29.5 L4.3 22.75 V9.25 Z"
        stroke={color}
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path
        d="M11.2 16 L20.3 11.7 M11.2 16 L20.3 20.3"
        stroke={color}
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <circle cx="11.2" cy="16" r="2.5" fill={color} />
      <circle cx="20.8" cy="11.5" r="2.1" fill={color} />
      <circle cx="20.8" cy="20.5" r="2.1" fill={color} />
    </svg>
  )
}
