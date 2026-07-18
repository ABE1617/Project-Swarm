import {
  Box,
  FileInput,
  FileOutput,
  GitBranch,
  Globe,
  Play,
  Shuffle,
  Sparkles,
  Timer,
  Variable,
  type LucideIcon,
} from 'lucide-react'

const ICONS: Record<string, LucideIcon> = {
  play: Play,
  globe: Globe,
  'git-branch': GitBranch,
  variable: Variable,
  shuffle: Shuffle,
  sparkles: Sparkles,
  'file-input': FileInput,
  'file-output': FileOutput,
  timer: Timer,
  box: Box,
}

export default function NodeIcon({ name, size = 16 }: { name: string; size?: number }) {
  const Icon = ICONS[name] ?? Box
  return <Icon size={size} strokeWidth={2} />
}
