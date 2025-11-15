"""
Universe Construction and Management

Builds and maintains the tradeable universe of stocks for screening.

Universe Sources:
-----------------
1. NYSE - New York Stock Exchange (~3,000 tickers)
2. NASDAQ - NASDAQ Stock Market (~3,500 tickers)
3. AMEX - American Stock Exchange (~300 tickers)
4. All Exchanges - Combined deduplicated list
5. Custom symbol lists (user-defined)

Data Source: US-Stock-Symbols GitHub (auto-updates daily)
https://github.com/rreichel3/US-Stock-Symbols

Pre-Screening Filters:
----------------------
- Minimum price (default: $5.00)
- Maximum price (default: $500.00)
- Minimum average volume (default: 500,000 shares/day)
- Sector/industry filters (optional)
- Exchange filters (NYSE, NASDAQ, etc.)

Usage:
------
from src.screening.universe import universe_manager

# Build universe from S&P 500
symbols = universe_manager.build_universe(sources=['sp500'])

# Apply filters
filtered = universe_manager.filter_universe(
    symbols,
    min_price=10.0,
    min_volume=1_000_000
)

# Get current quotes for universe validation
quotes = universe_manager.get_universe_quotes(symbols)
"""

import json
from typing import List, Dict, Set, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from src.config import config
from src.data.ib_manager import ib_manager
from src.data.ticker_downloader import ticker_downloader


class UniverseManager:
    """
    Universe construction and management.

    Builds and maintains the tradeable stock universe by loading symbol lists,
    applying filters, and validating data availability.

    Attributes:
    -----------
    data_dir : Path
        Directory for universe data files
    symbol_lists : dict
        Pre-loaded symbol lists from various sources
    cache : dict
        Cached universe data
    """

    # Supported exchange sources
    SUPPORTED_EXCHANGES = ['NYSE', 'NASDAQ', 'AMEX', 'ALL']

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize universe manager.

        Parameters:
        -----------
        data_dir : str, optional
            Directory for universe data files. If None, uses config default.
        """
        self.data_dir = Path(data_dir or config.get('storage.universe_dir', 'data/universe'))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Symbol lists from various sources
        self.symbol_lists: Dict[str, List[str]] = {}

        # Load configuration
        self.min_price = config.universe.min_price
        self.max_price = config.universe.max_price
        self.min_avg_volume = config.universe.min_avg_volume

        # Cache for universe data
        self.cache: Dict[str, Any] = {}

        logger.info(f"Universe manager initialized: {self.data_dir}")

    def load_symbol_list(
        self,
        source: str,
        file_path: Optional[str] = None
    ) -> List[str]:
        """
        Load symbol list from source.

        Parameters:
        -----------
        source : str
            Source name ('NYSE', 'NASDAQ', 'AMEX', 'ALL', or 'custom')
        file_path : str, optional
            Path to custom symbol list file (JSON or CSV)

        Returns:
        --------
        list of str
            List of stock symbols

        Examples:
        ---------
        >>> symbols = universe_manager.load_symbol_list('NYSE')
        >>> len(symbols)
        ~3000
        >>> nasdaq = universe_manager.load_symbol_list('NASDAQ')
        >>> custom = universe_manager.load_symbol_list(
        ...     'custom',
        ...     file_path='data/my_symbols.json'
        ... )
        """
        try:
            # Try to load from file first
            if file_path is not None:
                file_path = Path(file_path)
                if file_path.suffix == '.json':
                    with open(file_path, 'r') as f:
                        symbols = json.load(f)
                elif file_path.suffix == '.csv':
                    df = pd.read_csv(file_path)
                    # Assume first column is symbols
                    symbols = df.iloc[:, 0].tolist()
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")

                logger.info(f"Loaded {len(symbols)} symbols from {file_path}")
                self.symbol_lists[source] = symbols
                return symbols

            # Check if already loaded
            if source in self.symbol_lists:
                return self.symbol_lists[source]

            # Handle exchange sources (NYSE, NASDAQ, AMEX, ALL)
            source_upper = source.upper()
            if source_upper in self.SUPPORTED_EXCHANGES:
                if source_upper == 'ALL':
                    symbols = ticker_downloader.get_all_tickers()
                else:
                    symbols = ticker_downloader.get_tickers(source_upper)

                logger.info(f"Loaded {len(symbols)} symbols from {source_upper} via ticker downloader")
                self.symbol_lists[source] = symbols
                return symbols

            # Try to load from data directory
            json_path = self.data_dir / f"{source}.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    symbols = json.load(f)
                logger.info(f"Loaded {len(symbols)} symbols from {json_path}")
                self.symbol_lists[source] = symbols
                return symbols

            logger.warning(f"Unknown symbol list source: {source}")
            return []

        except Exception as e:
            logger.error(f"Error loading symbol list '{source}': {e}")
            return []

    def save_symbol_list(
        self,
        source: str,
        symbols: List[str]
    ) -> bool:
        """
        Save symbol list to file.

        Parameters:
        -----------
        source : str
            Source name
        symbols : list of str
            List of symbols

        Returns:
        --------
        bool
            True if save successful
        """
        try:
            file_path = self.data_dir / f"{source}.json"
            with open(file_path, 'w') as f:
                json.dump(symbols, f, indent=2)

            logger.info(f"Saved {len(symbols)} symbols to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving symbol list '{source}': {e}")
            return False

    def build_universe(
        self,
        sources: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build universe from multiple sources.

        Combines symbol lists from specified sources and removes duplicates.

        Parameters:
        -----------
        sources : list of str, optional
            List of sources to combine. If None, uses config default.
            Options: 'NYSE', 'NASDAQ', 'AMEX', 'ALL', or custom file sources

        Returns:
        --------
        list of str
            Combined list of unique symbols

        Examples:
        ---------
        >>> # Build from NYSE and NASDAQ
        >>> universe = universe_manager.build_universe(['NYSE', 'NASDAQ'])
        >>> len(universe)
        ~6000

        >>> # Build from all exchanges
        >>> universe = universe_manager.build_universe(['ALL'])
        >>> len(universe)
        ~6800
        """
        if sources is None:
            sources = config.universe.sources

        all_symbols: Set[str] = set()

        for source in sources:
            symbols = self.load_symbol_list(source)
            all_symbols.update(symbols)

        universe = sorted(list(all_symbols))
        logger.info(f"Built universe from {sources}: {len(universe)} symbols")

        return universe

    def get_universe_quotes(
        self,
        symbols: List[str],
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get current market quotes for universe symbols.

        Parameters:
        -----------
        symbols : list of str
            List of symbols
        fields : list of str, optional
            Fields to retrieve. If None, gets all available.
            Options: 'last', 'bid', 'ask', 'volume', 'close', 'high', 'low'

        Returns:
        --------
        pd.DataFrame
            Quote data with columns: symbol, last, bid, ask, volume, etc.

        Notes:
        ------
        This is used for real-time universe filtering based on current price/volume.
        """
        try:
            if not ib_manager.is_connected():
                logger.warning("IB not connected, cannot get quotes")
                return pd.DataFrame()

            quotes_data = []

            for symbol in symbols:
                try:
                    # Create contract
                    from ib_insync import Stock
                    contract = Stock(symbol, 'SMART', 'USD')

                    # Get market data snapshot
                    ticker = ib_manager.ib.reqTicker(contract)
                    ib_manager.ib.sleep(0.1)  # Rate limiting

                    quote = {
                        'symbol': symbol,
                        'last': ticker.last if ticker.last == ticker.last else None,  # Check for NaN
                        'bid': ticker.bid if ticker.bid == ticker.bid else None,
                        'ask': ticker.ask if ticker.ask == ticker.ask else None,
                        'volume': ticker.volume if ticker.volume == ticker.volume else None,
                        'close': ticker.close if ticker.close == ticker.close else None,
                        'high': ticker.high if ticker.high == ticker.high else None,
                        'low': ticker.low if ticker.low == ticker.low else None,
                        'timestamp': datetime.now()
                    }

                    quotes_data.append(quote)

                except Exception as e:
                    logger.debug(f"Error getting quote for {symbol}: {e}")
                    continue

            df = pd.DataFrame(quotes_data)
            logger.info(f"Retrieved quotes for {len(df)} symbols")

            return df

        except Exception as e:
            logger.error(f"Error getting universe quotes: {e}")
            return pd.DataFrame()

    def filter_universe(
        self,
        symbols: List[str],
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_volume: Optional[int] = None,
        use_cached_quotes: bool = False
    ) -> List[str]:
        """
        Filter universe based on price and volume criteria.

        Parameters:
        -----------
        symbols : list of str
            Input symbol list
        min_price : float, optional
            Minimum price filter (default from config)
        max_price : float, optional
            Maximum price filter (default from config)
        min_volume : int, optional
            Minimum daily volume filter (default from config)
        use_cached_quotes : bool, default=False
            If True, uses cached quotes. If False, fetches fresh quotes.

        Returns:
        --------
        list of str
            Filtered symbol list

        Examples:
        ---------
        >>> filtered = universe_manager.filter_universe(
        ...     symbols=['AAPL', 'MSFT', 'PENNY_STOCK'],
        ...     min_price=10.0,
        ...     min_volume=1_000_000
        ... )
        """
        if min_price is None:
            min_price = self.min_price
        if max_price is None:
            max_price = self.max_price
        if min_volume is None:
            min_volume = self.min_avg_volume

        logger.info(
            f"Filtering {len(symbols)} symbols: "
            f"price ${min_price}-${max_price}, volume >{min_volume:,}"
        )

        # Get quotes
        if use_cached_quotes and 'quotes' in self.cache:
            df = self.cache['quotes']
        else:
            df = self.get_universe_quotes(symbols)
            self.cache['quotes'] = df
            self.cache['quotes_timestamp'] = datetime.now()

        if df.empty:
            logger.warning("No quote data available, returning unfiltered universe")
            return symbols

        # Apply filters
        filtered_df = df[
            (df['last'] >= min_price) &
            (df['last'] <= max_price) &
            (df['volume'] >= min_volume)
        ]

        filtered_symbols = filtered_df['symbol'].tolist()

        logger.info(
            f"Filtered universe: {len(filtered_symbols)} / {len(symbols)} symbols passed"
        )

        return filtered_symbols

    def get_universe_summary(
        self,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for universe.

        Parameters:
        -----------
        symbols : list of str, optional
            Symbol list. If None, builds from default sources.

        Returns:
        --------
        dict
            Summary with keys:
            - symbol_count: Total symbols
            - sources: List of sources used
            - price_range: (min, max) price
            - volume_range: (min, max) volume
            - sectors: Sector distribution (if available)

        Examples:
        ---------
        >>> summary = universe_manager.get_universe_summary()
        >>> print(f"Universe: {summary['symbol_count']} symbols")
        """
        if symbols is None:
            symbols = self.build_universe()

        # Get quotes for analysis
        df = self.get_universe_quotes(symbols)

        summary = {
            'symbol_count': len(symbols),
            'sources': config.universe.sources,
            'timestamp': datetime.now().isoformat()
        }

        if not df.empty:
            summary['price_range'] = (
                float(df['last'].min()),
                float(df['last'].max())
            )
            summary['volume_range'] = (
                int(df['volume'].min()),
                int(df['volume'].max())
            )
            summary['avg_price'] = float(df['last'].mean())
            summary['avg_volume'] = int(df['volume'].mean())

        return summary

    def refresh_universe(self) -> List[str]:
        """
        Refresh universe by rebuilding and filtering.

        Returns:
        --------
        list of str
            Fresh universe after filters

        Examples:
        ---------
        >>> universe = universe_manager.refresh_universe()
        >>> print(f"Refreshed universe: {len(universe)} symbols")
        """
        # Build raw universe
        raw_universe = self.build_universe()

        # Apply filters
        filtered_universe = self.filter_universe(raw_universe)

        # Cache result
        self.cache['universe'] = filtered_universe
        self.cache['universe_timestamp'] = datetime.now()

        logger.info(f"Refreshed universe: {len(filtered_universe)} symbols")

        return filtered_universe


# Global singleton instance
universe_manager = UniverseManager()
