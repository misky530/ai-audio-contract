import { getStore, getLastFilename, resetStore, startHeader } from '../../../services/store';

Page({
    data: {
        filename: '',
        fileSize: '',
        fileType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },

    onLoad() {
        const store = getStore();
        const filename = store.lastFilename || '采购合同.docx';

        const filePath = filename.startsWith('/')
            ? filename
            : `${wx.env.USER_DATA_PATH}/${filename}`;

        let fileSize = '';
        try {
            const fileManager = wx.getFileSystemManager();
            const fileInfo = fileManager.statSync(filePath);
            const sizeKB = (fileInfo.size / 1024).toFixed(1);
            fileSize = `${sizeKB} KB`;
        } catch {
            fileSize = '未知';
        }

        const displayFilename = store.lastFilename || '采购合同.docx';

        this.setData({
            filename: displayFilename,
            fileSize,
        });
    },

    triggerDownload() {
        const store = getStore();
        const filePath = store.lastFilename;

        if (!filePath) {
            wx.showToast({ title: '请先生成合同', icon: 'none' });
            return;
        }

        wx.openDocument({
            filePath: filePath,
            fileType: 'docx',
            showMenu: true,
            success: () => {
            },
            fail: (err) => {
                wx.showToast({ title: '打开文件失败', icon: 'none' });
                console.error('Open document error:', err);
            },
        });
    },

    restart() {
        wx.showModal({
            title: '确认重新录入',
            content: '确定要清空当前所有数据，重新开始吗？',
            success: (res) => {
                if (res.confirm) {
                    resetStore();
                    startHeader();

                    const pages = getCurrentPages();
                    const needRedirect = pages.some(
                        (p) => !p.route.includes('contract/record')
                    );

                    if (needRedirect) {
                        wx.redirectTo({
                            url: '/pages/contract/record/record',
                        });
                    } else {
                        const recordPage = pages.find((p) => p.route.includes('contract/record'));
                        if (recordPage) {
                            recordPage.onLoad();
                        }
                    }
                }
            },
        });
    },
});