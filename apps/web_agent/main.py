"""
Web Intelligence Agent - Monitors news and sets system flags
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
import requests
import yaml

# Add parent directory to path for imports
sys.path.insert(0, '/app/apps')
from common.db import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebIntelligenceAgent:
    """Monitors web news and intelligence for market-moving events"""
    
    def __init__(self, 
                 symbols_config_path: str = '/app/configs/symbols.yaml',
                 sources_config_path: str = '/app/configs/sources.yaml'):
        self.symbols_config = self._load_config(symbols_config_path)
        self.sources_config = self._load_config(sources_config_path)
        
    def _load_config(self, path: str) -> dict:
        """Load configuration from YAML"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            return {}
    
    def fetch_gdelt_news(self, query: str, lookback_hours: int = 24) -> list:
        """
        Fetch news from GDELT API
        
        Args:
            query: Search query
            lookback_hours: How many hours back to search
            
        Returns:
            List of news articles
        """
        # GDELT Doc 2.0 API endpoint
        base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)
        
        params = {
            'query': query,
            'mode': 'artlist',
            'maxrecords': 20,
            'format': 'json',
            'startdatetime': start_time.strftime('%Y%m%d%H%M%S'),
            'enddatetime': end_time.strftime('%Y%m%d%H%M%S')
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('articles', [])
        except Exception as e:
            logger.error(f"GDELT API error: {e}")
            return []
    
    def analyze_sentiment(self, title: str, summary: str = '') -> tuple:
        """
        Simple keyword-based sentiment analysis
        
        Returns:
            (impact: str, confidence: float)
        """
        text = (title + ' ' + summary).lower()
        
        # Get keywords from config
        bearish_keywords = self.sources_config.get('high_impact_bearish_keywords', [
            'crash', 'hack', 'exploit', 'scam', 'fraud', 'ban', 'regulation',
            'sec', 'investigation', 'lawsuit', 'bankruptcy', 'collapse', 'crisis'
        ])
        
        bullish_keywords = [
            'adoption', 'partnership', 'approval', 'etf', 'institutional',
            'growth', 'surge', 'breakthrough', 'innovation'
        ]
        
        # Count matches
        bearish_count = sum(1 for kw in bearish_keywords if kw in text)
        bullish_count = sum(1 for kw in bullish_keywords if kw in text)
        
        # Determine impact
        if bearish_count > bullish_count:
            impact = 'bearish'
            confidence = min(bearish_count * 20, 100)  # 20% per keyword, max 100%
        elif bullish_count > bearish_count:
            impact = 'bullish'
            confidence = min(bullish_count * 20, 100)
        else:
            impact = 'neutral'
            confidence = 50
        
        return impact, confidence
    
    def monitor_news_for_symbol(self, symbol: str):
        """
        Monitor news for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
        """
        # Extract base currency from symbol (e.g., BTC from BTCUSDT)
        base = symbol.replace('USDT', '').replace('USD', '')
        
        # Search terms
        search_terms = [
            f'{base} cryptocurrency',
            f'bitcoin' if base == 'BTC' else base.lower()
        ]
        
        lookback_hours = self.sources_config.get('lookback_hours', 24)
        
        for term in search_terms:
            articles = self.fetch_gdelt_news(term, lookback_hours)
            
            for article in articles:
                try:
                    title = article.get('title', '')
                    url = article.get('url', '')
                    published_str = article.get('seendate', '')
                    
                    if not title or not url:
                        continue
                    
                    # Parse published date
                    try:
                        # GDELT format: YYYYMMDDHHMMSS
                        published_at = datetime.strptime(published_str, '%Y%m%d%H%M%S')
                    except:
                        published_at = datetime.now()
                    
                    # Analyze sentiment
                    impact, confidence = self.analyze_sentiment(title, '')
                    
                    # Store in database
                    db.insert_news_event(
                        symbol=symbol,
                        published_at=published_at,
                        title=title,
                        url=url,
                        source='GDELT',
                        summary=None,
                        impact=impact,
                        confidence=confidence
                    )
                    
                    logger.info(
                        f"News: {symbol} - {impact.upper()} "
                        f"({confidence:.0f}%) - {title[:60]}..."
                    )
                    
                    # Check if we should pause trading
                    pause_threshold = self.sources_config.get('pause_confidence_threshold', 80)
                    if impact == 'bearish' and confidence >= pause_threshold:
                        logger.warning(
                            f"HIGH IMPACT BEARISH NEWS DETECTED: {title}"
                        )
                        db.set_system_flag('TRADE_PAUSE', 'true')
                        db.set_system_flag(
                            'TRADE_PAUSE_REASON',
                            f'High-impact bearish news: {title[:100]}'
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to process article: {e}")
    
    def run_once(self):
        """Run one news monitoring cycle"""
        symbols = self.symbols_config.get('symbols', ['BTCUSDT'])
        
        logger.info("=== News monitoring cycle starting ===")
        
        for symbol in symbols:
            try:
                self.monitor_news_for_symbol(symbol)
            except Exception as e:
                logger.error(f"Failed to monitor news for {symbol}: {e}")
        
        logger.info("News monitoring cycle complete")


def main():
    """Main entry point"""
    logger.info("=== Web Intelligence Agent Starting ===")
    
    # Connect to database
    db.connect()
    
    # Initialize agent
    agent = WebIntelligenceAgent()
    
    # Get interval from environment
    interval_seconds = int(os.getenv('WEB_EVERY', 7200))  # Default 2 hours
    
    try:
        while True:
            try:
                agent.run_once()
            except Exception as e:
                logger.error(f"Web intelligence error: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down web intelligence agent...")
    finally:
        db.disconnect()


if __name__ == '__main__':
    main()
