/* eslint-disable no-console */
import { DimItem } from 'app/inventory/item-types';
import { storesSelector } from 'app/inventory/selectors';
import { store } from 'app/store/store';
import {
  getDisplayedItemSockets,
  getSocketsByIndexes,
  isKillTrackerSocket,
} from 'app/utils/socket-utils';

const socket = new WebSocket('ws://localhost:8765');

socket.addEventListener('open', () => {
  console.log('MCP: WebSocket connection opened, preparing data...');
  sendInventory();
});

function sendInventory() {
  const state = store.getState();
  const stores = storesSelector(state);
  if (!stores.length) {
    console.log('MCP: Inventory not loaded yet, retrying in 1s...');
    setTimeout(sendInventory, 1000);
    return;
  }

  let allItems: DimItem[] = [];
  for (const dimStore of stores) {
    const gearItems = dimStore.items.filter((i) => i.bucket.inWeapons || i.bucket.inArmor);
    allItems = allItems.concat(gearItems);
  }

  const itemsData = allItems.map((item) => buildItemData(item));
  socket.send(JSON.stringify(itemsData));
  console.log(`MCP: Sent ${itemsData.length} item entries to the server.`);
}

function buildItemData(item: DimItem) {
  const itemObj: any = {
    name: item.name,
    type: item.typeName,
    class:
      item.classTypeNameLocalized?.toLowerCase() === 'unknown'
        ? 'Any'
        : item.classTypeNameLocalized,
    rarity: item.rarity,
  };

  if (item.power !== undefined) {
    itemObj.power = item.power;
  } else if (item.primaryStat) {
    itemObj.power = item.primaryStat.value;
  }

  if (item.element) {
    itemObj.element = item.element.displayProperties.name;
  }

  if (item.stats) {
    const stats: Record<string, number> = {};
    for (const stat of item.stats) {
      stats[stat.displayProperties.name] = stat.value;
    }
    itemObj.stats = stats;
  }

  if (item.energy) {
    const energyTypeMap: Record<number, string> = {
      1: 'Arc',
      2: 'Solar',
      3: 'Void',
      6: 'Stasis',
    };
    const { energyType, energyCapacity } = item.energy;
    itemObj.energy = {
      type: energyTypeMap[energyType] || 'Any',
      capacity: energyCapacity,
    };
  }

  const sockets = getDisplayedItemSockets(item, true);
  const perksByColumn: string[][] = [];
  const socketCategories: Record<string, string[]> = {};

  if (sockets) {
    const { intrinsicSocket, perks, modSocketsByCategory } = sockets;

    if (intrinsicSocket) {
      if (
        isKillTrackerSocket(intrinsicSocket) &&
        intrinsicSocket.plugged?.plugDef.displayProperties.name
      ) {
        perksByColumn.push([intrinsicSocket.plugged.plugDef.displayProperties.name]);
      } else {
        const names = intrinsicSocket.plugOptions.map((p) => {
          const name = p.plugDef.displayProperties.name;
          return intrinsicSocket.plugged?.plugDef.hash === p.plugDef.hash ? `${name}*` : name;
        });
        perksByColumn.push(names);
      }
    }

    if (perks) {
      const perkSockets = getSocketsByIndexes(item.sockets!, perks.socketIndexes);
      for (const socket of perkSockets) {
        if (isKillTrackerSocket(socket) && socket.plugged?.plugDef.displayProperties.name) {
          perksByColumn.push([socket.plugged.plugDef.displayProperties.name]);
        } else {
          const names = socket.plugOptions.map((p) => {
            const name = p.plugDef.displayProperties.name;
            return socket.plugged?.plugDef.hash === p.plugDef.hash ? `${name}*` : name;
          });
          perksByColumn.push(names);
        }
      }
    }

    for (const [category, socketList] of modSocketsByCategory) {
      const categoryName = category.category.displayProperties.name;
      const names: string[] = [];
      for (const socket of socketList) {
        if (isKillTrackerSocket(socket) && socket.plugged?.plugDef.displayProperties.name) {
          names.push(socket.plugged.plugDef.displayProperties.name);
        } else {
          for (const p of socket.plugOptions) {
            const name = p.plugDef.displayProperties.name;
            names.push(socket.plugged?.plugDef.hash === p.plugDef.hash ? `${name}*` : name);
          }
        }
      }
      if (names.length) {
        socketCategories[categoryName] = names;
      }
    }
  }

  if (perksByColumn.length) {
    itemObj.perksByColumn = perksByColumn;
  }
  if (Object.keys(socketCategories).length) {
    itemObj.socketCategories = socketCategories;
  }

  if (item.masterworkInfo) {
    const mw = item.masterworkInfo;
    const mwObj: any = { tier: mw.tier };
    if (mw.stats?.length) {
      mwObj.stats = mw.stats.map((s) => ({ name: s.name, value: s.value }));
    }
    itemObj.masterwork = mwObj;
  }

  return itemObj;
}

socket.addEventListener('error', (evt) => {
  console.error('MCP: WebSocket error', evt);
});

socket.addEventListener('close', () => {
  console.log('MCP: WebSocket connection closed.');
});

export function startMcpSocket() {
  // intentional noop - socket connection starts on import
}
