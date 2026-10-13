/** Independently authored small UI-boundary fixture; no production IO. */
import type {CurrentAgreementInput} from './currentAgreement';
export function renewReceipt(input: CurrentAgreementInput) {
  input.rawSnapshotKey = JSON.stringify(input.rows);
  input.receipt = {response:input.response, responseRevision:input.response.revision, origin:JSON.stringify(input.response.origin),
    rawSnapshotKey:input.rawSnapshotKey, requestKey:JSON.stringify([input.source,input.market,input.symbol,input.minutes,input.priceStyle]),
    settingsRevision:input.settings.revision, windowEpoch:input.windowEpoch, generation:1, calculationEpoch:2};
}
export function makeAgreementInput(): CurrentAgreementInput {
  const origin = {time:0,generation:1,contract:'native-close-engine-seeds-v1'};
  const settings: CurrentAgreementInput['settings'] = {version:1,revision:4,origins:{},instances:[
    {id:'sma',type:'sma',params:{period:1},visible:true,color:'#ffffff'},
    {id:'roc',type:'roc',params:{period:1},visible:true,color:'#ffffff'},
    {id:'cmf',type:'cmf',params:{period:1},visible:true,color:'#ffffff'},
  ]};
  const context = {source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,start:0,end:180,settings_revision:4,generation:1,origin:0};
  const input: CurrentAgreementInput = {
    source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,priceStyle:'candles',windowEpoch:1,settings,
    rows:[100,105,110,999].map((close,index) => ({time:index*60,open:close,high:close+1,low:close-1,close,volume:1,confirmation:index===3?'forming':'synthetic_closed'})),
    response:{status:'ready',revision:'a'.repeat(64),origin,settings:{...structuredClone(settings),origins:{1:{...origin}}},
      times:[60,120,180,240],columns:{sma:{value:[100,104,105,null]},roc:{value:[null,5,5,null]},cmf:{value:[0,0,0,null]}},
      projections:{version:1,contract:'ichimoku-raw-ordinal-v1',context:{...context},horizon:240,raw_times:[60,120,180,240],instances:{}},
      indicator_events:{version:1,contract:'confirmed-vmc-events-v1',context:{...context},horizon:240,instances:{}}},
    receipt:null,rawSnapshotKey:'',active:true,fresh:true,historical:false,loading:false,loaded:true,saving:false,error:'',
  };
  renewReceipt(input); return input;
}
