import { ITEM_FIELDS } from '../../../services/api';
import {
    getStore,
    removeItem,
    editItem as editItemStore,
    startNewItem,
    navigateTo,
} from '../../../services/store';

Page({
    data: {
        itemList: [],
        itemTitles: [],
        itemDetails: [],
        progress: 0,
        stepLabel: '',
    },

    onLoad: function () {
        this.renderItemList();
    },

    onShow: function () {
        this.renderItemList();
    },

    renderItemList: function () {
        var self = this;
        var store = getStore();
        var itemList = store.itemList;

        var itemTitles = {};
        var itemDetails = {};

        itemList.forEach(function (item, i) {
            var titleParts = [item['货物品牌'], item['货物型号'], item['货物品类']].filter(function (v) { return v; });
            itemTitles[i] = titleParts.length > 0 ? titleParts.join(' ') : '第' + (i + 1) + '条';

            var spec = item['货物规格'] ? '（' + item['货物规格'] + '）' : '';
            var qty = item['数量'] || '';
            var price = item['单价'] ? '单价 ' + item['单价'] + ' 元' : '';
            var detailParts = [qty, price].filter(function (v) { return v; });
            itemDetails[i] = detailParts.length > 0 ? detailParts.join(' | ') : '';
        });

        var totalFields = 3 + itemList.length * ITEM_FIELDS.length;
        var doneFields = 3;
        var progress = totalFields > 0 ? (doneFields / totalFields) * 80 : 0;
        var stepLabel = '已添加 ' + itemList.length + ' 条货物';

        self.setData({
            itemList: itemList,
            itemTitles: itemTitles,
            itemDetails: itemDetails,
            progress: progress,
            stepLabel: stepLabel,
        });
    },

    onBack: function () {
        wx.navigateBack();
    },

    editItem: function (e) {
        var index = e.currentTarget.dataset.index;
        editItemStore(index);
        navigateTo('record');
    },

    deleteItem: function (e) {
        var self = this;
        var index = e.currentTarget.dataset.index;
        wx.showModal({
            title: '确认删除',
            content: '确定要删除这条货物吗？',
            success: function (res) {
                if (res.confirm) {
                    removeItem(index);
                    self.renderItemList();
                }
            },
        });
    },

    startNewItem: function () {
        startNewItem();
        navigateTo('record');
    },

    goToSummary: function () {
        if (this.data.itemList.length === 0) {
            wx.showToast({ title: '请至少添加一条货物', icon: 'none' });
            return;
        }
        navigateTo('summary');
    },
});