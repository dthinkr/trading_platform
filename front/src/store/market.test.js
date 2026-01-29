import { describe, it, expect } from 'vitest'

// The aggregation function to test
function aggregateOrdersByPrice(orders, step = 1) {
  const aggregated = {}

  orders.forEach((order) => {
    const bucket = Math.round(order.x / step) * step
    aggregated[bucket] = (aggregated[bucket] || 0) + order.y
  })

  return Object.entries(aggregated)
    .map(([x, y]) => ({ x: parseFloat(x), y }))
    .sort((a, b) => a.x - b.x)
}

describe('aggregateOrdersByPrice', () => {
  it('should aggregate orders at the same price', () => {
    const orders = [
      { x: 100, y: 5 },
      { x: 100, y: 3 },
      { x: 101, y: 2 },
    ]

    const result = aggregateOrdersByPrice(orders)

    expect(result).toEqual([
      { x: 100, y: 8 }, // 5 + 3
      { x: 101, y: 2 },
    ])
  })

  it('should round nearby prices to same bucket', () => {
    const orders = [
      { x: 99.8, y: 2 },
      { x: 100.1, y: 3 },
      { x: 100.2, y: 1 },
      { x: 101.7, y: 4 },
    ]

    const result = aggregateOrdersByPrice(orders, 1)

    expect(result).toEqual([
      { x: 100, y: 6 }, // 99.8→100, 100.1→100, 100.2→100
      { x: 102, y: 4 }, // 101.7→102
    ])
  })

  it('should handle different step sizes', () => {
    const orders = [
      { x: 99.3, y: 2 },
      { x: 99.7, y: 3 },
      { x: 100.2, y: 1 },
    ]

    const result = aggregateOrdersByPrice(orders, 0.5)

    expect(result).toEqual([
      { x: 99.5, y: 5 }, // 99.3→99.5, 99.7→99.5
      { x: 100, y: 1 },  // 100.2→100
    ])
  })

  it('should return sorted results', () => {
    const orders = [
      { x: 102, y: 1 },
      { x: 99, y: 2 },
      { x: 101, y: 3 },
    ]

    const result = aggregateOrdersByPrice(orders)

    expect(result[0].x).toBe(99)
    expect(result[1].x).toBe(101)
    expect(result[2].x).toBe(102)
  })
})
