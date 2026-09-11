export function OrderBookPanel({book,age,active}:{book:any;age?:number|null;active:boolean}){
 const valid=active&&book?.valid&&age!=null&&age<=15;
 const rows=(side:string)=>(book?.[side]??[]).slice(0,15) as string[][];
 const max=Math.max(1,...[...rows('asks'),...rows('bids')].map(r=>Number(r[1])));
 return <section className={`order-book ${valid?'':'stale'}`} aria-label="Order book"><h3>Order book <small>{valid?'15 levels':'Waiting / stale'}</small></h3><div className="book-columns"><span>Price</span><span>Size</span></div>{(['asks','bids'] as const).map(side=><div key={side} className={side}>{rows(side).map(([price,size])=><div className="book-row" key={price} style={{background:`linear-gradient(to left, ${side==='bids'?'#42cda822':'#ed7e8622'} ${Number(size)/max*100}%, transparent 0)`}}><span>{price}</span><span>{size}</span></div>)}</div>)}</section>;
}
export function TradeTape({trades,active}:{trades:any[];active:boolean}){
 return <section className={`trade-tape ${active?'':'stale'}`} aria-label="Recent trades"><h3>Recent trades</h3><div className="tape-rows">{trades.slice(0,50).map(t=><div className={t.side==='Buy'?'positive':'negative'} key={t.id}><time>{new Date(t.time).toISOString().slice(11,19)}</time><span>{t.price}</span><span>{t.size}</span><small>{t.side}</small></div>)}</div><small>Observed taker side · gaps are not recovered</small></section>;
}
