import ccxt from 'ccxt';

async function testOKX() {
    const exchange = new ccxt.okx({ enableRateLimit: true });
    console.log('Loading markets...');
    const markets = await exchange.loadMarkets();
    const symbols = Object.keys(markets);
    console.log('Total symbols:', symbols.length);

    let swapUsdt = 0;
    let active = 0;

    for (const [s, _m] of Object.entries(markets)) {
        const m = _m as any;
        if (m.swap) {
            if (m.quote === 'USDT') {
                swapUsdt++;
                if (m.active) {
                    active++;
                }
            }
        }
    }
    console.log('Swap USDT:', swapUsdt);
    console.log('Active Swap USDT:', active);

    const validSymbols = symbols.filter(s => {
        const m = markets[s] as any;
        return m && m.swap && m.quote === 'USDT' && m.active;
    });
    console.log('Valid symbols length:', validSymbols.length);

    if (validSymbols.length > 0) {
        console.log('Fetching tickers...');
        const tickers = await exchange.fetchTickers(validSymbols);

        const btc = tickers['BTC/USDT:USDT'];
        if (btc) {
            console.log('BTC Ticker:', {
                quoteVolume: btc.quoteVolume,
                baseVolume: btc.baseVolume,
                last: btc.last,
                volCcy24h: btc.info.volCcy24h,
                vol24h: btc.info.vol24h,
                derivedVolume: (btc.baseVolume || 0) * (btc.last || 0)
            });
        }
        const tickerValues = Object.values(tickers);
        if (tickerValues.length > 0) {
            console.log('Sample ticker:', tickerValues[0]);
        }

        const qualified = Object.entries(tickers)
            .filter(([_, t]: [string, any]) => (t.quoteVolume || 0) > 20_000_000)
            .map(([sym, t]: [string, any]) => ({ symbol: sym.split('/')[0], price: t.last, vol: t.quoteVolume }))
            .slice(0, 25);

        console.log('Qualified symbols length:', qualified.length);
        console.log('Sample qualified:', qualified);
    }
}

testOKX().catch(console.error);
