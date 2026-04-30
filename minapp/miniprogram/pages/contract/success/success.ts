import { getStore, getLastFilename, resetStore, startHeader } from '../../../services/store';

Page({
    data: {
        filename: '',
        fileSize: '',
        fileType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },

    onLoad: function () {
        var store = getStore();
        var filename = store.lastFilename || '采购合同.docx';

        var filePath = filename.indexOf('/') === 0
            ? filename
            : wx.env.USER_DATA_PATH + '/' + filename;

        var fileSize = '';
        try {
            var fileManager = wx.getFileSystemManager();
            var fileInfo = fileManager.statSync(filePath);
            var sizeKB = (fileInfo.size / 1024).toFixed(1);
            fileSize = sizeKB + ' KB';
        } catch (e) {
            fileSize = '未知';
        }

        var displayFilename = store.lastFilename || '采购合同.docx';

        this.setData({
            filename: displayFilename,
            fileSize: fileSize,
        });
    },

    triggerDownload: function () {
        var store = getStore();
        var filePath = store.lastFilename;

        if (!filePath) {
            wx.showToast({ title: '请先生成合同', icon: 'none' });
            return;
        }

        wx.openDocument({
            filePath: filePath,
            fileType: 'docx',
            showMenu: true,
            success: function () {
            },
            fail: function (err) {
                wx.showToast({ title: '打开文件失败', icon: 'none' });
                console.error('Open document error:', err);
            },
        });
    },

    restart: function () {
        var self = this;
        wx.showModal({
            title: '确认重新录入',
            content: '确定要清空当前所有数据，重新开始吗？',
            success: function (res) {
                if (res.confirm) {
                    resetStore();
                    startHeader();

                    var pages = getCurrentPages();
                    var needRedirect = pages.some(function (p) {
                        return p.route.indexOf('contract/record') === -1;
                    });

                    if (needRedirect) {
                        wx.redirectTo({
                            url: '/pages/contract/record/record',
                        });
                    } else {
                        var recordPage = null;
                        for (var i = 0; i < pages.length; i++) {
                            if (pages[i].route.indexOf('contract/record') !== -1) {
                                recordPage = pages[i];
                                break;
                            }
                        }
                        if (recordPage && recordPage.onLoad) {
                            recordPage.onLoad();
                        }
                    }
                }
            },
        });
    },
});