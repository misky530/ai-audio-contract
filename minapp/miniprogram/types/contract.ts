export interface Field {
  key: string;
  label: string;
  hint: string;
}

export interface HeaderData {
  甲方名称?: string;
  甲方联系人?: string;
  甲方电话?: string;
  [key: string]: string | undefined;
}

export interface ItemData {
  货物品类?: string;
  货物品牌?: string;
  货物型号?: string;
  货物规格?: string;
  数量?: string;
  单价?: string;
  [key: string]: string | undefined;
}

export interface ContractData {
  header: HeaderData;
  items: ItemData[];
}

export interface TranscribeResponse {
  text: string;
  suggestions?: Array<{ text: string }>;
}

export interface GenerateResponse {
  filename: string;
  content: string;
}

export type Phase = 'header' | 'item';
export type PageType = 'record' | 'itemlist' | 'summary' | 'success';