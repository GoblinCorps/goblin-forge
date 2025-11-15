"""
US Stock Ticker List Downloader

Downloads and maintains up-to-date ticker lists from the US-Stock-Symbols GitHub repository.

Data Source:
------------
GitHub: https://github.com/rreichel3/US-Stock-Symbols
- Auto-updates daily at midnight Eastern time
- Provides per-exchange ticker lists (NYSE, NASDAQ, AMEX)
- Available in JSON and TXT formats

Exchange Files:
---------------
- NYSE: nyse/nyse_tickers.json
- NASDAQ: nasdaq/nasdaq_tickers.json
- AMEX: amex/amex_tickers.json
- All: all/all_tickers.json (contains duplicates)

Recommended Workflow:
---------------------
Use per-exchange lists to avoid duplicate symbols across exchanges.

Usage:
------
from src.data.ticker_downloader import ticker_downloader

# Download latest tickers
ticker_downloader.download_all_exchanges()

# Get tickers by exchange
nyse = ticker_downloader.get_tickers('NYSE')
nasdaq = ticker_downloader.get_tickers('NASDAQ')

# Get all unique tickers
all_tickers = ticker_downloader.get_all_tickers()
"""

import json
import urllib.request
from typing import List, Dict, Optional, Set, Any
from pathlib import Path
from datetime import datetime, timedelta

from loguru import logger

from src.config import config


class TickerDownloader:
    """
    Downloads and caches US stock ticker lists from GitHub.

    Maintains local cache of ticker lists with automatic refresh.
    """

    # GitHub raw content base URL
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main"

    # Exchange configurations
    EXCHANGES = {
        'NYSE': 'nyse/nyse_tickers.json',
        'NASDAQ': 'nasdaq/nasdaq_tickers.json',
        'AMEX': 'amex/amex_tickers.json'
    }

    def __init__(self, cache_dir: Optional[str] = None, cache_hours: int = 24):
        """
        Initialize ticker downloader.

        Parameters:
        -----------
        cache_dir : str, optional
            Directory for cached ticker files
        cache_hours : int, default=24
            Hours before cache expires and refresh is needed
        """
        self.cache_dir = Path(cache_dir or config.get('storage.ticker_cache_dir', 'data/tickers'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_hours = cache_hours

        logger.info(f"Ticker downloader initialized: {self.cache_dir}")

    def _get_cache_file(self, exchange: str) -> Path:
        """Get cache file path for exchange."""
        return self.cache_dir / f"{exchange.lower()}_tickers.json"

    def _is_cache_valid(self, exchange: str) -> bool:
        """
        Check if cached file exists and is recent enough.

        Parameters:
        -----------
        exchange : str
            Exchange name (NYSE, NASDAQ, AMEX)

        Returns:
        --------
        bool
            True if cache is valid
        """
        cache_file = self._get_cache_file(exchange)

        if not cache_file.exists():
            return False

        # Check file age
        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

        if age_hours > self.cache_hours:
            logger.info(f"{exchange} cache expired ({age_hours:.1f}h old)")
            return False

        return True

    def download_exchange(self, exchange: str, force: bool = False) -> List[str]:
        """
        Download ticker list for a specific exchange.

        Parameters:
        -----------
        exchange : str
            Exchange name (NYSE, NASDAQ, AMEX)
        force : bool, default=False
            Force download even if cache is valid

        Returns:
        --------
        list of str
            List of ticker symbols

        Raises:
        -------
        ValueError
            If exchange is not supported
        urllib.error.URLError
            If download fails
        """
        if exchange not in self.EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange}. Must be one of {list(self.EXCHANGES.keys())}")

        cache_file = self._get_cache_file(exchange)

        # Use cache if valid
        if not force and self._is_cache_valid(exchange):
            logger.debug(f"Using cached {exchange} tickers")
            with open(cache_file) as f:
                return json.load(f)

        # Download from GitHub
        try:
            url = f"{self.GITHUB_BASE_URL}/{self.EXCHANGES[exchange]}"
            logger.info(f"Downloading {exchange} tickers from GitHub...")

            with urllib.request.urlopen(url, timeout=30) as response:
                tickers = json.loads(response.read().decode())

            # Validate
            if not isinstance(tickers, list):
                raise ValueError(f"Invalid ticker data format for {exchange}")

            # Save to cache
            with open(cache_file, 'w') as f:
                json.dump(tickers, f, indent=2)

            logger.info(f"✅ Downloaded {len(tickers)} {exchange} tickers")
            return tickers

        except urllib.error.URLError as e:
            logger.error(f"Failed to download {exchange} tickers: {e}")

            # Fall back to cache if available
            if cache_file.exists():
                logger.warning(f"Using stale {exchange} cache as fallback")
                with open(cache_file) as f:
                    return json.load(f)
            else:
                raise

        except Exception as e:
            logger.error(f"Error processing {exchange} tickers: {e}")
            raise

    def download_all_exchanges(self, force: bool = False) -> Dict[str, List[str]]:
        """
        Download ticker lists for all exchanges.

        Parameters:
        -----------
        force : bool, default=False
            Force download even if cache is valid

        Returns:
        --------
        dict
            Dictionary mapping exchange name to ticker list
        """
        results = {}

        for exchange in self.EXCHANGES.keys():
            try:
                results[exchange] = self.download_exchange(exchange, force=force)
            except Exception as e:
                logger.error(f"Failed to download {exchange}: {e}")
                results[exchange] = []

        total_tickers = sum(len(tickers) for tickers in results.values())
        logger.info(f"Downloaded {total_tickers} total tickers across {len(results)} exchanges")

        return results

    def get_tickers(self, exchange: str, auto_download: bool = True) -> List[str]:
        """
        Get ticker list for an exchange.

        Parameters:
        -----------
        exchange : str
            Exchange name (NYSE, NASDAQ, AMEX)
        auto_download : bool, default=True
            Automatically download if cache is missing or expired

        Returns:
        --------
        list of str
            List of ticker symbols
        """
        cache_file = self._get_cache_file(exchange)

        # Check cache
        if self._is_cache_valid(exchange):
            with open(cache_file) as f:
                return json.load(f)

        # Auto-download if enabled
        if auto_download:
            return self.download_exchange(exchange)

        # No cache and auto-download disabled
        if cache_file.exists():
            logger.warning(f"Using expired {exchange} cache")
            with open(cache_file) as f:
                return json.load(f)
        else:
            logger.error(f"No {exchange} tickers available")
            return []

    def get_all_tickers(self, exchanges: Optional[List[str]] = None, auto_download: bool = True) -> List[str]:
        """
        Get combined ticker list from multiple exchanges (deduplicated).

        Parameters:
        -----------
        exchanges : list of str, optional
            List of exchange names. If None, uses all exchanges.
        auto_download : bool, default=True
            Automatically download if cache is missing or expired

        Returns:
        --------
        list of str
            Deduplicated list of ticker symbols
        """
        if exchanges is None:
            exchanges = list(self.EXCHANGES.keys())

        all_tickers: Set[str] = set()

        for exchange in exchanges:
            tickers = self.get_tickers(exchange, auto_download=auto_download)
            all_tickers.update(tickers)

        sorted_tickers = sorted(list(all_tickers))
        logger.info(f"Combined {len(sorted_tickers)} unique tickers from {len(exchanges)} exchanges")

        return sorted_tickers

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about cached ticker data.

        Returns:
        --------
        dict
            Statistics including counts, cache ages, etc.
        """
        stats = {
            'exchanges': {},
            'total_unique': 0,
            'cache_dir': str(self.cache_dir)
        }

        all_tickers: Set[str] = set()

        for exchange in self.EXCHANGES.keys():
            cache_file = self._get_cache_file(exchange)

            if cache_file.exists():
                # Load tickers
                with open(cache_file) as f:
                    tickers = json.load(f)

                # Calculate age
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

                stats['exchanges'][exchange] = {
                    'count': len(tickers),
                    'cache_age_hours': round(age_hours, 1),
                    'cache_valid': age_hours <= self.cache_hours
                }

                all_tickers.update(tickers)
            else:
                stats['exchanges'][exchange] = {
                    'count': 0,
                    'cache_age_hours': None,
                    'cache_valid': False
                }

        stats['total_unique'] = len(all_tickers)

        return stats

    def refresh_if_needed(self) -> bool:
        """
        Refresh ticker lists if cache is expired.

        Returns:
        --------
        bool
            True if any exchange was refreshed
        """
        refreshed = False

        for exchange in self.EXCHANGES.keys():
            if not self._is_cache_valid(exchange):
                try:
                    self.download_exchange(exchange)
                    refreshed = True
                except Exception as e:
                    logger.error(f"Failed to refresh {exchange}: {e}")

        return refreshed


# Global singleton instance
ticker_downloader = TickerDownloader()
