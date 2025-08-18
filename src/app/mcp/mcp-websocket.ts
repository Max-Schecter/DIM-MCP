/* eslint-disable no-console */
import { currentAccountSelector } from 'app/accounts/selectors';
import { transfer } from 'app/bungie-api/destiny2-api';
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
import { showNotification } from 'app/notifications/notifications';
import { D1_StatHashes } from 'app/search/d1-known-values';
import { refresh } from 'app/shell/refresh-events';
import store from 'app/store/store';
import {
  getItemKillTrackerInfo,
  getMasterworkStatNames,
  isKillTrackerSocket,
} from 'app/utils/item-utils';
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
    ownerId: store?.id ?? item.owner,
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
    masterworkType: getMasterworkStatNames(item.masterworkInfo),
    masterworkTier: item.masterworkInfo?.tier,
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

function buildStoreInfo(stores: readonly DimStore[]) {
  return stores.map((store) => ({
    id: store.id,
    name: store.name,
    isVault: store.isVault,
    classType: store.classType,
    className: store.className,
    powerLevel: store.powerLevel,
    background: store.background,
    lastPlayed: store.lastPlayed?.toISOString(),
  }));
}

async function sendInventory() {
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

  const armor = allItems
    .filter((item) => item.bucket.inArmor)
    .map((item) => buildArmorSummary(item, getTag, getNotes, statNames, stores));

  const storeInfo = buildStoreInfo(stores);

  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(
      JSON.stringify({
        type: 'pong',
        weapons: { type: 'weapons', data: weapons },
        armor: { type: 'armor', data: armor },
        stores: { type: 'stores', data: storeInfo },
      }),
    );
  }
}

async function transferItemsByInstanceIds(instanceIds: string[], targetStoreId: string) {
  const state = store.getState();
  const allItems = allItemsSelector(state);
  const stores = storesSelector(state);
  const account = currentAccountSelector(state);

  if (!account) {
    throw new Error('No active account found');
  }

  const targetStore = stores.find((s) => s.id === targetStoreId);
  if (!targetStore) {
    throw new Error(`Target store not found: ${targetStoreId}`);
  }

  const results: { instanceId: string; success: boolean; error?: string }[] = [];

  for (const instanceId of instanceIds) {
    try {
      const item = allItems.find((i) => i.id === instanceId);
      if (!item) {
        results.push({
          instanceId,
          success: false,
          error: `Item not found: ${instanceId}`,
        });
        continue;
      }

      if (item.owner === targetStore.id && !item.location.inPostmaster) {
        results.push({
          instanceId,
          success: true,
        });
        continue;
      }

      if (item.notransfer && item.owner !== targetStore.id) {
        results.push({
          instanceId,
          success: false,
          error: 'Item cannot be transferred',
        });
        continue;
      }

      await transfer(account, item, targetStore, item.amount);
      results.push({
        instanceId,
        success: true,
      });
    } catch (error) {
      results.push({
        instanceId,
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  return results;
}

function handleMessage(event: MessageEvent) {
  let message: any = null;
  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    message = JSON.parse(String(event.data));
  } catch {
    if (event.data === 'ping') {
      sendInventory();
      return;
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
  if (message?.type === 'ping') {
    sendInventory();
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
  } else if (message?.type === 'transfer_items') {
    handleTransferItems(message as TransferItemsMessage);
  }
}

interface TransferItemsMessage {
  type: 'transfer_items';
  instanceIds: string[];
  targetStoreId: string;
}

async function handleTransferItems(message: TransferItemsMessage) {
  try {
    const { instanceIds, targetStoreId } = message;

    if (!Array.isArray(instanceIds)) {
      throw new Error('instanceIds must be an array');
    }

    if (typeof targetStoreId !== 'string') {
      throw new Error('targetStoreId must be a string');
    }

    const results = await transferItemsByInstanceIds(instanceIds, targetStoreId);

    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({
          type: 'transfer_items_response',
          results,
          success: true,
        }),
      );
    }

    const successCount = results.filter((r) => r.success).length;
    const failCount = results.filter((r) => !r.success).length;

    showNotification({
      type: successCount > 0 && failCount === 0 ? 'success' : failCount > 0 ? 'warning' : 'error',
      title: 'Bulk Transfer Complete',
      body: `${successCount} items transferred successfully${failCount > 0 ? `, ${failCount} failed` : ''}`,
    });

    // Refresh inventory after successful transfers
    if (successCount > 0) {
      refresh();
    }
  } catch (error) {
    console.error('Error handling transfer_items:', error);

    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({
          type: 'transfer_items_response',
          success: false,
          error: error instanceof Error ? error.message : String(error),
        }),
      );
    }

    showNotification({
      type: 'error',
      title: 'Transfer Failed',
      body: error instanceof Error ? error.message : String(error),
    });
  }
}

function connect() {
  socket = new WebSocket(MCP_URL);

  socket.onopen = async () => {
    console.log('MCP WebSocket connected');
    try {
      socket?.send(JSON.stringify({ type: 'hello' }));
    } catch {}
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
