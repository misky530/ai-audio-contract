import { startHeader } from '../../services/store';

Page({
  data: {},

  onLoad() { },

  startContract() {
    startHeader();
    wx.redirectTo({
      url: '/pages/contract/record/record',
    });
  },
});