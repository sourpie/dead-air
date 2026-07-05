// Pixel-art crew "beans" — Among Us-style silhouettes authored as pixel maps
// (one char = one pixel) and rendered as SVG rects. One shared grid set, five
// per-crew palettes; the player is the yellow bean with a detective hat.
import type { NpcId } from '../../types'

export type Sprite = { rows: string[]; palette: Record<string, string> }
export type BeanSet = { down: [Sprite, Sprite, Sprite]; side: [Sprite, Sprite, Sprite]; up: [Sprite, Sprite, Sprite] }

/* ── palette derivation ──────────────────────────────────────────────── */

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.round(((n >> 16) & 255) * f)
  const g = Math.round(((n >> 8) & 255) * f)
  const b = Math.round((n & 255) * f)
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
}

export function makeBeanPalette(body: string): Record<string, string> {
  return {
    B: body,
    D: shade(body, 0.55),   // shadow / feet
    P: shade(body, 0.75),   // backpack
    V: '#cfeef8',           // visor
    v: '#ffffff',           // visor highlight
    H: '#333c57',           // detective hat (player only)
  }
}

/* ── shared bean grids (12×16) ───────────────────────────────────────── */

const BODY_DOWN = [
  '....BBBB....',
  '..BBBBBBBB..',
  '.BBBBBBBBBB.',
  '.BVVVVVVVBB.',
  '.BVvvVVVVBB.',
  '.BVVVVVVVBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
]

const LEGS_IDLE = [
  '.BBBB..BBBB.',
  '.BBBB..BBBB.',
  '.DDDD..DDDD.',
  '............',
]
const LEGS_A = [
  '.BBBB..BBB..',
  '.BBBB...BBB.',
  '.DDDD....DD.',
  '............',
]
const LEGS_B = [
  '..BBB..BBBB.',
  '.BBB...BBBB.',
  '.DD....DDDD.',
  '............',
]

const BODY_SIDE = [
  '....BBBB....',
  '..BBBBBBB...',
  '.BBBBBBBBB..',
  'PBBBVVVVVB..',
  'PBBBVvvVVB..',
  'PBBBVVVVVB..',
  'PPBBBBBBBB..',
  'PPBBBBBBBB..',
  'PPBBBBBBBB..',
  'PBBBBBBBBB..',
  '.BBBBBBBBB..',
  '.BBBBBBBB...',
]
const SIDE_LEGS_IDLE = [
  '..BBB.BBB...',
  '..BBB.BBB...',
  '..DDD.DDD...',
  '............',
]
const SIDE_LEGS_A = [
  '..BBB..BBB..',
  '..BB....BBB.',
  '..DD.....DD.',
  '............',
]
const SIDE_LEGS_B = [
  '..BBB.BBB...',
  '...BBB.BB...',
  '...DD..DD...',
  '............',
]

const BODY_UP = [
  '....BBBB....',
  '..BBBBBBBB..',
  '.BBBBBBBBBB.',
  '.BPPPPPPPPB.',
  '.BPPPPPPPPB.',
  '.BPPPPPPPPB.',
  '.BPPPPPPPPB.',
  '.BPPPPPPPPB.',
  '.BPPPPPPPPB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
  '.BBBBBBBBBB.',
]

// Detective hat rows for the player (replace the bean's crown).
const HAT_DOWN = ['..HHHHHHHH..', 'HHHHHHHHHHHH']
const HAT_SIDE = ['..HHHHHHH...', 'HHHHHHHHHHH.']
const HAT_UP = ['..HHHHHHHH..', 'HHHHHHHHHHHH']

function bean(palette: Record<string, string>, body: string[], legs: string[], hat?: string[]): Sprite {
  const rows = hat ? [...hat, ...body.slice(hat.length)] : body
  return { palette, rows: [...rows, ...legs] }
}

function beanSet(bodyHex: string, hat = false): BeanSet {
  const p = makeBeanPalette(bodyHex)
  return {
    down: [
      bean(p, BODY_DOWN, LEGS_IDLE, hat ? HAT_DOWN : undefined),
      bean(p, BODY_DOWN, LEGS_A, hat ? HAT_DOWN : undefined),
      bean(p, BODY_DOWN, LEGS_B, hat ? HAT_DOWN : undefined),
    ],
    side: [
      bean(p, BODY_SIDE, SIDE_LEGS_IDLE, hat ? HAT_SIDE : undefined),
      bean(p, BODY_SIDE, SIDE_LEGS_A, hat ? HAT_SIDE : undefined),
      bean(p, BODY_SIDE, SIDE_LEGS_B, hat ? HAT_SIDE : undefined),
    ],
    up: [
      bean(p, BODY_UP, LEGS_IDLE, hat ? HAT_UP : undefined),
      bean(p, BODY_UP, LEGS_A, hat ? HAT_UP : undefined),
      bean(p, BODY_UP, LEGS_B, hat ? HAT_UP : undefined),
    ],
  }
}

/* ── crew + player sets ──────────────────────────────────────────────── */

export const CREW_COLORS: Record<NpcId, string> = {
  oda: '#d92f2f',
  vega: '#ef7d57',
  lin: '#5fd346',
  rio: '#38c3e8',
  nova: '#9a5ce0',
}

export const CREW_SPRITES: Record<NpcId, BeanSet> = {
  oda: beanSet(CREW_COLORS.oda),
  vega: beanSet(CREW_COLORS.vega),
  lin: beanSet(CREW_COLORS.lin),
  rio: beanSet(CREW_COLORS.rio),
  nova: beanSet(CREW_COLORS.nova),
}

export const PLAYER_SPRITES: BeanSet = beanSet('#f5d442', true)

// A convenient front-facing portrait sprite per crew (dialogs, lineups).
export const NPC_SPRITES: Record<NpcId, Sprite> = {
  oda: CREW_SPRITES.oda.down[0],
  vega: CREW_SPRITES.vega.down[0],
  lin: CREW_SPRITES.lin.down[0],
  rio: CREW_SPRITES.rio.down[0],
  nova: CREW_SPRITES.nova.down[0],
}
