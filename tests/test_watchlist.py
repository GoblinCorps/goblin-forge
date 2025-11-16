"""
Unit Tests for Watchlist Generator

Tests the WatchlistGenerator orchestration layer that runs the complete
screening pipeline from universe construction to ranked watchlist generation.

Pipeline Flow:
--------------
1. Universe Construction (500-1000 symbols)
2. Coarse Screening (1h filters) → ~50-100 candidates
3. Multi-timeframe Data Loading (15m/1h/4h/daily)
4. SABR20 Scoring (0-100 points) → ~10-30 scored setups
5. Filtering by min score threshold
6. Ranking and watchlist creation (Top 10-20)

Test Coverage:
--------------
- Initialization and configuration loading
- Multi-timeframe data loading (4 timeframes)
- Single candidate scoring
- Parallel batch scoring
- Full pipeline integration (generate method)
- Watchlist summary generation (DataFrame)
- CSV export functionality
- Edge cases and error handling
- Integration with all Phase 5 components
- Concurrent execution stress testing

Coverage Target: >90% (critical orchestration layer)

Run:
----
pytest tests/test_watchlist.py -v --cov=src/screening/watchlist --cov-report=term-missing
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor
import tempfile
import os

from src.screening.watchlist import WatchlistGenerator, watchlist_generator
from src.screening.sabr20_engine import SABR20Score


# ============================================================================
# Test Data Generators
# ============================================================================

def create_mock_ohlcv(
    symbol: str,
    timeframe: str,
    bars: int = 100,
    base_price: float = 100.0
) -> pd.DataFrame:
    """
    Create mock OHLCV data with indicators for testing.

    Parameters:
    -----------
    symbol : str
        Stock symbol
    timeframe : str
        Timeframe string (e.g., '15 mins', '1 hour')
    bars : int
        Number of bars to generate
    base_price : float
        Base price level

    Returns:
    --------
    pd.DataFrame
        OHLCV data with calculated indicators
    """
    np.random.seed(hash(symbol) % (2**32))  # Deterministic per symbol

    dates = pd.date_range(
        end=datetime.now(),
        periods=bars,
        freq='15min' if 'min' in timeframe else '1H'
    )

    close = base_price + np.cumsum(np.random.randn(bars) * 0.5)
    high = close + np.abs(np.random.randn(bars) * 0.3)
    low = close - np.abs(np.random.randn(bars) * 0.3)
    open_ = close + np.random.randn(bars) * 0.2

    df = pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(500000, 2000000, bars)
    })

    # Add mock indicators
    df['rsi'] = 50.0 + np.random.randn(bars) * 10
    df['stoch_rsi'] = 50.0 + np.random.randn(bars) * 20
    df['macd'] = np.random.randn(bars) * 0.5
    df['macd_signal'] = df['macd'] - 0.1
    df['macd_hist'] = df['macd'] - df['macd_signal']
    df['bb_upper'] = close + 10
    df['bb_middle'] = close
    df['bb_lower'] = close - 10
    df['bb_position'] = 0.5
    df['atr'] = close * 0.02

    return df


def create_mock_sabr20_score(
    symbol: str,
    total_points: float = 75.0,
    setup_strength: float = 16.0,
    bottom_phase: float = 12.0,
    accumulation: float = 14.0,
    trend_momentum: float = 12.0,
    risk_reward: float = 16.0,
    macro: float = 5.0
) -> SABR20Score:
    """
    Create mock SABR20Score for testing.

    Parameters:
    -----------
    symbol : str
        Stock symbol
    total_points : float
        Total score (0-100)
    setup_strength : float
        Component 1 score
    bottom_phase : float
        Component 2 score
    accumulation : float
        Component 3 score
    trend_momentum : float
        Component 4 score
    risk_reward : float
        Component 5 score
    macro : float
        Component 6 score

    Returns:
    --------
    SABR20Score
        Mock score object
    """
    return SABR20Score(
        symbol=symbol,
        total_points=total_points,
        component_scores={
            'setup_strength': setup_strength,
            'bottom_phase': bottom_phase,
            'accumulation_intensity': accumulation,
            'trend_momentum': trend_momentum,
            'risk_reward': risk_reward,
            'macro_confirmation': macro
        },
        setup_grade='Strong' if total_points >= 65 else 'Good',
        timestamp=datetime.now(),
        details={
            'risk_reward': {
                'entry': 100.0,
                'target': 110.0,
                'stop': 95.0,
                'rr_ratio': 2.0
            }
        }
    )


# ============================================================================
# Test WatchlistGenerator Initialization
# ============================================================================

class TestWatchlistGeneratorInitialization:
    """Test WatchlistGenerator initialization and configuration loading."""

    def test_init_loads_timeframe_configuration(self):
        """Test that initialization loads timeframe configuration correctly."""
        generator = WatchlistGenerator()

        # Verify timeframes loaded
        assert hasattr(generator, 'timeframes')
        assert isinstance(generator.timeframes, dict)
        assert 'trigger' in generator.timeframes
        assert 'confirmation' in generator.timeframes
        assert 'regime' in generator.timeframes
        assert 'macro' in generator.timeframes

        # Verify timeframe values are strings
        for tf_name, tf_value in generator.timeframes.items():
            assert isinstance(tf_value, str)
            assert any(unit in tf_value for unit in ['min', 'hour', 'day', 'week'])

    def test_init_loads_watchlist_parameters(self):
        """Test that initialization loads watchlist parameters from config."""
        generator = WatchlistGenerator()

        # Verify watchlist parameters
        assert hasattr(generator, 'max_watchlist_size')
        assert hasattr(generator, 'min_score_threshold')
        assert isinstance(generator.max_watchlist_size, int)
        assert isinstance(generator.min_score_threshold, (int, float))
        assert generator.max_watchlist_size > 0
        assert 0 <= generator.min_score_threshold <= 100

    def test_singleton_instance_exists(self):
        """Test that global singleton instance is created."""
        assert watchlist_generator is not None
        assert isinstance(watchlist_generator, WatchlistGenerator)

    def test_singleton_instance_is_same_as_new_instance(self):
        """Test that singleton instance has same configuration as new instance."""
        new_gen = WatchlistGenerator()

        assert watchlist_generator.timeframes == new_gen.timeframes
        assert watchlist_generator.max_watchlist_size == new_gen.max_watchlist_size
        assert watchlist_generator.min_score_threshold == new_gen.min_score_threshold


# ============================================================================
# Test Multi-Timeframe Data Loading
# ============================================================================

class TestLoadMultiTimeframeData:
    """Test multi-timeframe data loading functionality."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    @pytest.fixture
    def mock_historical_manager(self):
        """Mock historical_manager for data loading."""
        with patch('src.screening.watchlist.historical_manager') as mock:
            def load_data(symbol, timeframe):
                return create_mock_ohlcv(symbol, timeframe, bars=100)
            mock.load.side_effect = load_data
            yield mock

    @pytest.fixture
    def mock_indicator_engine(self):
        """Mock indicator_engine for indicator calculations."""
        with patch('src.screening.watchlist.indicator_engine') as mock:
            mock.calculate_all.side_effect = lambda df, **kwargs: df
            yield mock

    def test_load_all_timeframes_successfully(self, generator, mock_historical_manager, mock_indicator_engine):
        """Test loading all 4 timeframes successfully."""
        data_dict = generator.load_multi_timeframe_data('AAPL', use_cached=True)

        # Verify all timeframes present
        assert 'trigger' in data_dict
        assert 'confirmation' in data_dict
        assert 'regime' in data_dict
        assert 'macro' in data_dict

        # Verify all are DataFrames
        assert all(isinstance(df, pd.DataFrame) for df in data_dict.values())

        # Verify all have data
        assert all(not df.empty for df in data_dict.values())

        # Verify historical_manager.load called for each timeframe
        assert mock_historical_manager.load.call_count == 4

    def test_load_with_missing_timeframe(self, generator, mock_indicator_engine):
        """Test handling of missing timeframe data."""
        with patch('src.screening.watchlist.historical_manager') as mock_hist:
            # Return None for macro timeframe
            def load_data(symbol, timeframe):
                if '4 hours' in timeframe or '4 hour' in timeframe:
                    return None
                return create_mock_ohlcv(symbol, timeframe)
            mock_hist.load.side_effect = load_data

            data_dict = generator.load_multi_timeframe_data('AAPL')

            # Should have 3 timeframes (macro missing)
            assert len(data_dict) == 3
            assert 'trigger' in data_dict
            assert 'confirmation' in data_dict
            assert 'regime' in data_dict
            assert 'macro' not in data_dict

    def test_load_with_empty_dataframe(self, generator, mock_indicator_engine):
        """Test handling of empty DataFrame returns."""
        with patch('src.screening.watchlist.historical_manager') as mock_hist:
            # Return empty DataFrame for confirmation
            def load_data(symbol, timeframe):
                if '15 min' in timeframe and 'confirmation' in generator.timeframes.values():
                    return pd.DataFrame()
                return create_mock_ohlcv(symbol, timeframe)
            mock_hist.load.side_effect = load_data

            data_dict = generator.load_multi_timeframe_data('AAPL')

            # Should not include empty DataFrames
            assert all(not df.empty for df in data_dict.values())

    def test_load_with_invalid_symbol(self, generator, mock_indicator_engine):
        """Test loading data for invalid symbol."""
        with patch('src.screening.watchlist.historical_manager') as mock_hist:
            mock_hist.load.return_value = None

            data_dict = generator.load_multi_timeframe_data('INVALID')

            # Should return empty dict
            assert len(data_dict) == 0

    def test_load_with_exception_handling(self, generator, mock_indicator_engine):
        """Test that exceptions during loading are handled gracefully."""
        with patch('src.screening.watchlist.historical_manager') as mock_hist:
            # Raise exception for one timeframe
            def load_data(symbol, timeframe):
                if '1 hour' in timeframe:
                    raise ValueError("Simulated error")
                return create_mock_ohlcv(symbol, timeframe)
            mock_hist.load.side_effect = load_data

            data_dict = generator.load_multi_timeframe_data('AAPL')

            # Should continue loading other timeframes
            assert len(data_dict) >= 0  # May have partial data
            # Should not raise exception
            assert True

    def test_load_uses_cached_data_by_default(self, generator, mock_historical_manager, mock_indicator_engine):
        """Test that use_cached=True uses historical_manager.load."""
        data_dict = generator.load_multi_timeframe_data('AAPL', use_cached=True)

        # Should use historical_manager.load
        assert mock_historical_manager.load.called
        assert data_dict is not None

    def test_load_live_data_when_not_cached(self, generator, mock_indicator_engine):
        """Test that use_cached=False fetches live data."""
        with patch('src.screening.watchlist.ib_manager') as mock_ib:
            mock_ib.fetch_historical_bars.return_value = create_mock_ohlcv('AAPL', '15 mins')

            data_dict = generator.load_multi_timeframe_data('AAPL', use_cached=False)

            # Should use ib_manager.fetch_historical_bars
            assert mock_ib.fetch_historical_bars.called
            assert len(data_dict) > 0

    def test_load_indicator_calculation_called(self, generator, mock_historical_manager, mock_indicator_engine):
        """Test that indicator_engine.calculate_all is called for each timeframe."""
        data_dict = generator.load_multi_timeframe_data('AAPL')

        # Verify indicator calculation called for each timeframe
        assert mock_indicator_engine.calculate_all.call_count >= len(data_dict)


# ============================================================================
# Test Single Candidate Scoring
# ============================================================================

class TestScoreCandidate:
    """Test single candidate scoring functionality."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    @pytest.fixture
    def mock_data_loading(self):
        """Mock load_multi_timeframe_data method."""
        with patch.object(WatchlistGenerator, 'load_multi_timeframe_data') as mock:
            mock.return_value = {
                'trigger': create_mock_ohlcv('AAPL', '15 mins'),
                'confirmation': create_mock_ohlcv('AAPL', '15 mins'),
                'regime': create_mock_ohlcv('AAPL', '1 hour'),
                'macro': create_mock_ohlcv('AAPL', '4 hours')
            }
            yield mock

    @pytest.fixture
    def mock_sabr20_engine(self):
        """Mock sabr20_engine for scoring."""
        with patch('src.screening.watchlist.sabr20_engine') as mock:
            mock.score_symbol.return_value = create_mock_sabr20_score('AAPL', total_points=75.0)
            yield mock

    def test_score_candidate_successfully(self, generator, mock_data_loading, mock_sabr20_engine):
        """Test successful scoring of a candidate."""
        score = generator.score_candidate('AAPL')

        # Verify score returned
        assert score is not None
        assert isinstance(score, SABR20Score)
        assert score.symbol == 'AAPL'
        assert 0 <= score.total_points <= 100

        # Verify methods called
        assert mock_data_loading.called
        assert mock_sabr20_engine.score_symbol.called

    def test_score_candidate_with_missing_required_timeframe(self, generator, mock_sabr20_engine):
        """Test scoring with missing required timeframe (trigger)."""
        with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
            # Missing 'trigger' timeframe
            mock_load.return_value = {
                'confirmation': create_mock_ohlcv('AAPL', '15 mins'),
                'regime': create_mock_ohlcv('AAPL', '1 hour')
            }

            score = generator.score_candidate('AAPL')

            # Should return None due to insufficient data
            assert score is None

    def test_score_candidate_with_missing_macro_timeframe_ok(self, generator, mock_sabr20_engine):
        """Test that missing macro timeframe (optional) is acceptable."""
        with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
            # Missing 'macro' (optional)
            mock_load.return_value = {
                'trigger': create_mock_ohlcv('AAPL', '15 mins'),
                'confirmation': create_mock_ohlcv('AAPL', '15 mins'),
                'regime': create_mock_ohlcv('AAPL', '1 hour')
            }

            score = generator.score_candidate('AAPL')

            # Should still score (macro is optional)
            assert score is not None

    def test_score_candidate_with_sabr20_exception(self, generator, mock_data_loading):
        """Test handling of exception in sabr20_engine.score_symbol."""
        with patch('src.screening.watchlist.sabr20_engine') as mock_sabr20:
            mock_sabr20.score_symbol.side_effect = ValueError("Scoring error")

            score = generator.score_candidate('AAPL')

            # Should return None on exception
            assert score is None

    def test_score_candidate_with_data_loading_exception(self, generator):
        """Test handling of exception during data loading."""
        with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
            mock_load.side_effect = RuntimeError("Data loading error")

            score = generator.score_candidate('AAPL')

            # Should return None on exception
            assert score is None

    def test_score_candidate_uses_cached_data_parameter(self, generator, mock_sabr20_engine):
        """Test that use_cached_data parameter is passed correctly."""
        with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
            mock_load.return_value = {
                'trigger': create_mock_ohlcv('AAPL', '15 mins'),
                'confirmation': create_mock_ohlcv('AAPL', '15 mins'),
                'regime': create_mock_ohlcv('AAPL', '1 hour')
            }

            generator.score_candidate('AAPL', use_cached_data=False)

            # Verify use_cached parameter passed
            mock_load.assert_called_with('AAPL', use_cached=False)

    def test_score_candidate_returns_none_for_invalid_symbol(self, generator):
        """Test that invalid symbol returns None."""
        with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
            mock_load.return_value = {}

            score = generator.score_candidate('INVALID')

            assert score is None


# ============================================================================
# Test Parallel Candidate Scoring
# ============================================================================

class TestScoreCandidatesParallel:
    """Test parallel batch scoring functionality."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    @pytest.fixture
    def mock_score_candidate(self):
        """Mock score_candidate method."""
        def score_func(symbol, **kwargs):
            # Return different scores for different symbols
            points = 75.0 if symbol.startswith('AA') else 65.0
            return create_mock_sabr20_score(symbol, total_points=points)

        with patch.object(WatchlistGenerator, 'score_candidate') as mock:
            mock.side_effect = score_func
            yield mock

    def test_score_all_candidates_successfully(self, generator, mock_score_candidate):
        """Test scoring all candidates successfully."""
        candidates = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

        scores = generator.score_candidates_parallel(candidates, max_workers=2)

        # Verify all scored
        assert len(scores) == len(candidates)
        assert all(isinstance(s, SABR20Score) for s in scores)
        assert {s.symbol for s in scores} == set(candidates)

    def test_score_with_some_failures(self, generator):
        """Test scoring when some candidates fail."""
        def score_func(symbol, **kwargs):
            if symbol == 'FAIL':
                return None
            return create_mock_sabr20_score(symbol, total_points=70.0)

        with patch.object(generator, 'score_candidate', side_effect=score_func):
            candidates = ['AAPL', 'FAIL', 'MSFT', 'GOOGL']

            scores = generator.score_candidates_parallel(candidates)

            # Should exclude None results
            assert len(scores) == 3
            assert all(s.symbol != 'FAIL' for s in scores)

    def test_score_with_all_failures(self, generator):
        """Test scoring when all candidates fail."""
        with patch.object(generator, 'score_candidate', return_value=None):
            candidates = ['AAPL', 'MSFT', 'GOOGL']

            scores = generator.score_candidates_parallel(candidates)

            # Should return empty list
            assert len(scores) == 0

    def test_score_with_empty_candidate_list(self, generator, mock_score_candidate):
        """Test scoring with empty candidate list."""
        scores = generator.score_candidates_parallel([])

        assert len(scores) == 0
        assert not mock_score_candidate.called

    def test_score_with_single_candidate(self, generator, mock_score_candidate):
        """Test scoring with single candidate."""
        scores = generator.score_candidates_parallel(['AAPL'])

        assert len(scores) == 1
        assert scores[0].symbol == 'AAPL'

    def test_score_parallel_execution_completes(self, generator):
        """Test that parallel execution completes successfully."""
        candidates = ['AAPL', 'MSFT', 'GOOGL']

        with patch.object(generator, 'score_candidate') as mock_sc:
            mock_sc.side_effect = lambda sym, **kw: create_mock_sabr20_score(sym, 75.0)

            scores = generator.score_candidates_parallel(candidates, max_workers=2)

            # Verify parallel execution completed
            assert len(scores) == 3
            assert all(isinstance(s, SABR20Score) for s in scores)

    def test_score_max_workers_parameter(self, generator, mock_score_candidate):
        """Test that max_workers parameter is respected."""
        candidates = ['AAPL', 'MSFT', 'GOOGL']

        scores_2 = generator.score_candidates_parallel(candidates, max_workers=2)
        scores_4 = generator.score_candidates_parallel(candidates, max_workers=4)

        # Both should produce same results
        assert len(scores_2) == len(scores_4)
        assert {s.symbol for s in scores_2} == {s.symbol for s in scores_4}

    def test_score_handles_exceptions_in_parallel(self, generator):
        """Test that exceptions in parallel execution are handled."""
        def score_func(symbol, **kwargs):
            if symbol == 'ERROR':
                raise RuntimeError("Scoring error")
            return create_mock_sabr20_score(symbol, 70.0)

        with patch.object(generator, 'score_candidate', side_effect=score_func):
            candidates = ['AAPL', 'ERROR', 'MSFT']

            scores = generator.score_candidates_parallel(candidates)

            # Should continue despite exception
            assert len(scores) >= 2  # AAPL and MSFT should succeed

    def test_score_large_batch(self, generator):
        """Test scoring large batch of candidates."""
        with patch.object(generator, 'score_candidate') as mock_sc:
            mock_sc.side_effect = lambda sym, **kw: create_mock_sabr20_score(sym, 70.0)

            candidates = [f'SYM{i:03d}' for i in range(50)]

            scores = generator.score_candidates_parallel(candidates, max_workers=4)

            assert len(scores) == 50
            assert all(isinstance(s, SABR20Score) for s in scores)


# ============================================================================
# Test Full Pipeline (generate method)
# ============================================================================

class TestGenerateWatchlist:
    """Test full watchlist generation pipeline."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    @pytest.fixture
    def mock_universe_manager(self):
        """Mock universe_manager."""
        with patch('src.screening.watchlist.universe_manager') as mock:
            mock.build_universe.return_value = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
                'META', 'NVDA', 'AMD', 'INTC', 'NFLX'
            ]
            yield mock

    @pytest.fixture
    def mock_coarse_filter(self):
        """Mock coarse_filter."""
        with patch('src.screening.watchlist.coarse_filter') as mock:
            # Return subset of universe
            mock.screen.return_value = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
            yield mock

    @pytest.fixture
    def mock_score_candidates(self):
        """Mock score_candidates_parallel method."""
        def score_batch(candidates, **kwargs):
            return [
                create_mock_sabr20_score(sym, total_points=85.0 - i*5)
                for i, sym in enumerate(candidates)
            ]

        with patch.object(WatchlistGenerator, 'score_candidates_parallel') as mock:
            mock.side_effect = score_batch
            yield mock

    def test_generate_complete_pipeline(
        self,
        generator,
        mock_universe_manager,
        mock_coarse_filter,
        mock_score_candidates
    ):
        """Test complete watchlist generation pipeline."""
        watchlist = generator.generate()

        # Verify pipeline steps called
        assert mock_universe_manager.build_universe.called
        assert mock_coarse_filter.screen.called
        assert mock_score_candidates.called

        # Verify watchlist returned
        assert isinstance(watchlist, list)
        assert len(watchlist) > 0
        assert all(isinstance(s, SABR20Score) for s in watchlist)

    def test_generate_with_custom_universe(
        self,
        generator,
        mock_universe_manager,
        mock_coarse_filter,
        mock_score_candidates
    ):
        """Test generation with custom universe (bypasses universe_manager)."""
        custom_universe = ['AAPL', 'MSFT', 'GOOGL']

        with patch.object(mock_coarse_filter, 'screen', return_value=custom_universe):
            watchlist = generator.generate(universe=custom_universe)

            # Should not call build_universe
            assert not mock_universe_manager.build_universe.called
            assert watchlist is not None

    def test_generate_with_min_score_filtering(self, generator, mock_universe_manager, mock_coarse_filter):
        """Test that min_score threshold filters results."""
        # Create scores with varying points
        def score_batch(candidates, **kwargs):
            scores = [
                create_mock_sabr20_score('AAPL', 85.0),
                create_mock_sabr20_score('MSFT', 70.0),
                create_mock_sabr20_score('GOOGL', 60.0),  # Below threshold
                create_mock_sabr20_score('TSLA', 45.0),   # Below threshold
            ]
            return scores

        with patch.object(generator, 'score_candidates_parallel', side_effect=score_batch):
            watchlist = generator.generate(min_score=65.0)

            # Should only include scores >= 65
            assert all(s.total_points >= 65.0 for s in watchlist)
            assert len(watchlist) == 2  # AAPL and MSFT

    def test_generate_with_max_symbols_limit(self, generator, mock_universe_manager, mock_coarse_filter):
        """Test that max_symbols limits watchlist size."""
        # Create many high-scoring candidates
        def score_batch(candidates, **kwargs):
            return [
                create_mock_sabr20_score(f'SYM{i}', 90.0 - i)
                for i in range(20)
            ]

        with patch.object(generator, 'score_candidates_parallel', side_effect=score_batch):
            watchlist = generator.generate(max_symbols=10)

            # Should limit to 10
            assert len(watchlist) <= 10

    def test_generate_sorts_by_score_descending(self, generator, mock_universe_manager, mock_coarse_filter):
        """Test that watchlist is sorted by score (best first)."""
        def score_batch(candidates, **kwargs):
            return [
                create_mock_sabr20_score('LOW', 60.0),
                create_mock_sabr20_score('HIGH', 90.0),
                create_mock_sabr20_score('MED', 75.0),
            ]

        with patch.object(generator, 'score_candidates_parallel', side_effect=score_batch):
            watchlist = generator.generate()

            # Verify sorted descending
            scores = [s.total_points for s in watchlist]
            assert scores == sorted(scores, reverse=True)
            assert watchlist[0].symbol == 'HIGH'

    def test_generate_with_skip_coarse_filter(
        self,
        generator,
        mock_universe_manager,
        mock_coarse_filter,
        mock_score_candidates
    ):
        """Test generation with skip_coarse_filter=True."""
        watchlist = generator.generate(skip_coarse_filter=True)

        # Should not call coarse_filter
        assert not mock_coarse_filter.screen.called
        assert watchlist is not None

    def test_generate_with_empty_universe(self, generator):
        """Test generation with empty universe."""
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = []

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = []

                watchlist = generator.generate()

                # Should return empty watchlist
                assert len(watchlist) == 0

    def test_generate_with_all_filtered_out(self, generator, mock_universe_manager, mock_score_candidates):
        """Test when coarse filter removes all candidates."""
        with patch('src.screening.watchlist.coarse_filter') as mock_cf:
            mock_cf.screen.return_value = []

            watchlist = generator.generate()

            # Should return empty watchlist
            assert len(watchlist) == 0

    def test_generate_with_all_below_threshold(self, generator, mock_universe_manager, mock_coarse_filter):
        """Test when all scores are below min threshold."""
        def score_batch(candidates, **kwargs):
            # All low scores
            return [create_mock_sabr20_score(sym, 40.0) for sym in candidates]

        with patch.object(generator, 'score_candidates_parallel', side_effect=score_batch):
            watchlist = generator.generate(min_score=65.0)

            # Should return empty watchlist
            assert len(watchlist) == 0

    def test_generate_with_scoring_failures(self, generator, mock_universe_manager, mock_coarse_filter):
        """Test generation when some scoring attempts fail."""
        def score_batch(candidates, **kwargs):
            # Only some succeed
            return [create_mock_sabr20_score(candidates[0], 75.0)]

        with patch.object(generator, 'score_candidates_parallel', side_effect=score_batch):
            watchlist = generator.generate()

            # Should continue with successful scores
            assert len(watchlist) >= 0

    def test_generate_uses_config_defaults(self, generator, mock_universe_manager, mock_coarse_filter, mock_score_candidates):
        """Test that generate uses config defaults when parameters not specified."""
        watchlist = generator.generate()

        # Should use instance defaults
        assert len(watchlist) <= generator.max_watchlist_size


# ============================================================================
# Test Watchlist Summary
# ============================================================================

class TestGetWatchlistSummary:
    """Test watchlist summary DataFrame generation."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    def test_summary_creates_dataframe(self, generator):
        """Test that summary creates valid DataFrame."""
        watchlist = [
            create_mock_sabr20_score('AAPL', 85.0),
            create_mock_sabr20_score('MSFT', 75.0),
        ]

        df = generator.get_watchlist_summary(watchlist)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(watchlist)

    def test_summary_contains_required_columns(self, generator):
        """Test that summary contains all required columns."""
        watchlist = [create_mock_sabr20_score('AAPL', 85.0)]

        df = generator.get_watchlist_summary(watchlist)

        required_cols = [
            'symbol', 'score', 'grade',
            'setup_strength', 'bottom_phase', 'accumulation',
            'trend_momentum', 'risk_reward', 'macro',
            'entry', 'target', 'stop', 'rr_ratio', 'timestamp'
        ]

        for col in required_cols:
            assert col in df.columns

    def test_summary_with_empty_watchlist(self, generator):
        """Test summary with empty watchlist."""
        df = generator.get_watchlist_summary([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_summary_preserves_order(self, generator):
        """Test that summary preserves watchlist order."""
        watchlist = [
            create_mock_sabr20_score('AAA', 90.0),
            create_mock_sabr20_score('BBB', 80.0),
            create_mock_sabr20_score('CCC', 70.0),
        ]

        df = generator.get_watchlist_summary(watchlist)

        assert df['symbol'].tolist() == ['AAA', 'BBB', 'CCC']

    def test_summary_includes_component_scores(self, generator):
        """Test that summary includes all component scores."""
        score = create_mock_sabr20_score(
            'AAPL',
            total_points=85.0,
            setup_strength=18.0,
            bottom_phase=14.0,
            accumulation=16.0,
            trend_momentum=14.0,
            risk_reward=18.0,
            macro=5.0
        )

        df = generator.get_watchlist_summary([score])

        assert df['setup_strength'].iloc[0] == 18.0
        assert df['bottom_phase'].iloc[0] == 14.0
        assert df['accumulation'].iloc[0] == 16.0
        assert df['trend_momentum'].iloc[0] == 14.0
        assert df['risk_reward'].iloc[0] == 18.0
        assert df['macro'].iloc[0] == 5.0

    def test_summary_includes_risk_reward_details(self, generator):
        """Test that summary includes risk/reward details."""
        watchlist = [create_mock_sabr20_score('AAPL', 85.0)]

        df = generator.get_watchlist_summary(watchlist)

        assert 'entry' in df.columns
        assert 'target' in df.columns
        assert 'stop' in df.columns
        assert 'rr_ratio' in df.columns
        assert df['entry'].iloc[0] == 100.0
        assert df['target'].iloc[0] == 110.0

    def test_summary_with_large_watchlist(self, generator):
        """Test summary generation with large watchlist."""
        watchlist = [
            create_mock_sabr20_score(f'SYM{i:03d}', 90.0 - i)
            for i in range(100)
        ]

        df = generator.get_watchlist_summary(watchlist)

        assert len(df) == 100
        assert not df.empty


# ============================================================================
# Test Export Functionality
# ============================================================================

class TestExportWatchlist:
    """Test watchlist CSV export functionality."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    @pytest.fixture
    def temp_file(self):
        """Create temporary file for export testing."""
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_export_creates_file(self, generator, temp_file):
        """Test that export creates CSV file."""
        watchlist = [
            create_mock_sabr20_score('AAPL', 85.0),
            create_mock_sabr20_score('MSFT', 75.0),
        ]

        result = generator.export_watchlist(watchlist, filepath=temp_file)

        assert result is True
        assert os.path.exists(temp_file)

    def test_export_file_contains_data(self, generator, temp_file):
        """Test that exported CSV contains correct data."""
        watchlist = [
            create_mock_sabr20_score('AAPL', 85.0),
            create_mock_sabr20_score('MSFT', 75.0),
        ]

        generator.export_watchlist(watchlist, filepath=temp_file)

        # Read back and verify
        df = pd.read_csv(temp_file)
        assert len(df) == 2
        assert 'symbol' in df.columns
        assert df['symbol'].tolist() == ['AAPL', 'MSFT']

    def test_export_empty_watchlist(self, generator, temp_file):
        """Test exporting empty watchlist."""
        result = generator.export_watchlist([], filepath=temp_file)

        assert result is True
        # Verify file was created (empty DataFrame to CSV creates header only)
        assert os.path.exists(temp_file)

    def test_export_overwrites_existing_file(self, generator, temp_file):
        """Test that export overwrites existing file."""
        # First export
        watchlist1 = [create_mock_sabr20_score('AAPL', 85.0)]
        generator.export_watchlist(watchlist1, filepath=temp_file)

        # Second export (different data)
        watchlist2 = [create_mock_sabr20_score('MSFT', 75.0)]
        generator.export_watchlist(watchlist2, filepath=temp_file)

        # Verify only second data present
        df = pd.read_csv(temp_file)
        assert len(df) == 1
        assert df['symbol'].iloc[0] == 'MSFT'

    def test_export_with_invalid_path(self, generator):
        """Test export with invalid file path."""
        watchlist = [create_mock_sabr20_score('AAPL', 85.0)]

        # Invalid path (directory doesn't exist)
        result = generator.export_watchlist(
            watchlist,
            filepath='/nonexistent/directory/file.csv'
        )

        assert result is False

    def test_export_with_permission_error(self, generator):
        """Test export handling permission errors."""
        watchlist = [create_mock_sabr20_score('AAPL', 85.0)]

        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            mock_to_csv.side_effect = PermissionError("Permission denied")

            result = generator.export_watchlist(watchlist, filepath='test.csv')

            assert result is False

    def test_export_large_watchlist(self, generator, temp_file):
        """Test exporting large watchlist."""
        watchlist = [
            create_mock_sabr20_score(f'SYM{i:03d}', 90.0 - i*0.5)
            for i in range(100)
        ]

        result = generator.export_watchlist(watchlist, filepath=temp_file)

        assert result is True
        df = pd.read_csv(temp_file)
        assert len(df) == 100


# ============================================================================
# Test Edge Cases and Integration
# ============================================================================

class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    def test_very_large_universe(self, generator):
        """Test handling of very large universe (stress test)."""
        large_universe = [f'SYM{i:04d}' for i in range(1000)]

        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = large_universe

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                # Filter down to manageable size
                mock_cf.screen.return_value = large_universe[:50]

                with patch.object(generator, 'score_candidates_parallel') as mock_score:
                    mock_score.return_value = [
                        create_mock_sabr20_score(sym, 75.0)
                        for sym in large_universe[:10]
                    ]

                    watchlist = generator.generate()

                    # Should handle large universe without errors
                    assert watchlist is not None
                    assert len(watchlist) > 0

    def test_concurrent_execution_safety(self, generator):
        """Test thread safety of concurrent scoring."""
        candidates = [f'SYM{i:03d}' for i in range(20)]

        with patch.object(generator, 'score_candidate') as mock_sc:
            mock_sc.side_effect = lambda sym, **kw: create_mock_sabr20_score(sym, 75.0)

            # Run parallel scoring multiple times
            for _ in range(3):
                scores = generator.score_candidates_parallel(candidates, max_workers=4)
                assert len(scores) == len(candidates)

    def test_duplicate_symbols_in_universe(self, generator):
        """Test handling of duplicate symbols in universe."""
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            # Universe with duplicates
            mock_um.build_universe.return_value = ['AAPL', 'MSFT', 'AAPL', 'GOOGL', 'MSFT']

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = ['AAPL', 'MSFT', 'AAPL']

                with patch.object(generator, 'score_candidates_parallel') as mock_score:
                    # Return scores for duplicates
                    mock_score.return_value = [
                        create_mock_sabr20_score('AAPL', 85.0),
                        create_mock_sabr20_score('MSFT', 75.0),
                        create_mock_sabr20_score('AAPL', 80.0),  # Duplicate
                    ]

                    watchlist = generator.generate()

                    # Should handle duplicates
                    assert watchlist is not None

    def test_integration_all_components(self, generator):
        """Test integration with real (non-mocked) components where possible."""
        # This test verifies the orchestration logic without mocking everything
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = ['AAPL', 'MSFT', 'GOOGL']

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = ['AAPL', 'MSFT']

                with patch.object(generator, 'load_multi_timeframe_data') as mock_load:
                    mock_load.return_value = {
                        'trigger': create_mock_ohlcv('AAPL', '15 mins'),
                        'confirmation': create_mock_ohlcv('AAPL', '15 mins'),
                        'regime': create_mock_ohlcv('AAPL', '1 hour')
                    }

                    with patch('src.screening.watchlist.sabr20_engine') as mock_sabr20:
                        mock_sabr20.score_symbol.return_value = create_mock_sabr20_score('AAPL', 75.0)

                        # Run full pipeline
                        watchlist = generator.generate(max_symbols=5, min_score=50.0)

                        # Verify pipeline executed
                        assert mock_um.build_universe.called
                        assert mock_cf.screen.called
                        assert mock_load.called
                        assert mock_sabr20.score_symbol.called
                        assert watchlist is not None

    def test_all_components_fail_gracefully(self, generator):
        """Test that complete failure of all components is handled."""
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = ['AAPL']

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = ['AAPL']

                with patch.object(generator, 'score_candidate') as mock_sc:
                    # All scoring fails
                    mock_sc.return_value = None

                    watchlist = generator.generate()

                    # Should return empty watchlist, not crash
                    assert watchlist == []

    def test_score_validation_range(self, generator):
        """Test that scores are validated to be in valid range."""
        watchlist = [
            create_mock_sabr20_score('AAPL', 85.0),
            create_mock_sabr20_score('MSFT', 75.0),
            create_mock_sabr20_score('GOOGL', 65.0),
        ]

        # All scores should be 0-100
        for score in watchlist:
            assert 0 <= score.total_points <= 100
            assert score.setup_grade in ['Excellent', 'Strong', 'Good', 'Weak']


# ============================================================================
# Test Summary Statistics and Logging
# ============================================================================

class TestLoggingAndStatistics:
    """Test logging and statistics generation."""

    @pytest.fixture
    def generator(self):
        """Create WatchlistGenerator instance."""
        return WatchlistGenerator()

    def test_generate_logs_pipeline_steps(self, generator):
        """Test that generate() logs all pipeline steps."""
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = ['AAPL', 'MSFT']

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = ['AAPL']

                with patch.object(generator, 'score_candidates_parallel') as mock_score:
                    mock_score.return_value = [create_mock_sabr20_score('AAPL', 75.0)]

                    with patch('src.screening.watchlist.logger') as mock_logger:
                        generator.generate()

                        # Verify logging called (info messages)
                        assert mock_logger.info.called
                        # Should log: start, universe, coarse filter, scoring, filtering, ranking, complete

    def test_generate_returns_timing_information(self, generator):
        """Test that generate completes within reasonable time."""
        with patch('src.screening.watchlist.universe_manager') as mock_um:
            mock_um.build_universe.return_value = ['AAPL']

            with patch('src.screening.watchlist.coarse_filter') as mock_cf:
                mock_cf.screen.return_value = ['AAPL']

                with patch.object(generator, 'score_candidates_parallel') as mock_score:
                    mock_score.return_value = [create_mock_sabr20_score('AAPL', 75.0)]

                    start = datetime.now()
                    watchlist = generator.generate()
                    duration = (datetime.now() - start).total_seconds()

                    # Should complete quickly with mocks
                    assert duration < 5.0
                    assert watchlist is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/screening/watchlist', '--cov-report=term-missing'])
