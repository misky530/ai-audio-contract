export type RecordState = 'idle' | 'recording' | 'processing';

export interface RecorderEvents {
    onStateChange?: (state: RecordState) => void;
    onResult?: (text: string) => void;
    onError?: (error: string) => void;
    onStop?: (tempFilePath: string) => void;
}

class VoiceRecorder {
    private recorder: wx.RecorderManager | null = null;
    private tempFilePath: string = '';
    private events: RecorderEvents = {};

    constructor() {
        this.recorder = wx.getRecorderManager();
        this.setupListeners();
    }

    private setupListeners(): void {
        if (!this.recorder) return;

        this.recorder.onStart(() => {
            console.log('[Recorder] 录音开始');
            this.tempFilePath = '';
            this.events.onStateChange?.('recording');
        });

        this.recorder.onStop((res) => {
            console.log('[Recorder] 录音停止，文件路径:', res.tempFilePath);
            this.tempFilePath = res.tempFilePath || '';
            this.events.onStateChange?.('processing');
            if (this.tempFilePath) {
                this.events.onStop?.(this.tempFilePath);
            } else {
                this.events.onError?.('录音文件生成失败');
                this.events.onStateChange?.('idle');
            }
        });

        this.recorder.onError((err) => {
            const errorMsg = err.errMsg || '录音失败';
            console.error('[Recorder] 录音错误:', errorMsg);
            this.events.onError?.(errorMsg);
            this.events.onStateChange?.('idle');
        });
    }

    setEvents(events: RecorderEvents): void {
        this.events = events;
    }

    startRecording(): void {
        if (!this.recorder) {
            this.events.onError?.('录音模块不可用');
            return;
        }

        try {
            this.recorder.start({
                format: 'mp3',
                sampleRate: 16000,
                numberOfChannels: 1,
                encodeBitRate: 48000,
                duration: 60000,
            });
            console.log('[Recorder] 开始录音');
        } catch (err) {
            const errorMsg = '无法访问麦克风，请检查权限设置';
            console.error('[Recorder] 启动录音失败:', err);
            this.events.onError?.(errorMsg);
        }
    }

    stopRecording(): void {
        if (this.recorder) {
            this.recorder.stop();
            console.log('[Recorder] 请求停止录音');
        }
    }

    getTempFilePath(): string {
        return this.tempFilePath;
    }
}

let recorderInstance: VoiceRecorder | null = null;

export function getVoiceRecorder(): VoiceRecorder {
    if (!recorderInstance) {
        recorderInstance = new VoiceRecorder();
    }
    return recorderInstance;
}

export function releaseVoiceRecorder(): void {
    if (recorderInstance) {
        recorderInstance = null;
    }
}