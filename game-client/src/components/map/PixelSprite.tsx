// Renders a char-grid pixel sprite as SVG rects, anchored at bottom-center.
import type { Sprite } from './sprites'

export function PixelSprite({ sprite, px = 4 }: { sprite: Sprite; px?: number }) {
  const w = sprite.rows[0].length * px
  const h = sprite.rows.length * px
  return (
    <g transform={`translate(${-w / 2}, ${-h})`}>
      {sprite.rows.flatMap((row, y) =>
        [...row].map((ch, x) =>
          ch === '.' ? null : (
            <rect key={`${x}-${y}`} x={x * px} y={y * px} width={px} height={px} fill={sprite.palette[ch]} />
          ),
        ),
      )}
    </g>
  )
}

// Standalone <svg> portrait (dialog headers, lineups, meeting table).
export function BeanPortrait({ sprite, size = 40, accent }: { sprite: Sprite; size?: number; accent?: string }) {
  const px = 4
  const w = sprite.rows[0].length * px
  const h = sprite.rows.length * px
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={size * (w / h)}
      height={size}
      shapeRendering="crispEdges"
      style={{ background: 'var(--color-grape)', border: accent ? `2px solid ${accent}` : undefined }}
    >
      {sprite.rows.flatMap((row, y) =>
        [...row].map((ch, x) =>
          ch === '.' ? null : (
            <rect key={`${x}-${y}`} x={x * px} y={y * px} width={px} height={px} fill={sprite.palette[ch]} />
          ),
        ),
      )}
    </svg>
  )
}
