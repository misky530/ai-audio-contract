import type { Field } from '../../../types/contract';
import { HEADER_FIELDS, ITEM_FIELDS, transcribeAudio } from '../../../services/api';
import { getVoiceRecorder, releaseVoiceRecorder, type RecordState } from '../../../services/recorder';
import {
    getStore,
    saveField,
    saveCurrentItem,
    startNewItem,
    editLastItem,
    setFromSummary,
    navigateTo,
} from '../../../services/store';

interface Suggestion {
    text: string;
}

Page({
    data: {
        phase: 'header' as 'header' | 'item',
        fieldIndex: 0,
        fromSummary: false,
        editingItem: -1,
        currentField: {} as Field,
        progress: 0,
        stepLabel: '',
        nextBtnText: '',
        itemNo: 1,
        resultText: '',
        recordState: 'idle' as RecordState,
        recordStatusText: '点击麦克风开始录音',
        suggestions: [] as Suggestion[],
        showLoading: false,
        loadingText: '识别中…',
    },

    private: {
        recorder: null as any,
        fields: [] as Field[],
        headerFields: HEADER_FIELDS,
        itemFields: ITEM_FIELDS,
    },

    onLoad() {
        console.log('[RecordPage] 页面加载');
        this.private.fields = this.private.headerFields;
        this.initRecorder();
        this.renderField();
    },

    onUnload() {
        console.log('[RecordPage] 页面卸载');
        releaseVoiceRecorder();
    },

    initRecorder() {
        const recorder = getVoiceRecorder();
        this.private.recorder = recorder;

        recorder.setEvents({
            onStateChange: (state: RecordState) => {
                console.log('[RecordPage] 录音状态变化:', state);
                this.setData({ recordState: state });

                if (state === 'recording') {
                    this.setData({ recordStatusText: '录音中… 点击停止' });
                } else if (state === 'processing') {
                    this.setData({ recordStatusText: '识别中…' });
                } else {
                    this.setData({ recordStatusText: '点击麦克风开始录音' });
                }
            },
            onStop: (tempFilePath: string) => {
                console.log('[RecordPage] 录音停止，文件路径:', tempFilePath);
                if (tempFilePath) {
                    this.uploadAudio(tempFilePath);
                } else {
                    wx.showToast({ title: '录音文件生成失败', icon: 'none' });
                    this.setData({ recordState: 'idle', recordStatusText: '录音失败，请重试' });
                }
            },
            onResult: (text: string) => {
                this.setData({ resultText: text });
                this.setData({ recordStatusText: '识别完成，可修改后继续' });
            },
            onError: (error: string) => {
                console.error('[RecordPage] 录音错误:', error);
                wx.showToast({ title: error, icon: 'none' });
                this.setData({ recordStatusText: '录音失败，请重试' });
            },
        });
    },

    renderField() {
        const store = getStore();
        const phase = store.phase;
        const fieldIndex = store.fieldIndex;
        const fields = phase === 'header' ? this.private.headerFields : this.private.itemFields;
        this.private.fields = fields;

        const currentField = fields[fieldIndex] || fields[0];
        const totalFields = this.private.headerFields.length + store.itemList.length * this.private.itemFields.length;
        const done = (phase === 'header' ? 0 : this.private.headerFields.length) + fieldIndex;
        const progress = totalFields > 0 ? (done / totalFields) * 100 : 0;

        let stepLabel = '';
        if (phase === 'header') {
            stepLabel = `甲方信息 ${fieldIndex + 1} / ${this.private.headerFields.length}`;
        } else {
            const itemNo = store.editingItem >= 0 ? store.editingItem + 1 : store.itemList.length + 1;
            stepLabel = `第 ${itemNo} 条货物 ${fieldIndex + 1} / ${this.private.itemFields.length}`;
        }

        const existing = phase === 'header'
            ? store.headerAnswers[currentField.key]
            : store.currentItem[currentField.key];

        const isLast = fieldIndex === fields.length - 1;
        let nextBtnText = isLast
            ? (phase === 'header' ? '开始录货物 →' : '完成此条货物 →')
            : '下一项 →';

        if (currentField.key === '单价') {
            nextBtnText = store.fromSummary ? '保存并返回 →' : '完成此条货物 →';
        }

        if (store.fromSummary) {
            nextBtnText = '保存并返回 →';
        }

        const itemNo = store.editingItem >= 0 ? store.editingItem + 1 : store.itemList.length + 1;

        this.setData({
            phase,
            fieldIndex,
            fromSummary: store.fromSummary,
            editingItem: store.editingItem,
            currentField,
            progress,
            stepLabel,
            nextBtnText,
            itemNo,
            resultText: existing || '',
            suggestions: [],
        });
    },

    speakHint() {
        if (!wx.canIUse('createInnerAudioContext')) {
            wx.showToast({ title: '当前版本不支持朗读功能', icon: 'none' });
            return;
        }

        const innerAudioContext = wx.createInnerAudioContext();
        const field = this.data.currentField;

        innerAudioContext.onError = () => {
            wx.showToast({ title: '朗读失败', icon: 'none' });
            innerAudioContext.destroy();
        };

        innerAudioContext.onPlay = () => {
            setTimeout(() => {
                innerAudioContext.destroy();
            }, 5000);
        };

        const hint = field.hint;
        const speakText = hint.replace(/例如：/g, '').replace(/例如/g, '');

        wx.showToast({
            title: `朗读: ${speakText.substring(0, 10)}...`,
            icon: 'none',
            duration: 2000,
        });
    },

    toggleRecord() {
        const state = this.data.recordState;

        if (state === 'idle') {
            this.startRecord();
        } else if (state === 'recording') {
            this.stopRecord();
        }
    },

    startRecord() {
        try {
            const recorder = this.private.recorder;
            if (recorder) {
                recorder.startRecording();
                console.log('[RecordPage] 开始录音');
            }
        } catch (err) {
            wx.showToast({ title: '无法访问麦克风', icon: 'none' });
        }
    },

    stopRecord() {
        const recorder = this.private.recorder;
        if (recorder) {
            recorder.stopRecording();
            console.log('[RecordPage] 请求停止录音');
        }
    },

    async uploadAudio(tempFilePath: string) {
        if (!tempFilePath) {
            wx.showToast({ title: '录音文件无效', icon: 'none' });
            this.setData({ recordState: 'idle', recordStatusText: '录音文件无效' });
            return;
        }

        console.log('[RecordPage] 开始上传音频:', tempFilePath);
        this.setData({ showLoading: true, loadingText: '识别中…', recordState: 'processing' });

        try {
            const field = this.data.currentField;
            console.log(`[RecordPage] 调用识别接口: ${field.key}`);

            const result = await transcribeAudio(tempFilePath, field.key, 'zh');

            console.log('[RecordPage] 识别成功:', result.text);
            this.setData({
                resultText: result.text || '',
                suggestions: result.suggestions || [],
                recordState: 'idle',
                recordStatusText: '识别完成，可修改后继续',
                showLoading: false,
            });
        } catch (err: any) {
            console.error('[RecordPage] 识别失败:', err.message);
            wx.showToast({ title: '识别失败: ' + err.message, icon: 'none', duration: 3000 });
            this.setData({
                recordState: 'idle',
                recordStatusText: '识别失败，请重录',
                showLoading: false,
            });
        }
    },

    onInputChange(e: any) {
        this.setData({ resultText: e.detail.value });
    },

    applySuggestion(e: any) {
        const text = e.currentTarget.dataset.text;
        this.setData({ resultText: text, suggestions: [] });
    },

    goPrev() {
        const store = getStore();
        const value = this.data.resultText.trim();
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
            const newIndex = this.data.fieldIndex - 1;
            const newStore = getStore();
            newStore.fieldIndex = newIndex;
            this.renderField();
        } else if (this.data.phase === 'item') {
            navigateTo('itemlist');
        }
    },

    goNext() {
        const store = getStore();
        const value = this.data.resultText.trim();
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

        const fields = this.data.phase === 'header' ? this.private.headerFields : this.private.itemFields;

        if (this.data.fieldIndex < fields.length - 1) {
            store.fieldIndex = this.data.fieldIndex + 1;
            this.renderField();
        } else {
            if (this.data.phase === 'header') {
                startNewItem();
                this.private.fields = this.private.itemFields;
                this.renderField();
            } else {
                saveCurrentItem();
                navigateTo('itemlist');
            }
        }
    },
});