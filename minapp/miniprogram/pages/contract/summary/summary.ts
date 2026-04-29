import { HEADER_FIELDS, ITEM_FIELDS, generateContract } from '../../../services/api';
import { getStore, editItem as editItemStore, setFromSummary, setPhase, setFieldIndex, setLastFilename, resetStore } from '../../../services/store';

interface FieldRow {
    fieldKey: string;
    label: string;
}

Page({
    data: {
        headerFields: HEADER_FIELDS,
        headerAnswers: {} as Record<string, string>,
        itemList: [] as Record<string, string>[],
        itemTitles: [] as string[],
        itemFieldRows: [] as FieldRow[],
        progress: 0,
        stepLabel: '',
        showLoading: false,
        loadingText: '生成合同中…',
    },

    onLoad() {
        this.renderSummary();
    },

    onShow() {
        this.renderSummary();
    },

    renderSummary() {
        const store = getStore();
        const itemList = store.itemList;
        const headerAnswers = store.headerAnswers;

        const itemTitles: string[] = [];
        itemList.forEach((item) => {
            const titleParts = [item['货物品牌'], item['货物型号'], item['货物品类']].filter(Boolean);
            itemTitles.push(titleParts.length > 0 ? titleParts.join(' ') : '');
        });

        const itemFieldRows = ITEM_FIELDS.filter(
            (f) => f.key !== '货物品牌' && f.key !== '货物型号' && f.key !== '货物品类'
        ).map((f) => ({
            fieldKey: f.key,
            label: f.label,
        }));

        this.setData({
            headerAnswers,
            itemList,
            itemTitles,
            itemFieldRows,
            progress: 95,
            stepLabel: '确认信息',
        });
    },

    onBack() {
        wx.navigateBack();
    },

    editHeaderField(e: any) {
        const index = e.currentTarget.dataset.index;
        setFromSummary(true);
        setPhase('header');
        setFieldIndex(index);

        const pages = getCurrentPages();
        const recordPage = pages.find((p) => p.route.includes('record'));
        if (recordPage) {
            wx.navigateBack({ delta: pages.length - recordPage.__webviewId__ - 1 });
        } else {
            wx.navigateBack();
        }
    },

    editItem(e: any) {
        const index = e.currentTarget.dataset.index;
        editItemStore(index);
        setFromSummary(true);

        const pages = getCurrentPages();
        const recordPage = pages.find((p) => p.route.includes('record'));
        if (recordPage) {
            wx.navigateBack({ delta: pages.length - recordPage.__webviewId__ - 1 });
        } else {
            wx.navigateBack();
        }
    },

    async doGenerate() {
        const store = getStore();

        if (!store.headerAnswers['甲方名称']) {
            wx.showToast({ title: '请填写甲方名称', icon: 'none' });
            return;
        }

        if (store.itemList.length === 0) {
            wx.showToast({ title: '请至少添加一条货物', icon: 'none' });
            return;
        }

        this.setData({ showLoading: true, loadingText: '生成合同中…' });

        try {
            const result = await generateContract('采购合同', store.headerAnswers, store.itemList);

            const fileManager = wx.getFileSystemManager();
            const localPath = `${wx.env.USER_DATA_PATH}/${result.filename}`;

            fileManager.writeFile({
                filePath: localPath,
                data: result.blob,
                encoding: 'binary',
                success: () => {
                    setLastFilename(localPath);
                    wx.navigateTo({
                        url: '/pages/contract/success/success',
                    });
                },
                fail: (err) => {
                    wx.showToast({ title: '文件保存失败', icon: 'none' });
                    console.error('File write error:', err);
                },
            });
        } catch (err: any) {
            wx.showToast({ title: '生成失败: ' + err.message, icon: 'none' });
        } finally {
            this.setData({ showLoading: false });
        }
    },
});