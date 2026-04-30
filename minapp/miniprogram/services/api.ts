import type { Field, HeaderData, ItemData, TranscribeResponse } from '../types/contract';

const API_BASE = 'https://quarters-fresh-aggregate.ngrok-free.dev';

const HEADER_FIELDS: Field[] = [
    { key: '甲方名称', label: '甲方公司名称', hint: '请说出对方公司全称，例如：北京星辰科技有限公司' },
    { key: '甲方联系人', label: '甲方联系人', hint: '请说出对方联系人姓名，例如：张伟' },
    { key: '甲方电话', label: '甲方联系电话', hint: '请逐字说出电话号码，例如：一三八零零一三八零零零' },
];

const ITEM_FIELDS: Field[] = [
    { key: '货物品类', label: '货物品类', hint: '请说出设备类型，例如：笔记本电脑、服务器' },
    { key: '货物品牌', label: '货物品牌', hint: '请说出品牌名称，例如：联想、戴尔、华为' },
    { key: '货物型号', label: '货物型号', hint: '请说出具体型号，例如：ThinkPad X1 Carbon Gen12' },
    { key: '货物规格', label: '货物规格配置', hint: '请说出主要配置，例如：十六G内存 五百一十二G固态' },
    { key: '数量', label: '采购数量', hint: '请说出数量和单位，例如：五十台' },
    { key: '单价', label: '单价（元）', hint: '请说出单件价格，例如：九千八百元。不知道可直接点下一项跳过' },
];

function request<T>(options: {
    url: string;
    method?: string;
    data?: any;
    header?: Record<string, string>;
}): Promise<T> {
    return new Promise((resolve, reject) => {
        wx.request({
            ...options,
            success: (res) => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(res.data as T);
                } else {
                    const data = res.data as any;
                    const errMsg = (data && data.detail) ? data.detail : '请求失败: ' + res.statusCode;
                    reject(new Error(errMsg));
                }
            },
            fail: (err) => {
                reject(new Error(err.errMsg || '网络请求失败'));
            },
        });
    });
}

export async function fetchFields(): Promise<{ header_fields: Field[]; item_fields: Field[] }> {
    try {
        const data = await request<{ header_fields: Field[]; item_fields: Field[] }>({
            url: API_BASE + '/fields',
        });
        return {
            header_fields: data.header_fields || HEADER_FIELDS,
            item_fields: data.item_fields || ITEM_FIELDS,
        };
    } catch {
        return { header_fields: HEADER_FIELDS, item_fields: ITEM_FIELDS };
    }
}

export async function transcribeAudio(
    audioFilePath: string,
    fieldKey: string,
    language: string = 'zh'
): Promise<TranscribeResponse> {
    console.log('[API] 开始上传音频: ' + audioFilePath + ', fieldKey: ' + fieldKey);

    return new Promise(function (resolve, reject) {
        var fileName = 'audio_' + Date.now() + '.mp3';

        wx.uploadFile({
            url: API_BASE + '/transcribe/' + encodeURIComponent(fieldKey),
            filePath: audioFilePath,
            name: 'audio',
            fileName: fileName,
            formData: {
                language: language,
            },
            success: function (res) {
                console.log('[API] 上传响应: status=' + res.statusCode + ', data=' + res.data);

                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        var data = JSON.parse(res.data);
                        console.log('[API] 识别成功:', data.text);
                        resolve(data);
                    } catch (parseErr) {
                        console.error('[API] 解析响应失败:', parseErr);
                        reject(new Error('解析响应失败'));
                    }
                } else {
                    var errorMsg = '识别失败: ' + res.statusCode;
                    try {
                        var data = JSON.parse(res.data);
                        errorMsg = (data && (data.detail || data.message)) ? (data.detail || data.message) : errorMsg;
                    } catch (e) {
                        errorMsg = res.data || errorMsg;
                    }
                    console.error('[API] 识别失败:', errorMsg);
                    reject(new Error(errorMsg));
                }
            },
            fail: function (err) {
                var errorMsg = err.errMsg || '上传音频失败';
                console.error('[API] 上传失败:', errorMsg);
                reject(new Error(errorMsg));
            },
        });
    });
}

export async function generateContract(
    contractType: string,
    voiceData: HeaderData,
    items: ItemData[]
): Promise<{ blob: ArrayBuffer; filename: string }> {
    console.log('[API] 开始生成合同');

    var formattedItems = items.map(function (item) {
        return {
            "单价": item['单价'] || '',
            "数量": item['数量'] || '',
            "货物品牌": item['货物品牌'] || '',
            "货物品类": item['货物品类'] || '',
            "货物型号": item['货物型号'] || '',
            "货物规格": item['货物规格'] || '',
        };
    });

    var formattedVoiceData = {
        "甲方名称": voiceData['甲方名称'] || '',
        "甲方地址": voiceData['甲方地址'] || '',
        "甲方电话": voiceData['甲方电话'] || '',
        "甲方联系人": voiceData['甲方联系人'] || '',
    };

    var requestData = {
        contract_type: contractType,
        items: formattedItems,
        voice_data: formattedVoiceData,
    };

    console.log('[API] 请求数据:', JSON.stringify(requestData));
    console.log('[API] 货物数量:', formattedItems.length);

    return new Promise(function (resolve, reject) {
        wx.request({
            url: API_BASE + '/generate',
            method: 'POST',
            header: {
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': '1',
            },
            data: requestData,
            responseType: 'arraybuffer',
            success: function (res) {
                console.log('[API] 生成响应: status=' + res.statusCode);

                if (res.statusCode >= 200 && res.statusCode < 300) {
                    var cd = (res.header && res.header['Content-Disposition']) ? res.header['Content-Disposition'] : '';
                    var match = cd.match(/filename\*=UTF-8''(.+)/);
                    var filename = match ? decodeURIComponent(match[1]) : '采购合同.docx';
                    console.log('[API] 生成成功:', filename);
                    resolve({
                        blob: res.data as ArrayBuffer,
                        filename: filename,
                    });
                } else {
                    var errorMsg = '生成失败: ' + res.statusCode;
                    try {
                        var uint8Array = new Uint8Array(res.data as ArrayBuffer);
                        var jsonStr = String.fromCharCode.apply(null, uint8Array as any);
                        var jsonData = JSON.parse(jsonStr);
                        errorMsg = (jsonData && jsonData.detail) ? jsonData.detail : errorMsg;
                    } catch (e) { }
                    console.error('[API] 生成失败:', errorMsg);
                    reject(new Error(errorMsg));
                }
            },
            fail: function (err) {
                var errorMsg = err.errMsg || '生成请求失败';
                console.error('[API] 生成请求失败:', errorMsg);
                reject(new Error(errorMsg));
            },
        });
    });
}

export { HEADER_FIELDS, ITEM_FIELDS };