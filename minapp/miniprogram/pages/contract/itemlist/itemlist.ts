import { ITEM_FIELDS } from '../../../services/api';
import {
    getStore,
    removeItem,
    editItem as editItemStore,
    editLastItem as editLastItemStore,
    startNewItem,
    navigateTo,
} from '../../../services/store';

interface ItemTitle {
    [key: number]: string;
}

interface ItemDetail {
    [key: number]: string;
}

Page({
    data: {
        itemList: [] as Record<string, string>[],
        itemTitles: [] as string[],
        itemDetails: [] as string[],
        progress: 0,
        stepLabel: '',
    },

    onLoad() {
        this.renderItemList();
    },

    onShow() {
        this.renderItemList();
    },

    renderItemList() {
        const store = getStore();
        const itemList = store.itemList;

        const itemTitles: ItemTitle = {};
        const itemDetails: ItemDetail = {};

        itemList.forEach((item, i) => {
            const titleParts = [item['货物品牌'], item['货物型号'], item['货物品类']].filter(Boolean);
            itemTitles[i] = titleParts.length > 0 ? titleParts.join(' ') : `第${i + 1}条`;

            const spec = item['货物规格'] ? `（${item['货物规格']}）` : '';
            const qty = item['数量'] || '';
            const price = item['单价'] ? `单价 ${item['单价']} 元` : '';
            const detailParts = [qty, price].filter(Boolean);
            itemDetails[i] = detailParts.length > 0 ? detailParts.join(' | ') : '';
        });

        const totalFields = 3 + itemList.length * ITEM_FIELDS.length;
        const doneFields = 3;
        const progress = totalFields > 0 ? (doneFields / totalFields) * 80 : 0;
        const stepLabel = `已添加 ${itemList.length} 条货物`;

        this.setData({
            itemList,
            itemTitles,
            itemDetails,
            progress,
            stepLabel,
        });
    },

    onBack() {
        wx.navigateBack();
    },

    editItem(e: any) {
        const index = e.currentTarget.dataset.index;
        editItemStore(index);
        navigateTo('record');
    },

    deleteItem(e: any) {
        const index = e.currentTarget.dataset.index;
        wx.showModal({
            title: '确认删除',
            content: '确定要删除这条货物吗？',
            success: (res) => {
                if (res.confirm) {
                    removeItem(index);
                    this.renderItemList();
                }
            },
        });
    },

    editLastItem() {
        editLastItemStore();
        navigateTo('record');
    },

    startNewItem() {
        startNewItem();
        navigateTo('record');
    },

    goToSummary() {
        if (this.data.itemList.length === 0) {
            wx.showToast({ title: '请至少添加一条货物', icon: 'none' });
            return;
        }
        navigateTo('summary');
    },
});