import {it,expect} from 'vitest';
import {timeToLogical,logicalToTime,moveDrawing,sanitizeAnnotation,isTypingTarget,validAnchors,type Drawing} from './chartDrawings';
const rows=[0,60,180].map(time=>({time,open:10,high:12,low:9,close:11,volume:1}));
it('roundtrips absolute interval-end anchors through gaps, prepends and native timeframes',()=>{
 expect(timeToLogical(60,rows,60)).toBe(0);expect(timeToLogical(180,rows,60)).toBe(1.5);
 expect(logicalToTime(1.5,rows,60)).toBe(180);
 const prepended=[{...rows[0],time:-60},...rows];expect(timeToLogical(180,prepended,60)).toBe(2.5);
 const coarse=[{...rows[0],time:0},{...rows[0],time:240}];expect(timeToLogical(180,coarse,240)).toBe(-0.25);
 for(const time of [1,60,75,120,180,240,360])expect(logicalToTime(timeToLogical(time,rows,60)!,rows,60)).toBe(time);
 expect(timeToLogical(60,[],60)).toBeNull();
});
it('moves anchors without mutating saved input and bounds text/coordinates',()=>{
 const drawing:Drawing={id:'d1',kind:'trend',anchors:[{time:100,price:10},{time:200,price:20}],color:'#abcdef',width:2,style:'solid',text:'',visible:true,locked:false};
 const moved=moveDrawing(drawing,{time:100,price:10},{time:125,price:15});
 expect(moved.anchors).toEqual([{time:125,price:15},{time:225,price:25}]);expect(drawing.anchors[0]).toEqual({time:100,price:10});
 expect(sanitizeAnnotation('A\nB\x00<script>')).toBe('A B <script>');expect(sanitizeAnnotation('a'.repeat(300))).toHaveLength(200);
 expect(validAnchors([{time:1,price:1}])).toBe(true);expect(validAnchors([{time:NaN,price:1}])).toBe(false);
 for(const tag of ['input','textarea','select'])expect(isTypingTarget(document.createElement(tag))).toBe(true);
 expect(isTypingTarget(document.createElement('button'))).toBe(false);
});
