import { HEADER_FIELDS, ITEM_FIELDS, generateContract } from '../../../services/api';
import { getStore, editItem as editItemStore, setFromSummary, setPhase, setFieldIndex, setLastFilename, resetStore, navigateTo } from '../../../services/store';

Page({
    data: {
        headerFields: HEADER_FIELDS,
        headerAnswers: {},
        itemList: [],
        itemTitles: [],
        itemFieldRows: [],
        progress: 0,
        stepLabel: '',
        showLoading: false,
        loadingText: '生成合同中…',
    },

    onLoad: function () {
        this.renderSummary();
    },

    onShow: function () {
        this.renderSummary();
    },

    renderSummary: function () {
        var self = this;
        var store = getStore();
        var itemList = store.itemList;
        var headerAnswers = store.headerAnswers;

        var itemTitles = [];
        itemList.forEach(function (item) {
            var titleParts = [item['货物品牌'], item['货物型号'], item['货物品类']].filter(function (v) { return v; });
            itemTitles.push(titleParts.length > 0 ? titleParts.join(' ') : '');
        });

        var itemFieldRows = ITEM_FIELDS.filter(function (f) {
            return f.key !== '货物品牌' && f.key !== '货物型号' && f.key !== '货物品类';
        }).map(function (f) {
            return {
                fieldKey: f.key,
                label: f.label,
            };
        });

        self.setData({
            headerAnswers: headerAnswers,
            itemList: itemList,
            itemTitles: itemTitles,
            itemFieldRows: itemFieldRows,
            progress: 95,
            stepLabel: '确认信息',
        });
    },

    onBack: function () {
        wx.navigateBack();
    },

    editHeaderField: function (e) {
        var index = e.currentTarget.dataset.index;
        setFromSummary(true);
        setPhase('header');
        setFieldIndex(index);
        navigateTo('record');
    },

    editItem: function (e) {
        var index = e.currentTarget.dataset.index;
        editItemStore(index);
        setFromSummary(true);
        navigateTo('record');
    },

    doGenerate: function () {
        var self = this;
        var store = getStore();

        if (!store.headerAnswers['甲方名称']) {
            wx.showToast({ title: '请填写甲方名称', icon: 'none' });
            return;
        }

        if (store.itemList.length === 0) {
            wx.showToast({ title: '请至少添加一条货物', icon: 'none' });
            return;
        }

        console.log('[Summary] 准备生成合同');
        console.log('[Summary] headerAnswers:', JSON.stringify(store.headerAnswers));
        console.log('[Summary] itemList:', JSON.stringify(store.itemList));
        console.log('[Summary] 货物数量:', store.itemList.length);

        self.setData({ showLoading: true, loadingText: '生成合同中…' });

        generateContract('采购合同', store.headerAnswers, store.itemList).then(function (result) {
            var fileManager = wx.getFileSystemManager();
            var localPath = wx.env.USER_DATA_PATH + '/' + result.filename;

            fileManager.writeFile({
                filePath: localPath,
                data: result.blob,
                encoding: 'binary',
                success: function () {
                    setLastFilename(localPath);
                    wx.navigateTo({
                        url: '/pages/contract/success/success',
                    });
                },
                fail: function (err) {
                    wx.showToast({ title: '文件保存失败', icon: 'none' });
                    console.error('File write error:', err);
                },
            });
        }).catch(function (err) {
            wx.showToast({ title: '生成失败: ' + err.message, icon: 'none' });
        }).finally(function () {
            self.setData({ showLoading: false });
        });
    },
});