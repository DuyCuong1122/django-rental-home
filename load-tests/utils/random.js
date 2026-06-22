export function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function randomFloat(min, max, precision = 2) {
  const value = Math.random() * (max - min) + min;
  return Number(value.toFixed(precision));
}

export function chance(probability) {
  return Math.random() < probability;
}

export function pickRandom(items, fallback = null) {
  if (!items || items.length === 0) {
    return fallback;
  }

  return items[randomInt(0, items.length - 1)];
}

export function pickWeighted(weightedItems) {
  const totalWeight = weightedItems.reduce((sum, item) => sum + item.weight, 0);
  let cursor = Math.random() * totalWeight;

  for (const item of weightedItems) {
    cursor -= item.weight;
    if (cursor <= 0) {
      return item.value;
    }
  }

  return weightedItems[weightedItems.length - 1].value;
}

export function unique(items) {
  return Array.from(new Set((items || []).filter(Boolean)));
}

export function randomPauseRange(minSeconds = 0.2, maxSeconds = 1.2) {
  return randomFloat(minSeconds, maxSeconds, 3);
}
