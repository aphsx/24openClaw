"""
ClawBot AI - LIVE SYSTEM TEST
Tests ALL components with real data from the internet.
"""

import asyncio
import json
import traceback
from datetime import datetime

# Test results
results = {}

async def test_news_collector():
    """Test news collection (RSS + scraping)"""
    print("\n" + "="*60)
    print("📰 TEST 1: News Collector (RSS + Scraping)")
    print("="*60)
    
    from src.collectors.news_collector import NewsCollector
    collector = NewsCollector()
    
    try:
        result = await collector.collect()
        articles = result.get('articles', [])
        
        print(f"✅ Total articles: {len(articles)}")
        print(f"   RSS count: {result.get('rss_count', 0)}")
        print(f"   Scraped count: {result.get('scraped_count', 0)}")
        
        # Show first 5
        for i, a in enumerate(articles[:5]):
            title = a.get('title', '?')[:60]
            source = a.get('source', '?')
            print(f"   {i+1}. [{source}] {title}")
        
        results['news'] = {'status': 'PASS', 'count': len(articles)}
        await collector.close()
    except Exception as e:
        print(f"❌ News failed: {e}")
        traceback.print_exc()
        results['news'] = {'status': 'FAIL', 'error': str(e)}


async def test_news_scraper():
    """Test web scraper directly"""
    print("\n" + "="*60)
    print("🕷️ TEST 2: News Scraper (Web Scraping)")
    print("="*60)
    
    from src.collectors.news_scraper import NewsScraper
    scraper = NewsScraper()
    
    try:
        articles = await scraper.scrape_all()
        
        print(f"✅ Scraped articles: {len(articles)}")
        for i, a in enumerate(articles[:3]):
            title = a.get('title', '?')[:60]
            source = a.get('source', '?')
            print(f"   {i+1}. [{source}] {title}")
        
        results['scraper'] = {'status': 'PASS', 'count': len(articles)}
        await scraper.close()
    except Exception as e:
        print(f"❌ Scraper failed: {e}")
        traceback.print_exc()
        results['scraper'] = {'status': 'FAIL', 'error': str(e)}


async def test_onchain():
    """Test on-chain data collection"""
    print("\n" + "="*60)
    print("⛓️ TEST 3: On-Chain Data")
    print("="*60)
    
    from src.collectors.onchain_collector import OnchainCollector
    collector = OnchainCollector()
    
    try:
        result = await collector.collect()
        metrics = result.get('metrics', {})
        
        print(f"✅ Metrics collected: {len(metrics)} coins")
        
        # Show fear & greed
        fg = result.get('fear_greed', {})
        print(f"   Fear & Greed: {fg.get('value', '?')} ({fg.get('classification', '?')})")
        
        for coin, data in list(metrics.items())[:3]:
            print(f"   {coin}: score={data.get('score', 0):.2f}, signal={data.get('signal', '?')}")
        
        results['onchain'] = {'status': 'PASS', 'count': len(metrics)}
    except Exception as e:
        print(f"❌ On-chain failed: {e}")
        traceback.print_exc()
        results['onchain'] = {'status': 'FAIL', 'error': str(e)}


async def test_binance_public():
    """Test Binance public endpoints (no API key needed)"""
    print("\n" + "="*60)
    print("📊 TEST 4: Binance Public Data")
    print("="*60)
    
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            # Test ticker price
            r = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
            btc_price = float(r.json()['price'])
            print(f"✅ BTC Price: ${btc_price:,.2f}")
            
            # Test funding rate (futures)
            r2 = await client.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1")
            fr_data = r2.json()
            if fr_data:
                fr = float(fr_data[0]['fundingRate'])
                print(f"✅ BTC Funding Rate: {fr:.6f} ({'longs pay' if fr > 0 else 'shorts pay'})")
            
            # Test L/S ratio
            r3 = await client.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1")
            ls_data = r3.json()
            if ls_data:
                ls = float(ls_data[0]['longShortRatio'])
                print(f"✅ BTC L/S Ratio: {ls:.4f}")
            
            # Test klines
            r4 = await client.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=5")
            klines = r4.json()
            print(f"✅ 1m Candles: {len(klines)} received")
            
            results['binance'] = {'status': 'PASS', 'btc_price': btc_price, 'funding_rate': fr}
    except Exception as e:
        print(f"❌ Binance failed: {e}")
        traceback.print_exc()
        results['binance'] = {'status': 'FAIL', 'error': str(e)}


async def test_aggregator():
    """Test aggregator with mock data"""
    print("\n" + "="*60)
    print("📊 TEST 5: Aggregator (with mock data)")
    print("="*60)
    
    from src.processors.aggregator import DataAggregator
    
    try:
        agg = DataAggregator()
        
        # Mock data
        tech = {
            'coins': [{
                'symbol': 'BTCUSDT',
                'price': 97000.0,
                'score': 72,
                'signals': {'trend': 'BULLISH', 'momentum': 'STRONG', 'volatility': 'MEDIUM'},
                'indicators': {
                    'ema_9': 96800, 'ema_21': 96500, 'ema_55': 96000,
                    'ema_20': 96600, 'ema_50': 95500, 'ema_200': 90000,
                    'rsi_7': 62.5, 'rsi_14': 58.3,
                    'macd': {'histogram': 150.0},
                    'volume_ratio': 1.3, 'atr_14': 450.0,
                    'bollinger': {'upper': 98000, 'middle': 96500, 'lower': 95000}
                }
            }]
        }
        
        sentiment = {
            'overall_sentiment': {'score': 65, 'label': 'SLIGHTLY_BULLISH'},
            'narrative': 'Bitcoin holding near $97k amid strong institutional demand'
        }
        
        onchain = {'metrics': {'BTC': {'score': 0.6, 'signal': 'BULLISH', 'price_change_24h': 2.1, 'reasoning': 'Bullish on-chain'}}}
        
        binance_raw = {
            'coins': [{
                'symbol': 'BTCUSDT',
                'funding_rate': 0.0002,
                'long_short_ratio': {'long_ratio': 0.52, 'short_ratio': 0.48, 'long_short_ratio': 1.08}
            }]
        }
        
        result = agg.aggregate(
            technical=tech,
            sentiment=sentiment,
            onchain=onchain,
            binance_raw=binance_raw,
            positions=[],
            balance={'total': 100, 'free': 80, 'used': 20},
            cycle_id='test_cycle_001'
        )
        
        btc = result['market_data'].get('BTCUSDT', {})
        print(f"✅ Aggregated BTCUSDT:")
        print(f"   Combined Score: {btc.get('combined_score', 0)}")
        print(f"   Combined Signal: {btc.get('combined_signal', '?')}")
        print(f"   Funding Rate: {btc.get('funding_rate', 0):.6f}")
        print(f"   L/S Ratio: {btc.get('long_short_ratio', {}).get('long_short_ratio', 0):.2f}")
        print(f"   Technical RSI-7: {btc.get('technical', {}).get('rsi_7', 0)}")
        print(f"   Technical EMA-9: {btc.get('technical', {}).get('ema_9', 0)}")
        print(f"   Summary: {result.get('summary', {})}")
        
        results['aggregator'] = {'status': 'PASS'}
    except Exception as e:
        print(f"❌ Aggregator failed: {e}")
        traceback.print_exc()
        results['aggregator'] = {'status': 'FAIL', 'error': str(e)}


async def test_ai_brain_fallback():
    """Test AI brain fallback decision logic"""
    print("\n" + "="*60)
    print("🧠 TEST 6: AI Brain Fallback Logic")
    print("="*60)
    
    from src.brain.ai_brain import AIBrain
    
    try:
        brain = AIBrain()
        
        # Test with position in loss + trend against
        mock_data = {
            'current_positions': [{
                'symbol': 'BTCUSDT',
                'side': 'long',
                'entry_price': 98000,
                'current_price': 96500,
                'pnl_percent': -1.5,
                'margin': 10,
                'leverage': 20
            }],
            'market_data': {
                'BTCUSDT': {
                    'price': 96500,
                    'technical': {
                        'trend': 'BEARISH',
                        'momentum': 'WEAK',
                        'score': 35,
                        'ema_9': 97000,
                        'rsi_7': 38,
                        'rsi_14': 42,
                        'ema_20': 97200,
                        'ema_50': 97500,
                        'ema_200': 92000,
                        'macd_histogram': -100,
                        'volume_ratio': 0.8
                    },
                    'combined_score': 38,
                    'combined_signal': 'BEARISH',
                    'signal_agreement': '2/3 ALIGNED'
                }
            },
            'summary': {
                'market_outlook': 'BEARISH',
                'bullish_coins': 2,
                'bearish_coins': 5,
                'best_opportunity': None,
                'best_score': 0,
                'open_positions': 1,
                'risk_level': 'MEDIUM',
                'avg_funding_rate': 0.0001
            },
            'account': {'balance_usdt': 100, 'available_margin': 80},
            'cycle_id': 'test_001'
        }
        
        decision = brain._fallback_decision(mock_data)
        
        print(f"✅ Fallback decision:")
        print(f"   Model: {decision['ai_model']}")
        for d in decision.get('decisions', []):
            print(f"   → {d['action']} {d['symbol']}: {d['reasoning'][:60]}")
        
        # Verify it closes position (loss + bearish trend)
        close_actions = [d for d in decision.get('decisions', []) if d['action'] == 'CLOSE']
        if close_actions:
            print(f"   ✅ Correctly identified CLOSE signal (loss + trend against)")
        else:
            print(f"   ⚠️ Did not close - check logic")
        
        results['ai_fallback'] = {'status': 'PASS', 'actions': len(decision.get('decisions', []))}
    except Exception as e:
        print(f"❌ AI Brain failed: {e}")
        traceback.print_exc()
        results['ai_fallback'] = {'status': 'FAIL', 'error': str(e)}


async def test_position_analyzer():
    """Test position analyzer"""
    print("\n" + "="*60)
    print("📈 TEST 7: Position Analyzer")
    print("="*60)
    
    from src.brain.position_analyzer import PositionAnalyzer
    
    try:
        analyzer = PositionAnalyzer()
        
        # Position with stop loss (-4%)
        result = analyzer.analyze(
            position={
                'symbol': 'ETHUSDT',
                'side': 'long',
                'entryPrice': 3500,
                'markPrice': 3360,
                'percentage': -4.0,
                'unrealizedPnl': -4.0,
                'leverage': 20,
                'initialMargin': 10
            },
            market_data={
                'technical': {
                    'trend': 'BEARISH',
                    'momentum': 'STRONG',
                    'score': 30,
                    'ema_9': 3400,
                    'rsi_7': 28,
                    'rsi_14': 35,
                    'volume_ratio': 1.5
                }
            }
        )
        
        print(f"✅ Position Analysis:")
        print(f"   Action: {result.get('action', '?')}")
        print(f"   Reasoning: {result.get('reasoning', '?')[:60]}")
        print(f"   Conviction: {result.get('conviction', 0)}")
        
        if result.get('action') == 'CLOSE':
            print(f"   ✅ Correctly identified stop loss at -4%")
        
        results['position_analyzer'] = {'status': 'PASS'}
    except Exception as e:
        print(f"❌ Position analyzer failed: {e}")
        traceback.print_exc()
        results['position_analyzer'] = {'status': 'FAIL', 'error': str(e)}


async def main():
    print("="*60)
    print("🤖 ClawBot AI — LIVE SYSTEM TEST")
    print(f"   Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("="*60)
    
    # Test 1-3: Live data tests
    await test_binance_public()
    await test_news_collector()
    await test_news_scraper()
    await test_onchain()
    
    # Test 4-7: Logic tests
    await test_aggregator()
    await test_ai_brain_fallback()
    await test_position_analyzer()
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    for name, res in results.items():
        status = res.get('status', '?')
        icon = '✅' if status == 'PASS' else '❌'
        extra = ''
        if 'count' in res:
            extra = f" ({res['count']} items)"
        if 'btc_price' in res:
            extra = f" (BTC=${res['btc_price']:,.0f})"
        print(f"   {icon} {name}{extra}")
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
    
    print(f"\n   TOTAL: {passed} passed, {failed} failed out of {len(results)}")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
