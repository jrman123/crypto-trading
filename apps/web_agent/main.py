"""
Web Agent
Monitors GDELT news for crypto-related events.
Sets TRADE_PAUSE flag on high-impact bearish news.
"""
import os
import sys
import time
import logging
import yaml
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.db import insert_news_event, set_system_flag, execute_query

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_sources_config():
    """Load sources configuration."""
    config_path = os.getenv('SOURCES_CONFIG', '/app/configs/sources.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Error loading sources config: {e}, using defaults")
        return {
            'news': {
                'gdelt': {
                    'enabled': True,
                    'api_url': 'https://api.gdeltproject.org/api/v2/doc/doc',
                    'query_interval_sec': 300,
                    'keywords': ['bitcoin', 'ethereum', 'cryptocurrency'],
                    'max_results': 10
                }
            }
        }


def search_gdelt_news(keywords, max_results=10, api_url=None):
    """
    Search GDELT for news articles.
    
    Args:
        keywords: List of keywords to search
        max_results: Maximum number of results
        api_url: GDELT API URL
        
    Returns:
        List of news articles
    """
    if not api_url:
        api_url = 'https://api.gdeltproject.org/api/v2/doc/doc'
    
    try:
        # Build query
        query = ' OR '.join(keywords)
        
        # GDELT API parameters
        params = {
            'query': query,
            'mode': 'artlist',
            'maxrecords': max_results,
            'format': 'json',
            'timespan': '1h'  # Last 1 hour
        }
        
        response = requests.get(api_url, params=params, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                articles = data.get('articles', [])
                logger.info(f"Found {len(articles)} articles from GDELT")
                return articles
            except ValueError:
                logger.error("Failed to parse GDELT JSON response")
                return []
        else:
            logger.warning(f"GDELT API returned status {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching GDELT: {e}")
        return []


def analyze_sentiment(title, url=''):
    """
    Simple sentiment analysis based on keywords.
    
    Args:
        title: Article title
        url: Article URL
        
    Returns:
        Tuple of (sentiment, impact_score)
    """
    title_lower = title.lower()
    
    # Bearish keywords
    bearish_keywords = [
        'crash', 'plunge', 'drop', 'fall', 'decline', 'bear',
        'collapse', 'crisis', 'hack', 'scam', 'fraud', 'ban',
        'regulation', 'crackdown', 'warning', 'risk', 'loss'
    ]
    
    # Bullish keywords
    bullish_keywords = [
        'surge', 'rally', 'rise', 'gain', 'bull', 'soar',
        'breakthrough', 'adoption', 'approval', 'partnership',
        'launch', 'success', 'milestone', 'record'
    ]
    
    bearish_count = sum(1 for kw in bearish_keywords if kw in title_lower)
    bullish_count = sum(1 for kw in bullish_keywords if kw in title_lower)
    
    # Determine sentiment
    if bearish_count > bullish_count:
        sentiment = 'BEARISH'
        impact_score = min(0.3 + (bearish_count * 0.1), 0.9)
    elif bullish_count > bearish_count:
        sentiment = 'BULLISH'
        impact_score = min(0.3 + (bullish_count * 0.1), 0.9)
    else:
        sentiment = 'NEUTRAL'
        impact_score = 0.2
    
    return sentiment, impact_score


def process_news_articles(articles):
    """
    Process and store news articles.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        List of processed articles with sentiment
    """
    processed = []
    
    for article in articles:
        try:
            title = article.get('title', '')
            url = article.get('url', '')
            published = article.get('seendate', datetime.now().isoformat())
            
            if not title:
                continue
            
            # Parse date
            try:
                # GDELT date format: YYYYMMDDHHMMSS
                if len(published) >= 14:
                    published_dt = datetime.strptime(published[:14], '%Y%m%d%H%M%S')
                else:
                    published_dt = datetime.now()
            except (ValueError, TypeError):
                published_dt = datetime.now()
            
            # Analyze sentiment
            sentiment, impact_score = analyze_sentiment(title, url)
            
            # Extract keywords from title
            keywords = [word.lower() for word in title.split() if len(word) > 4][:10]
            
            # Store in database
            news_id = insert_news_event(
                source='GDELT',
                title=title,
                url=url,
                published_at=published_dt,
                sentiment=sentiment,
                impact_score=impact_score,
                keywords=keywords,
                raw_data=article
            )
            
            processed.append({
                'id': news_id,
                'title': title,
                'sentiment': sentiment,
                'impact_score': impact_score
            })
            
            logger.info(
                f"Processed news: {sentiment} (impact={impact_score:.2f}) - {title[:60]}..."
            )
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
    
    return processed


def check_high_impact_bearish_news():
    """
    Check for recent high-impact bearish news.
    
    Returns:
        True if high-impact bearish news found
    """
    query = """
        SELECT * FROM news_events
        WHERE sentiment = 'BEARISH'
        AND impact_score > 0.6
        AND published_at > NOW() - INTERVAL '1 hour'
        ORDER BY impact_score DESC
        LIMIT 1
    """
    
    results = execute_query(query)
    return len(results) > 0


def update_trade_pause_flag(should_pause, reason=''):
    """
    Update TRADE_PAUSE system flag.
    
    Args:
        should_pause: True to pause trading
        reason: Reason for the flag change
    """
    set_system_flag(
        flag_name='TRADE_PAUSE',
        flag_value=should_pause,
        reason=reason,
        set_by='web_agent'
    )
    
    status = "PAUSED" if should_pause else "RESUMED"
    logger.warning(f"Trading {status}: {reason}")


def run_continuous_monitoring(config):
    """
    Continuously monitor news sources.
    
    Args:
        config: Sources configuration
    """
    logger.info("Starting continuous news monitoring...")
    
    gdelt_config = config['news'].get('gdelt', {})
    
    if not gdelt_config.get('enabled', True):
        logger.warning("GDELT monitoring is disabled")
        return
    
    api_url = gdelt_config.get('api_url')
    keywords = gdelt_config.get('keywords', ['bitcoin', 'ethereum', 'cryptocurrency'])
    interval = gdelt_config.get('query_interval_sec', 300)
    max_results = gdelt_config.get('max_results', 10)
    
    logger.info(f"Monitoring keywords: {keywords}")
    
    while True:
        try:
            # Search for news
            articles = search_gdelt_news(keywords, max_results, api_url)
            
            if articles:
                # Process articles
                processed = process_news_articles(articles)
                
                # Check for high-impact bearish news
                if check_high_impact_bearish_news():
                    logger.warning("High-impact bearish news detected!")
                    update_trade_pause_flag(
                        should_pause=True,
                        reason='High-impact bearish news in crypto market'
                    )
                else:
                    # Resume trading if paused
                    update_trade_pause_flag(
                        should_pause=False,
                        reason='No high-impact bearish news'
                    )
            
            logger.info(f"Sleeping for {interval} seconds...")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("Shutting down web agent...")
            break
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}")
            time.sleep(30)


def main():
    """Main entry point."""
    logger.info("Starting Web Agent (News Monitor)...")
    
    # Load configuration
    config = load_sources_config()
    
    # Start continuous monitoring
    run_continuous_monitoring(config)


if __name__ == '__main__':
    main()
