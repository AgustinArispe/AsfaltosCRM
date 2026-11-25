const DONUT_CENTER = 56
const DONUT_RADIUS = 44

function donutPoint(fraction: number): { x: number; y: number } {
  const angle = fraction * Math.PI * 2 - Math.PI / 2
  return {
    x: DONUT_CENTER + DONUT_RADIUS * Math.cos(angle),
    y: DONUT_CENTER + DONUT_RADIUS * Math.sin(angle),
  }
}

export function donutArcPath(startFraction: number, endFraction: number): string {
  const share = endFraction - startFraction
  if (share >= 1) {
    return `M ${DONUT_CENTER} ${DONUT_CENTER - DONUT_RADIUS} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 1 1 ${DONUT_CENTER} ${DONUT_CENTER + DONUT_RADIUS} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 1 1 ${DONUT_CENTER} ${DONUT_CENTER - DONUT_RADIUS}`
  }
  const start = donutPoint(startFraction)
  const end = donutPoint(endFraction)
  return `M ${start.x} ${start.y} A ${DONUT_RADIUS} ${DONUT_RADIUS} 0 ${share > 0.5 ? 1 : 0} 1 ${end.x} ${end.y}`
}
