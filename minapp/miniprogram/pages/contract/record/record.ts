import { HEADER_FIELDS, ITEM_FIELDS, transcribeAudio } from '../../../services/api';
import { getVoiceRecorder, releaseVoiceRecorder } from '../../../services/recorder';
import {
    getStore,
    saveField,
    saveCurrentItem,
    startNewItem,
    setFromSummary,
    setFieldIndex,
    navigateTo,
} from '../../../services/store';

Page({
    data: {
        phase: 'header',
        fieldIndex: 0,
        fromSummary: false,
        editingItem: -1,
        currentField: {},
        progress: 0,
        stepLabel: '',
        nextBtnText: '',
        itemNo: 1,
        resultText: '',
        recordState: 'idle',
        recordStatusText: '点击麦克风开始录音',
        suggestions: [],
        showLoading: false,
        loadingText: '识别中…',
    },

    _recorder: null,
    _fields: [],
    _headerFields: HEADER_FIELDS,
    _itemFields: ITEM_FIELDS,

    onLoad: function () {
        console.log('[RecordPage] 页面加载');
        this._fields = this._headerFields;
        this.initRecorder();
        this.renderField();
    },

    onUnload: function () {
        console.log('[RecordPage] 页面卸载');
        releaseVoiceRecorder();
    },

    initRecorder: function () {
        var self = this;
        var recorder = getVoiceRecorder();
        this._recorder = recorder;

        recorder.setEvents({
            onStateChange: function (state) {
                console.log('[RecordPage] 录音状态变化:', state);
                self.setData({ recordState: state });

                if (state === 'recording') {
                    self.setData({ recordStatusText: '录音中… 点击停止' });
                } else if (state === 'processing') {
                    self.setData({ recordStatusText: '识别中…' });
                } else {
                    self.setData({ recordStatusText: '点击麦克风开始录音' });
                }
            },
            onStop: function (tempFilePath) {
                console.log('[RecordPage] 录音停止，文件路径:', tempFilePath);
                if (tempFilePath) {
                    self.uploadAudio(tempFilePath);
                } else {
                    wx.showToast({ title: '录音文件生成失败', icon: 'none' });
                    self.setData({ recordState: 'idle', recordStatusText: '录音失败，请重试' });
                }
            },
            onResult: function (text) {
                self.setData({ resultText: text });
                self.setData({ recordStatusText: '识别完成，可修改后继续' });
            },
            onError: function (error) {
                console.error('[RecordPage] 录音错误:', error);
                wx.showToast({ title: error, icon: 'none' });
                self.setData({ recordStatusText: '录音失败，请重试' });
            },
        });
    },

    renderField: function () {
        var self = this;
        var store = getStore();
        var phase = store.phase;
        var fieldIndex = store.fieldIndex;
        var fields = phase === 'header' ? this._headerFields : this._itemFields;
        this._fields = fields;

        var currentField = fields[fieldIndex] || fields[0];
        var totalFields = this._headerFields.length + store.itemList.length * this._itemFields.length;
        var done = (phase === 'header' ? 0 : this._headerFields.length) + fieldIndex;
        var progress = totalFields > 0 ? (done / totalFields) * 100 : 0;

        var stepLabel = '';
        if (phase === 'header') {
            stepLabel = '甲方信息 ' + (fieldIndex + 1) + ' / ' + this._headerFields.length;
        } else {
            var itemNo = store.editingItem >= 0 ? store.editingItem + 1 : store.itemList.length + 1;
            stepLabel = '第 ' + itemNo + ' 条货物 ' + (fieldIndex + 1) + ' / ' + this._itemFields.length;
        }

        var existing = phase === 'header'
            ? store.headerAnswers[currentField.key]
            : store.currentItem[currentField.key];

        var isLast = fieldIndex === fields.length - 1;
        var nextBtnText = isLast
            ? (phase === 'header' ? '开始录货物 →' : '完成此条货物 →')
            : '下一项 →';

        if (currentField.key === '单价') {
            nextBtnText = store.fromSummary ? '保存并返回 →' : '完成此条货物 →';
        }

        if (store.fromSummary) {
            nextBtnText = '保存并返回 →';
        }

        var itemNo = store.editingItem >= 0 ? store.editingItem + 1 : store.itemList.length + 1;

        this.setData({
            phase: phase,
            fieldIndex: fieldIndex,
            fromSummary: store.fromSummary,
            editingItem: store.editingItem,
            currentField: currentField,
            progress: progress,
            stepLabel: stepLabel,
            nextBtnText: nextBtnText,
            itemNo: itemNo,
            resultText: existing || '',
            suggestions: [],
        });
    },

    speakHint: function () {
        if (!wx.canIUse('createInnerAudioContext')) {
            wx.showToast({ title: '当前版本不支持朗读功能', icon: 'none' });
            return;
        }

        var innerAudioContext = wx.createInnerAudioContext();
        var field = this.data.currentField;

        innerAudioContext.onError(function () {
            wx.showToast({ title: '朗读失败', icon: 'none' });
            innerAudioContext.destroy();
        });

        innerAudioContext.onPlay(function () {
            setTimeout(function () {
                innerAudioContext.destroy();
            }, 5000);
        });

        var hint = field.hint;
        var speakText = hint.replace(/例如：/g, '').replace(/例如/g, '');

        wx.showToast({
            title: '朗读: ' + speakText.substring(0, 10) + '...',
            icon: 'none',
            duration: 2000,
        });
    },

    checkRecordPermission: function (callback) {
        var self = this;
        wx.getSetting({
            success: function (res) {
                if (!res.authSetting['scope.record']) {
                    wx.authorize({
                        scope: 'scope.record',
                        success: function () {
                            callback(true);
                        },
                        fail: function () {
                            wx.showModal({
                                title: '需要麦克风权限',
                                content: '请在设置中开启麦克风权限',
                                showCancel: false,
                            });
                            callback(false);
                        }
                    });
                } else {
                    callback(true);
                }
            },
            fail: function () {
                callback(false);
            }
        });
    },

    toggleRecord: function () {
        console.log('[RecordPage] 点击录音按钮，当前状态:', this.data.recordState);

        var self = this;
        var state = this.data.recordState;

        if (state === 'idle') {
            this.checkRecordPermission(function (granted) {
                if (granted) {
                    self.startRecord();
                }
            });
        } else if (state === 'recording') {
            self.stopRecord();
        }
    },

    startRecord: function () {
        console.log('[RecordPage] 开始录音');
        try {
            var recorder = this._recorder;
            if (recorder) {
                recorder.startRecording();
            } else {
                console.error('[RecordPage] 录音器未初始化');
                wx.showToast({ title: '录音器未初始化', icon: 'none' });
            }
        } catch (err) {
            console.error('[RecordPage] 启动录音异常:', err);
            wx.showToast({ title: '无法访问麦克风', icon: 'none' });
        }
    },

    stopRecord: function () {
        console.log('[RecordPage] 停止录音');
        var recorder = this._recorder;
        if (recorder) {
            recorder.stopRecording();
        } else {
            console.error('[RecordPage] 录音器未初始化');
        }
    },

    uploadAudio: function (tempFilePath) {
        var self = this;
        if (!tempFilePath) {
            wx.showToast({ title: '录音文件无效', icon: 'none' });
            this.setData({ recordState: 'idle', recordStatusText: '录音文件无效' });
            return;
        }

        console.log('[RecordPage] 开始上传音频:', tempFilePath);
        this.setData({ showLoading: true, loadingText: '识别中…', recordState: 'processing' });

        var field = this.data.currentField;
        console.log('[RecordPage] 调用识别接口: ' + field.key);

        transcribeAudio(tempFilePath, field.key, 'zh').then(function (result) {
            console.log('[RecordPage] 识别成功:', result.text);
            self.setData({
                resultText: result.text || '',
                suggestions: result.suggestions || [],
                recordState: 'idle',
                recordStatusText: '识别完成，可修改后继续',
                showLoading: false,
            });
        }).catch(function (err) {
            console.error('[RecordPage] 识别失败:', err.message);
            wx.showToast({ title: '识别失败: ' + err.message, icon: 'none', duration: 3000 });
            self.setData({
                recordState: 'idle',
                recordStatusText: '识别失败，请重录',
                showLoading: false,
            });
        });
    },

    onInputChange: function (e) {
        this.setData({ resultText: e.detail.value });
    },

    applySuggestion: function (e) {
        var text = e.currentTarget.dataset.text;
        this.setData({ resultText: text, suggestions: [] });
    },

    goPrev: function () {
        var value = this.data.resultText.trim();
        saveField(this.data.currentField.key, value);

        if (this.data.fromSummary) {
            setFromSummary(false);
            if (this.data.phase === 'header') {
                navigateTo('summary');
            } else {
                navigateTo('itemlist');
            }
            return;
        }

        if (this.data.fieldIndex > 0) {
            var newIndex = this.data.fieldIndex - 1;
            setFieldIndex(newIndex);
            this.renderField();
        } else if (this.data.phase === 'item') {
            navigateTo('itemlist');
        }
    },

    goNext: function () {
        var value = this.data.resultText.trim();
        saveField(this.data.currentField.key, value);

        if (this.data.fromSummary) {
            setFromSummary(false);
            if (this.data.phase === 'header') {
                navigateTo('summary');
            } else {
                saveCurrentItem();
                navigateTo('itemlist');
            }
            return;
        }

        var fields = this.data.phase === 'header' ? this._headerFields : this._itemFields;

        if (this.data.fieldIndex < fields.length - 1) {
            var newIndex = this.data.fieldIndex + 1;
            setFieldIndex(newIndex);
            this.renderField();
        } else {
            if (this.data.phase === 'header') {
                startNewItem();
                this._fields = this._itemFields;
                this.renderField();
            } else {
                saveCurrentItem();
                navigateTo('itemlist');
            }
        }
    },
});