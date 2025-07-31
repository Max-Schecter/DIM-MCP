/* eslint-disable no-console */
import type { TagValue } from 'app/inventory/dim-item-info';
import type { DimItem } from 'app/inventory/item-types';
import {
  allItemsSelector,
  getNotesSelector,
  getTagSelector,
  storesSelector,
} from 'app/inventory/selectors';
import { buildSocketNames, csvStatNamesForDestinyVersion } from 'app/inventory/spreadsheets';
import type { DimStore } from 'app/inventory/store-types';
import { getStore } from 'app/inventory/stores-helpers';
import { D1_StatHashes } from 'app/search/d1-known-values';
import store from 'app/store/store';
import { getItemKillTrackerInfo } from 'app/utils/item-utils';
import { countEnhancedPerks } from 'app/utils/socket-utils';
import { StatHashes } from 'data/d2/generated-enums';

const MCP_PORT = 9130;
const MCP_URL = `wss://localhost:${MCP_PORT}`;
let socket: WebSocket | null = null;
let sending = false;

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function buildBaseItemSummary(
  item: DimItem,
  getTag: (item: DimItem) => TagValue | undefined,
  getNotes: (item: DimItem) => string | undefined,
  statNames: Map<number, string>,
  stores: readonly DimStore[],
) {
  const stats: Record<string, number> = {};
  for (const stat of item.stats ?? []) {
    const name = statNames.get(stat.statHash) ?? stat.displayProperties.name;
    stats[name] = stat.value;
  }

  const store = getStore(stores, item.owner);

  return {
    name: item.name,
    type: item.typeName,
    tier: item.tier,
    element: item.element?.displayProperties.name,
    power: item.power,
    stats,
    owner: store?.name ?? item.owner,
    tag: getTag(item),
    notes: getNotes(item),
  };
}

function buildWeaponSummary(
  item: DimItem,
  getTag: (item: DimItem) => TagValue | undefined,
  getNotes: (item: DimItem) => string | undefined,
  statNames: Map<number, string>,
  stores: readonly DimStore[],
) {
  const base = buildBaseItemSummary(item, getTag, getNotes, statNames, stores);
  return {
    ...base,
    perks: buildSocketNames(item),
    enhancedPerks: item.sockets ? countEnhancedPerks(item.sockets) : 0,
    craftedLevel: item.craftedInfo?.level,
    killTracker: getItemKillTrackerInfo(item)?.count,
  };
}

function buildArmorSummary(
  item: DimItem,
  getTag: (item: DimItem) => TagValue | undefined,
  getNotes: (item: DimItem) => string | undefined,
  statNames: Map<number, string>,
  stores: readonly DimStore[],
) {
  const base = buildBaseItemSummary(item, getTag, getNotes, statNames, stores);
  return {
    ...base,
    mods: buildSocketNames(item),
    enhancedPerks: item.sockets ? countEnhancedPerks(item.sockets) : 0,
  };
}

async function sendWeapons() {
  const state = store.getState();
  const allItems = allItemsSelector(state);
  const getTag = getTagSelector(state);
  const getNotes = getNotesSelector(state);
  const destinyVersion = allItems[0]?.destinyVersion ?? 2;
  const statNames = csvStatNamesForDestinyVersion(destinyVersion);
  const stores = storesSelector(state);

  const weapons = allItems
    .filter(
      (item) =>
        item.primaryStat &&
        (item.primaryStat.statHash === D1_StatHashes.Attack ||
          item.primaryStat.statHash === StatHashes.Attack),
    )
    .map((item) => buildWeaponSummary(item, getTag, getNotes, statNames, stores));

  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'weapons', data: weapons }));
  }
}

async function sendArmor() {
  const state = store.getState();
  const allItems = allItemsSelector(state);
  const getTag = getTagSelector(state);
  const getNotes = getNotesSelector(state);
  const destinyVersion = allItems[0]?.destinyVersion ?? 2;
  const statNames = csvStatNamesForDestinyVersion(destinyVersion);
  const stores = storesSelector(state);

  const armor = allItems
    .filter((item) => item.bucket.inArmor)
    .map((item) => buildArmorSummary(item, getTag, getNotes, statNames, stores));

  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'armor', data: armor }));
  }
}

async function sendInventory() {
  if (sending) {
    console.log('🔄 Skipping sendInventory — already in progress');
    return;
  }
  sending = true;
  console.log('🚀 Sending inventory data (per-store streaming)...');

  const state = store.getState();
  const stores = storesSelector(state);
  const currencies = state.inventory.currencies;

  try {
    // 1) Tell server how many stores to expect
    socket?.send(JSON.stringify({ type: 'inventoryStart', storeCount: stores.length }));
    await sleep(10);

    // 2) Send currencies separately (small)
    socket?.send(JSON.stringify({ type: 'currencies', data: currencies }));
    await sleep(10);

    // 3) Send each store as its own chunked blob
    const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB

    for (let i = 0; i < stores.length; i++) {
      const store = stores[i];
      const seen = new WeakSet<object>();
      const sjson = JSON.stringify(store, function (_: any, value: any) {
        if (typeof value === 'object' && value !== null) {
          if (seen.has(value as object)) {
            return '[Circular]';
          }
          seen.add(value as object);
        }
        // eslint-disable-next-line @typescript-eslint/no-unsafe-return
        return value;
      });

      const totalChunks = Math.ceil(sjson.length / CHUNK_SIZE) || 1;
      for (let c = 0; c < totalChunks; c++) {
        const chunk = sjson.slice(c * CHUNK_SIZE, (c + 1) * CHUNK_SIZE);
        const message = JSON.stringify({
          type: 'storeChunk',
          storeIndex: i,
          chunkIndex: c,
          totalChunks,
          data: chunk,
        });
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(message);
          await sleep(20); // throttle a bit to avoid buffer backpressure
        }
      }
      console.log(`📤 Store ${i} sent in ${Math.ceil(sjson.length / CHUNK_SIZE) || 1} chunks`);
      await sleep(30);
    }

    console.log('✅ All stores sent');
  } catch (err) {
    console.error('❌ sendInventory failed:', err);
  } finally {
    sending = false;
  }
}

function handleMessage(event: MessageEvent) {
  let message: any = null;
  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    message = JSON.parse(String(event.data));
  } catch {
    if (event.data === 'ping') {
      sendInventory();
      sendWeapons();
      return;
    }
  }
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
  if (message && message.type === 'ping') {
    sendInventory();
    sendWeapons();
    sendArmor();
  }
}

function connect() {
  socket = new WebSocket(MCP_URL);

  socket.onopen = async () => {
    console.log('MCP WebSocket connected');
    try {
      socket?.send(JSON.stringify({ type: 'hello' }));
    } catch {}
    await sendInventory();
    await sendWeapons();
    await sendArmor();
  };

  socket.onmessage = handleMessage;

  socket.onerror = (err) => {
    console.error('MCP WebSocket error', err);
    try {
      socket?.close();
    } catch {}
  };

  socket.onclose = () => {
    console.warn('MCP WebSocket closed, retrying in 3s');
    setTimeout(connect, 3000);
  };
}

export function startMcpSocket() {
  if (!socket || socket.readyState === WebSocket.CLOSED) {
    connect();
  }
}
