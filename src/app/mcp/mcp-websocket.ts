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
import { getItemKillTrackerInfo, isKillTrackerSocket } from 'app/utils/item-utils';
import { getSocketsByIndexes, getWeaponSockets, isEnhancedPerk } from 'app/utils/socket-utils';
import { StatHashes } from 'data/d2/generated-enums';

const MCP_PORT = 9130;
const MCP_URL = `wss://localhost:${MCP_PORT}`;
let socket: WebSocket | null = null;

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
    id: item.id,
    name: item.name,
    type: item.typeName,
    gearTier: item.tier,
    element: item.element?.displayProperties.name,
    power: item.power,
    stats,
    owner: store?.name ?? item.owner,
    tag: getTag(item),
    notes: getNotes(item),
  };
}

function buildWeaponPerkColumns(item: DimItem): string[][] {
  if (!item.sockets) {
    return [];
  }

  const { perks } = getWeaponSockets(item, { excludeEmptySockets: true }) ?? {};
  if (!perks) {
    return [];
  }

  return getSocketsByIndexes(item.sockets, perks.socketIndexes)
    .filter((socket) => !isKillTrackerSocket(socket))
    .map((socket) =>
      socket.plugOptions.map((p) => {
        let name = p.plugDef.displayProperties.name;
        if (isEnhancedPerk(p.plugDef)) {
          name += ' (Enhanced)';
        }
        if (socket.plugged?.plugDef.hash === p.plugDef.hash) {
          name += ' (Equipped)';
        }
        return name;
      }),
    );
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
    perks: buildWeaponPerkColumns(item),
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

function handleMessage(event: MessageEvent) {
  let message: any = null;
  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    message = JSON.parse(String(event.data));
  } catch {
    if (event.data === 'ping') {
      sendWeapons();
      sendArmor();
      return;
    }
  }
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
  if (message && message.type === 'ping') {
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
