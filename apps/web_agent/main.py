"""
Web Agent Service
Searches web/news in near real-time and writes news_events
Can set TRADE_PAUSE flags based on significant events
"""
import sys
import os
import time
import re
from datetime import datetime, timezone
import feedparser
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Add parent directory to path to import common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import (
    db, setup_logging, get_sources_config,
    get_current_timestamp
)


class WebAgent:
    """Ingests news and web intelligence"""
    
    def __init__(self):
        self.logger = setup_logging('web_agent')
        self.sources_config = get_sources_config()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.seen_urls = set()  # Track seen URLs to avoid duplicates
        
    def extract_symbols(self, text):
        """Extract crypto symbols from text"""
        if not text:
            return []
        
        text_upper = text.upper()
        symbols = []
        
        # Common crypto keywords and their symbols
        crypto_keywords = {
            'BITCOIN': 'BTCUSDT',
            'BTC': 'BTCUSDT',
            'ETHEREUM': 'ETHUSDT',
            'ETH': 'ETHUSDT',
            'BINANCE COIN': 'BNBUSDT',
            'BNB': 'BNBUSDT',
            'SOLANA': 'SOLUSDT',
            'SOL': 'SOLUSDT',
        }
        
        for keyword, symbol in crypto_keywords.items():
            if keyword in text_upper:
                if symbol not in symbols:
                    symbols.append(symbol)
        
        return symbols
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text"""
        if not text:
            return 'neutral', 0.0
        
        # Use VADER sentiment analyzer
        scores = self.sentiment_analyzer.polarity_scores(text)
        compound_score = scores['compound']
        
        # Classify sentiment
        if compound_score >= 0.05:
            sentiment = 'positive'
        elif compound_score <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return sentiment, compound_score
    
    def determine_impact_level(self, text, sentiment_score):
        """Determine impact level of news"""
        if not text:
            return 'low'
        
        text_lower = text.lower()
        
        # High impact keywords
        high_impact = self.sources_config.get('sentiment', {}).get('impact_keywords', {}).get('high', [])
        medium_impact = self.sources_config.get('sentiment', {}).get('impact_keywords', {}).get('medium', [])
        
        for keyword in high_impact:
            if keyword.lower() in text_lower:
                return 'high'
        
        for keyword in medium_impact:
            if keyword.lower() in text_lower:
                return 'medium'
        
        # Strong sentiment also indicates higher impact
        if abs(sentiment_score) > 0.7:
            return 'high'
        elif abs(sentiment_score) > 0.4:
            return 'medium'
        
        return 'low'
    
    def extract_keywords(self, text):
        """Extract keywords from text"""
        if not text:
            return []
        
        # Simple keyword extraction (can be improved with NLP)
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        
        # Filter common words
        common_words = {'that', 'this', 'with', 'from', 'have', 'been', 'will', 'their', 'about'}
        keywords = [w for w in words if w not in common_words]
        
        # Return top unique keywords
        return list(set(keywords))[:10]
    
    def fetch_rss_feed(self, source_config):
        """Fetch and parse RSS feed"""
        try:
            url = source_config.get('url')
            feed = feedparser.parse(url)
            
            news_items = []
            for entry in feed.entries[:10]:  # Process last 10 items
                # Skip if already seen
                url = entry.get('link', '')
                if url in self.seen_urls:
                    continue
                
                self.seen_urls.add(url)
                
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                content = f"{title}. {summary}"
                
                # Extract symbols
                symbols = self.extract_symbols(content)
                
                # Analyze sentiment
                sentiment, sentiment_score = self.analyze_sentiment(content)
                
                # Determine impact
                impact_level = self.determine_impact_level(content, sentiment_score)
                
                # Extract keywords
                keywords = self.extract_keywords(content)
                
                # Parse published date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                
                news_item = {
                    'source': source_config.get('name'),
                    'title': title,
                    'content': summary,
                    'url': url,
                    'sentiment': sentiment,
                    'sentiment_score': sentiment_score,
                    'symbols': symbols,
                    'impact_level': impact_level,
                    'category': 'news',
                    'keywords': keywords,
                    'published_at': published_at
                }
                
                news_items.append(news_item)
            
            self.logger.info(f"Fetched {len(news_items)} new items from RSS",
                           source=source_config.get('name'))
            
            return news_items
            
        except Exception as e:
            self.logger.error("Failed to fetch RSS feed",
                            source=source_config.get('name'),
                            error=str(e))
            return []
    
    def store_news_events(self, news_items):
        """Store news events in database"""
        stored_count = 0
        high_impact_count = 0
        
        for item in news_items:
            try:
                news_id = db.insert_news_event(item)
                stored_count += 1
                
                if item['impact_level'] == 'high':
                    high_impact_count += 1
                    self.logger.warning("High impact news detected",
                                      title=item['title'],
                                      sentiment=item['sentiment'],
                                      symbols=item['symbols'])
                
            except Exception as e:
                self.logger.error("Failed to store news event",
                                title=item.get('title'),
                                error=str(e))
        
        self.logger.info(f"Stored {stored_count} news events",
                       high_impact=high_impact_count)
        
        db.log_audit('web_agent', 'store_news', 'news_events', None,
                    {'count': stored_count, 'high_impact': high_impact_count}, 'success')
        
        return high_impact_count
    
    def check_and_set_pause_flag(self, high_impact_count):
        """Check if we should pause trading based on news"""
        try:
            # Pause if we have multiple high impact news in one cycle
            if high_impact_count >= 2:
                db.set_system_flag(
                    'TRADE_PAUSE',
                    True,
                    reason=f"Multiple high-impact news events detected ({high_impact_count})",
                    set_by='web_agent'
                )
                self.logger.warning("TRADE_PAUSE flag set due to high impact news",
                                  count=high_impact_count)
            else:
                # Check if we should unpause
                current_pause = db.get_system_flag('TRADE_PAUSE')
                if current_pause and high_impact_count == 0:
                    # Could implement auto-unpause logic here
                    pass
                    
        except Exception as e:
            self.logger.error("Failed to update pause flag", error=str(e))
    
    def run_once(self):
        """Run one news ingestion cycle"""
        self.logger.info("Starting news ingestion cycle")
        
        all_news = []
        
        # Fetch from all enabled RSS sources
        news_sources = self.sources_config.get('news_sources', [])
        for source in news_sources:
            if not source.get('enabled', False):
                continue
            
            if source.get('type') == 'rss':
                news_items = self.fetch_rss_feed(source)
                all_news.extend(news_items)
            
            time.sleep(1)  # Be polite to sources
        
        # Store news events
        if all_news:
            high_impact_count = self.store_news_events(all_news)
            
            # Check if we should pause trading
            self.check_and_set_pause_flag(high_impact_count)
        else:
            self.logger.debug("No new news items found")
        
        self.logger.info("News ingestion cycle complete")
    
    def run_continuous(self, interval_seconds=300):
        """Run news ingestion continuously"""
        self.logger.info(f"Starting continuous news ingestion (interval: {interval_seconds}s)")
        
        while True:
            try:
                self.run_once()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                self.logger.info("Stopping web agent")
                break
            except Exception as e:
                self.logger.error("Unexpected error in web agent loop", error=str(e))
                time.sleep(30)


if __name__ == '__main__':
    agent = WebAgent()
    
    # Get update interval from environment (default 5 minutes)
    interval = int(os.getenv('WEB_AGENT_INTERVAL_SECONDS', '300'))
    
    # Run continuously
    agent.run_continuous(interval_seconds=interval)
