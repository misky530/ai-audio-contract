import type { Phase, PageType } from '../types/contract';

const STORAGE_KEY = 'contract_data';

export interface ContractStore {
    phase: Phase;
    fieldIndex: number;
    fromSummary: boolean;
    editingItem: number;
    headerAnswers: Record<string, string>;
    itemList: Record<string, string>[];
    currentItem: Record<string, string>;
    lastFilename: string;
}

const defaultStore: ContractStore = {
    phase: 'header',
    fieldIndex: 0,
    fromSummary: false,
    editingItem: -1,
    headerAnswers: {},
    itemList: [],
    currentItem: {},
    lastFilename: '',
};

export function getStore(): ContractStore {
    try {
        const data = wx.getStorageSync(STORAGE_KEY);
        if (data) {
            return { ...defaultStore, ...data };
        }
    } catch {
    }
    return { ...defaultStore };
}

function saveStore(store: ContractStore): void {
    try {
        wx.setStorageSync(STORAGE_KEY, store);
    } catch {
    }
}

export function getCurrentPhase(): Phase {
    return getStore().phase;
}

export function getFieldIndex(): number {
    return getStore().fieldIndex;
}

export function setFieldIndex(index: number): void {
    const store = getStore();
    store.fieldIndex = index;
    saveStore(store);
}

export function getFromSummary(): boolean {
    return getStore().fromSummary;
}

export function setFromSummary(value: boolean): void {
    const store = getStore();
    store.fromSummary = value;
    saveStore(store);
}

export function getEditingItem(): number {
    return getStore().editingItem;
}

export function setEditingItem(index: number): void {
    const store = getStore();
    store.editingItem = index;
    saveStore(store);
}

export function getHeaderAnswers(): Record<string, string> {
    return getStore().headerAnswers;
}

export function setHeaderAnswer(key: string, value: string): void {
    const store = getStore();
    if (value) {
        store.headerAnswers[key] = value;
    } else {
        delete store.headerAnswers[key];
    }
    saveStore(store);
}

export function getItemList(): Record<string, string>[] {
    return getStore().itemList;
}

export function addItem(item: Record<string, string>): void {
    const store = getStore();
    if (store.editingItem >= 0) {
        store.itemList[store.editingItem] = item;
    } else {
        store.itemList.push(item);
    }
    saveStore(store);
}

export function updateItem(index: number, item: Record<string, string>): void {
    const store = getStore();
    if (index >= 0 && index < store.itemList.length) {
        store.itemList[index] = item;
        saveStore(store);
    }
}

export function removeItem(index: number): void {
    const store = getStore();
    store.itemList.splice(index, 1);
    saveStore(store);
}

export function getCurrentItem(): Record<string, string> {
    return getStore().currentItem;
}

export function setCurrentItem(item: Record<string, string>): void {
    const store = getStore();
    store.currentItem = item;
    saveStore(store);
}

export function setPhase(phase: Phase): void {
    const store = getStore();
    store.phase = phase;
    saveStore(store);
}

export function getLastFilename(): string {
    return getStore().lastFilename;
}

export function setLastFilename(filename: string): void {
    const store = getStore();
    store.lastFilename = filename;
    saveStore(store);
}

export function startHeader(): void {
    const store = getStore();
    store.phase = 'header';
    store.fieldIndex = 0;
    store.fromSummary = false;
    store.editingItem = -1;
    store.currentItem = {};
    saveStore(store);
}

export function startNewItem(): void {
    const store = getStore();
    store.phase = 'item';
    store.fieldIndex = 0;
    store.editingItem = -1;
    store.currentItem = {};
    saveStore(store);
}

export function editItem(index: number): void {
    const store = getStore();
    store.editingItem = index;
    store.currentItem = { ...store.itemList[index] };
    store.phase = 'item';
    store.fieldIndex = 0;
    store.fromSummary = false;
    saveStore(store);
}

export function editLastItem(): void {
    const store = getStore();
    if (store.itemList.length === 0) return;
    editItem(store.itemList.length - 1);
}

export function saveField(key: string, value: string): void {
    const store = getStore();
    if (store.phase === 'header') {
        if (value) {
            store.headerAnswers[key] = value;
        }
    } else {
        if (value) {
            store.currentItem[key] = value;
        }
    }
    saveStore(store);
}

export function saveCurrentItem(): void {
    const store = getStore();
    if (store.editingItem >= 0) {
        store.itemList[store.editingItem] = { ...store.currentItem };
    } else {
        store.itemList.push({ ...store.currentItem });
    }
    saveStore(store);
}

export function resetStore(): void {
    try {
        wx.removeStorageSync(STORAGE_KEY);
    } catch {
    }
}

export function navigateTo(page: PageType, params?: Record<string, string>): void {
    const pages: Record<PageType, string> = {
        record: '/pages/contract/record/record',
        itemlist: '/pages/contract/itemlist/itemlist',
        summary: '/pages/contract/summary/summary',
        success: '/pages/contract/success/success',
    };

    let url = pages[page];
    if (params) {
        const query = Object.entries(params)
            .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
            .join('&');
        url += `?${query}`;
    }

    if (page === 'record') {
        wx.redirectTo({ url });
    } else {
        wx.navigateTo({ url });
    }
}