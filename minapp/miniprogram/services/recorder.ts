export type RecordState = 'idle' | 'recording' | 'processing';

export interface RecorderEvents {
    onStateChange?: (state: RecordState) => void;
    onResult?: (text: string) => void;
    onError?: (error: string) => void;
    onStop?: (tempFilePath: string) => void;
}

function VoiceRecorder() {
    var recorder: wx.RecorderManager | null = null;
    var tempFilePath: string = '';
    var events: RecorderEvents = {};

    function setupListeners() {
        if (!recorder) return;

        recorder.onStart(function () {
            console.log('[Recorder] 录音开始');
            tempFilePath = '';
            if (events.onStateChange) {
                events.onStateChange('recording');
            }
        });

        recorder.onStop(function (res) {
            console.log('[Recorder] 录音停止，文件路径:', res.tempFilePath);
            tempFilePath = res.tempFilePath || '';
            if (events.onStateChange) {
                events.onStateChange('processing');
            }
            if (tempFilePath) {
                if (events.onStop) {
                    events.onStop(tempFilePath);
                }
            } else {
                if (events.onError) {
                    events.onError('录音文件生成失败');
                }
                if (events.onStateChange) {
                    events.onStateChange('idle');
                }
            }
        });

        recorder.onError(function (err) {
            var errorMsg = err.errMsg || '录音失败';
            console.error('[Recorder] 录音错误:', errorMsg);
            if (events.onError) {
                events.onError(errorMsg);
            }
            if (events.onStateChange) {
                events.onStateChange('idle');
            }
        });
    }

    function setEvts(evts: RecorderEvents) {
        events = evts;
    }

    function startRecording() {
        if (!recorder) {
            if (events.onError) {
                events.onError('录音模块不可用');
            }
            return;
        }

        try {
            recorder.start({
                format: 'mp3',
                sampleRate: 16000,
                numberOfChannels: 1,
                encodeBitRate: 48000,
                duration: 60000,
            });
            console.log('[Recorder] 开始录音');
        } catch (err) {
            var errorMsg = '无法访问麦克风，请检查权限设置';
            console.error('[Recorder] 启动录音失败:', err);
            if (events.onError) {
                events.onError(errorMsg);
            }
        }
    }

    function stopRecording() {
        if (recorder) {
            recorder.stop();
            console.log('[Recorder] 请求停止录音');
        }
    }

    function getTempFilePath() {
        return tempFilePath;
    }

    recorder = wx.getRecorderManager();
    setupListeners();

    return {
        setEvents: setEvts,
        startRecording: startRecording,
        stopRecording: stopRecording,
        getTempFilePath: getTempFilePath,
    };
}

var recorderInstance: any = null;

export function getVoiceRecorder(): any {
    if (!recorderInstance) {
        recorderInstance = VoiceRecorder();
    }
    return recorderInstance;
}

export function releaseVoiceRecorder(): void {
    if (recorderInstance) {
        recorderInstance = null;
    }
}