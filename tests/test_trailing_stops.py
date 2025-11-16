"""
Comprehensive Test Suite for Trailing Stop Management

Test Coverage:
--------------
1. Configuration Tests (5 tests)
2. Stop Calculation Tests (10 tests)
3. Integration Tests (8 tests)
4. ATR Tests (5 tests)
5. Status and History Tests (4 tests)
6. Edge Cases (3 tests)

Total: 35+ tests with >80% coverage target
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from src.execution.trailing_stop_manager import (
    TrailingStopManager,
    TrailingConfig,
    StopAdjustment,
    trailing_stop_manager
)
from src.execution.order_manager import OrderManager, Position
from src.data.trade_database import TradeDatabase


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fresh_trailing_manager():
    """Create fresh trailing stop manager instance for each test."""
    manager = TrailingStopManager()
    manager.trailing_configs.clear()
    manager.adjustment_history.clear()
    manager.last_check_time = None
    return manager


@pytest.fixture
def mock_order_manager():
    """Mock order manager with test positions."""
    manager = Mock(spec=OrderManager)
    manager.positions = {}
    return manager


@pytest.fixture
def mock_position_long():
    """Create mock LONG position."""
    return Position(
        symbol='AAPL',
        side='BUY',
        quantity=100,
        entry_price=150.00,
        entry_time=datetime.now(),
        stop_price=148.00,
        target_price=154.00,
        current_price=152.00,
        risk_amount=200.00,
        mae=0.0,
        mfe=200.0
    )


@pytest.fixture
def mock_position_short():
    """Create mock SHORT position."""
    return Position(
        symbol='TSLA',
        side='SELL',
        quantity=50,
        entry_price=200.00,
        entry_time=datetime.now(),
        stop_price=202.00,
        target_price=196.00,
        current_price=198.00,
        risk_amount=100.00,
        mae=0.0,
        mfe=100.0
    )


@pytest.fixture
def mock_historical_manager():
    """Mock historical manager returning sample OHLCV data."""
    mock = Mock()

    # Create sample OHLCV data for ATR calculation
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(149, 151, 100),
        'high': np.random.uniform(150, 152, 100),
        'low': np.random.uniform(148, 150, 100),
        'close': np.random.uniform(149, 151, 100),
        'volume': np.random.randint(100000, 200000, 100)
    })

    mock.load_symbol_data.return_value = df
    return mock


@pytest.fixture
def mock_indicator_engine():
    """Mock indicator engine with ATR calculation."""
    mock = Mock()

    def calculate_atr_mock(df):
        # Add ATR column with realistic values (around 2% of price)
        df['atr'] = np.full(len(df), 3.0)  # $3 ATR
        return df

    mock.calculate_atr.side_effect = calculate_atr_mock
    return mock


# ============================================================================
# Test Category 1: Configuration Tests (5 tests)
# ============================================================================

def test_enable_trailing_stop_percentage(fresh_trailing_manager):
    """Test enabling percentage-based trailing stop."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.5
    )

    assert 'AAPL' in fresh_trailing_manager.trailing_configs
    config = fresh_trailing_manager.trailing_configs['AAPL']
    assert config.symbol == 'AAPL'
    assert config.trailing_type == 'percentage'
    assert config.trailing_amount == 2.0
    assert config.activation_profit_pct == 1.5
    assert config.enabled is True
    assert config.activated is False


def test_enable_trailing_stop_atr(fresh_trailing_manager):
    """Test enabling ATR-based trailing stop."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='TSLA',
        trailing_type='atr',
        trailing_amount=3.0,
        activation_profit_pct=2.0
    )

    assert 'TSLA' in fresh_trailing_manager.trailing_configs
    config = fresh_trailing_manager.trailing_configs['TSLA']
    assert config.trailing_type == 'atr'
    assert config.trailing_amount == 3.0
    assert config.activation_profit_pct == 2.0


def test_disable_trailing_stop(fresh_trailing_manager):
    """Test disabling trailing stop."""
    fresh_trailing_manager.enable_trailing_stop('AAPL')
    assert 'AAPL' in fresh_trailing_manager.trailing_configs

    fresh_trailing_manager.disable_trailing_stop('AAPL')
    assert 'AAPL' not in fresh_trailing_manager.trailing_configs


def test_trailing_config_storage(fresh_trailing_manager):
    """Test that trailing configs are stored correctly."""
    symbols = ['AAPL', 'TSLA', 'MSFT']

    for symbol in symbols:
        fresh_trailing_manager.enable_trailing_stop(
            symbol=symbol,
            trailing_amount=2.0 + len(symbol)  # Different amounts
        )

    assert len(fresh_trailing_manager.trailing_configs) == 3
    assert all(s in fresh_trailing_manager.trailing_configs for s in symbols)


def test_multiple_symbols_config(fresh_trailing_manager):
    """Test configuring trailing stops for multiple symbols."""
    configs = [
        ('AAPL', 'percentage', 2.0, 1.5),
        ('TSLA', 'atr', 3.0, 2.0),
        ('MSFT', 'percentage', 1.5, 1.0)
    ]

    for symbol, t_type, amount, activation in configs:
        fresh_trailing_manager.enable_trailing_stop(
            symbol=symbol,
            trailing_type=t_type,
            trailing_amount=amount,
            activation_profit_pct=activation
        )

    assert len(fresh_trailing_manager.trailing_configs) == 3

    # Verify each config
    assert fresh_trailing_manager.trailing_configs['AAPL'].trailing_type == 'percentage'
    assert fresh_trailing_manager.trailing_configs['TSLA'].trailing_type == 'atr'
    assert fresh_trailing_manager.trailing_configs['MSFT'].trailing_amount == 1.5


# ============================================================================
# Test Category 2: Stop Calculation Tests (10 tests)
# ============================================================================

def test_calculate_new_stop_percentage_long(fresh_trailing_manager, mock_position_long):
    """Test stop calculation for LONG position with percentage trail."""
    # Enable trailing
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0  # Low threshold for testing
    )

    # Position at entry: 150, current: 152 (1.33% profit)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=152.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    # Should activate and calculate: 152 * (1 - 0.02) = 148.96
    assert new_stop is not None
    assert new_stop > 148.00  # Better than current stop
    assert new_stop < 152.00  # Below current price
    assert abs(new_stop - 148.96) < 0.01


def test_calculate_new_stop_percentage_short(fresh_trailing_manager, mock_position_short):
    """Test stop calculation for SHORT position with percentage trail."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='TSLA',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0
    )

    # Position entry: 200, current: 198 (1% profit for short)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='TSLA',
        current_price=198.00,
        position_side='SELL',
        entry_price=200.00,
        current_stop=202.00
    )

    # Should activate and calculate: 198 * (1 + 0.02) = 201.96
    assert new_stop is not None
    assert new_stop < 202.00  # Better than current stop (lower for short)
    assert new_stop > 198.00  # Above current price
    assert abs(new_stop - 201.96) < 0.01


def test_calculate_new_stop_atr_long(fresh_trailing_manager, mock_historical_manager, mock_indicator_engine):
    """Test stop calculation for LONG position with ATR trail."""
    # Patch the singleton objects in the already-loaded modules via sys.modules
    import sys
    from importlib import import_module

    # Ensure modules are imported to populate sys.modules
    import_module('src.data.historical_manager')
    import_module('src.indicators.indicator_engine')

    hm_module = sys.modules['src.data.historical_manager']
    ie_module = sys.modules['src.indicators.indicator_engine']

    original_hm = hm_module.historical_manager
    original_ie = ie_module.indicator_engine

    try:
        hm_module.historical_manager = mock_historical_manager
        ie_module.indicator_engine = mock_indicator_engine

        fresh_trailing_manager.enable_trailing_stop(
            symbol='AAPL',
            trailing_type='atr',
            trailing_amount=2.0,  # 2x ATR
            activation_profit_pct=1.0
        )

        # ATR = 3.0, price = 160, 2x ATR = 6.0, trail_pct = 6/160 = 3.75%
        # New stop = 160 * (1 - 0.0375) = 154.0 (higher than current 145.0)
        new_stop = fresh_trailing_manager._calculate_new_stop_price(
            symbol='AAPL',
            current_price=160.00,
            position_side='BUY',
            entry_price=150.00,
            current_stop=145.00
        )

        # Stop should move UP for LONG positions (profitable trail)
        assert new_stop is not None
        assert abs(new_stop - 154.0) < 0.1  # Approx 160 - 6 = 154
        assert new_stop > 145.00  # Better than current stop
    finally:
        # Restore original singletons
        hm_module.historical_manager = original_hm
        ie_module.indicator_engine = original_ie


def test_calculate_new_stop_atr_short(fresh_trailing_manager, mock_historical_manager, mock_indicator_engine):
    """Test stop calculation for SHORT position with ATR trail."""
    import sys
    from importlib import import_module

    # Ensure modules are imported to populate sys.modules
    import_module('src.data.historical_manager')
    import_module('src.indicators.indicator_engine')

    hm_module = sys.modules['src.data.historical_manager']
    ie_module = sys.modules['src.indicators.indicator_engine']

    original_hm = hm_module.historical_manager
    original_ie = ie_module.indicator_engine

    try:
        hm_module.historical_manager = mock_historical_manager
        ie_module.indicator_engine = mock_indicator_engine

        fresh_trailing_manager.enable_trailing_stop(
            symbol='TSLA',
            trailing_type='atr',
            trailing_amount=2.0,
            activation_profit_pct=1.0
        )

        # ATR = 3.0, price = 195, 2x ATR = 6.0, trail_pct = 6/195 = 3.08%
        # New stop = 195 * (1 + 0.0308) = 200.95 (lower than current 205.0)
        new_stop = fresh_trailing_manager._calculate_new_stop_price(
            symbol='TSLA',
            current_price=195.00,
            position_side='SELL',
            entry_price=200.00,
            current_stop=205.00
        )

        # Stop should move DOWN for SHORT positions (profitable trail)
        assert new_stop is not None
        assert new_stop < 205.00  # Better than current stop (lower for shorts)
        assert new_stop > 195.00  # Above current price for stop validity
    finally:
        # Restore original singletons
        hm_module.historical_manager = original_hm
        ie_module.indicator_engine = original_ie


def test_stop_not_adjusted_before_activation(fresh_trailing_manager):
    """Test that stop is not adjusted before activation threshold met."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=2.0  # Require 2% profit
    )

    # Only 1% profit (below threshold)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=151.50,  # 1% profit
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    assert new_stop is None  # Should not adjust yet


def test_stop_adjusted_after_activation(fresh_trailing_manager):
    """Test that stop is adjusted after activation threshold met."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0
    )

    # 2% profit (above 1% threshold)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=153.00,  # 2% profit
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    assert new_stop is not None
    assert new_stop > 148.00


def test_stop_only_moves_favorably_long(fresh_trailing_manager):
    """Test that stop only moves UP for LONG positions."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0
    )

    # First call activates at 152
    fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=152.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    # Price drops to 151 (trail would give lower stop)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=151.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.96  # Previous stop
    )

    # Should return None (don't lower stop)
    assert new_stop is None


def test_stop_only_moves_favorably_short(fresh_trailing_manager):
    """Test that stop only moves DOWN for SHORT positions."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='TSLA',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0
    )

    # First call activates at 198
    fresh_trailing_manager._calculate_new_stop_price(
        symbol='TSLA',
        current_price=198.00,
        position_side='SELL',
        entry_price=200.00,
        current_stop=202.00
    )

    # Price rises to 199 (trail would give higher stop)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='TSLA',
        current_price=199.00,
        position_side='SELL',
        entry_price=200.00,
        current_stop=201.96  # Previous stop
    )

    # Should return None (don't raise stop)
    assert new_stop is None


def test_minimum_trail_amount_respected(fresh_trailing_manager):
    """Test that minimum trail distance is respected."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=0.3,  # Very small trail
        activation_profit_pct=1.0,
        min_trail_amount=0.005  # 0.5% minimum
    )

    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=152.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    # Should use minimum 0.5% trail: 152 * 0.995 = 151.24
    assert new_stop is not None
    expected_stop = 152.00 * 0.995
    assert abs(new_stop - expected_stop) < 0.01


def test_no_adjustment_if_price_moved_against(fresh_trailing_manager):
    """Test no adjustment when price moves against position."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.0
    )

    # Activate at 152
    fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=152.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.00
    )

    config = fresh_trailing_manager.trailing_configs['AAPL']
    assert config.highest_price == 152.00

    # Price drops to 151 (moved against)
    new_stop = fresh_trailing_manager._calculate_new_stop_price(
        symbol='AAPL',
        current_price=151.00,
        position_side='BUY',
        entry_price=150.00,
        current_stop=148.96
    )

    # No adjustment (highest_price still 152)
    assert new_stop is None


# ============================================================================
# Test Category 3: Integration Tests (8 tests)
# ============================================================================

def test_check_and_update_stops_single_position(fresh_trailing_manager):
    """Test checking and updating single position."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        # Setup position
        position = Position(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            entry_price=150.00,
            entry_time=datetime.now(),
            stop_price=148.00,
            target_price=154.00,
            current_price=153.00,
            risk_amount=200.00
        )
        mock_om.positions = {'AAPL': position}

        # Enable trailing
        fresh_trailing_manager.enable_trailing_stop(
            symbol='AAPL',
            trailing_amount=2.0,
            activation_profit_pct=1.0
        )

        # Check and update
        adjustments = fresh_trailing_manager.check_and_update_stops()

        assert len(adjustments) == 1
        assert adjustments[0]['symbol'] == 'AAPL'
        assert adjustments[0]['new_stop'] > 148.00


def test_check_and_update_stops_multiple_positions(fresh_trailing_manager):
    """Test checking and updating multiple positions."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        # Setup positions
        positions = {
            'AAPL': Position(
                symbol='AAPL', side='BUY', quantity=100,
                entry_price=150.00, entry_time=datetime.now(),
                stop_price=148.00, current_price=153.00, risk_amount=200.00
            ),
            'TSLA': Position(
                symbol='TSLA', side='BUY', quantity=50,
                entry_price=200.00, entry_time=datetime.now(),
                stop_price=198.00, current_price=204.00, risk_amount=100.00
            )
        }
        mock_om.positions = positions

        # Enable trailing for both
        for symbol in ['AAPL', 'TSLA']:
            fresh_trailing_manager.enable_trailing_stop(
                symbol=symbol,
                activation_profit_pct=1.0
            )

        # Check and update
        adjustments = fresh_trailing_manager.check_and_update_stops()

        assert len(adjustments) == 2
        symbols = [adj['symbol'] for adj in adjustments]
        assert 'AAPL' in symbols
        assert 'TSLA' in symbols


def test_check_and_update_stops_no_positions(fresh_trailing_manager):
    """Test checking when no positions exist."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        mock_om.positions = {}

        adjustments = fresh_trailing_manager.check_and_update_stops()

        assert len(adjustments) == 0


def test_check_and_update_stops_mixed_long_short(fresh_trailing_manager):
    """Test checking mixed LONG and SHORT positions."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        positions = {
            'AAPL': Position(
                symbol='AAPL', side='BUY', quantity=100,
                entry_price=150.00, entry_time=datetime.now(),
                stop_price=148.00, current_price=153.00, risk_amount=200.00
            ),
            'TSLA': Position(
                symbol='TSLA', side='SELL', quantity=50,
                entry_price=200.00, entry_time=datetime.now(),
                stop_price=202.00, current_price=198.00, risk_amount=100.00
            )
        }
        mock_om.positions = positions

        # Enable trailing for both
        for symbol in ['AAPL', 'TSLA']:
            fresh_trailing_manager.enable_trailing_stop(
                symbol=symbol,
                activation_profit_pct=1.0
            )

        adjustments = fresh_trailing_manager.check_and_update_stops()

        # Both should adjust
        assert len(adjustments) == 2

        # AAPL (LONG): new stop should be higher
        aapl_adj = next(a for a in adjustments if a['symbol'] == 'AAPL')
        assert aapl_adj['new_stop'] > aapl_adj['old_stop']

        # TSLA (SHORT): new stop should be lower
        tsla_adj = next(a for a in adjustments if a['symbol'] == 'TSLA')
        assert tsla_adj['new_stop'] < tsla_adj['old_stop']


def test_order_manager_modify_stop():
    """Test OrderManager.modify_stop() method."""
    from src.execution.order_manager import order_manager

    # Create test position
    position = Position(
        symbol='TEST',
        side='BUY',
        quantity=100,
        entry_price=100.00,
        entry_time=datetime.now(),
        stop_price=98.00,
        current_price=102.00,
        risk_amount=200.00
    )

    order_manager.positions['TEST'] = position

    # Modify stop to higher value (valid for LONG)
    success = order_manager.modify_stop('TEST', 99.00)

    assert success is True
    assert order_manager.positions['TEST'].stop_price == 99.00

    # Try to modify stop to lower value (invalid for LONG)
    success = order_manager.modify_stop('TEST', 98.50)

    assert success is False
    assert order_manager.positions['TEST'].stop_price == 99.00  # Unchanged

    # Cleanup
    del order_manager.positions['TEST']


def test_order_manager_enable_trailing():
    """Test OrderManager.enable_trailing_stop_for_position() method."""
    from src.execution.order_manager import order_manager

    # Create test position
    position = Position(
        symbol='TEST',
        side='BUY',
        quantity=100,
        entry_price=100.00,
        entry_time=datetime.now(),
        stop_price=98.00,
        current_price=102.00,
        risk_amount=200.00
    )

    order_manager.positions['TEST'] = position

    # Enable trailing
    order_manager.enable_trailing_stop_for_position(
        symbol='TEST',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.5
    )

    # Verify config created
    assert 'TEST' in trailing_stop_manager.trailing_configs
    config = trailing_stop_manager.trailing_configs['TEST']
    assert config.trailing_amount == 2.0
    assert config.activation_profit_pct == 1.5

    # Cleanup
    del order_manager.positions['TEST']
    trailing_stop_manager.disable_trailing_stop('TEST')


def test_database_stop_update():
    """Test TradeDatabase.update_trade_stop() method."""
    from src.data.trade_database import trade_database

    # Record test trade
    trade_id = trade_database.record_trade_entry(
        symbol='TEST',
        side='BUY',
        entry_time=datetime.now(),
        entry_price=100.00,
        quantity=100,
        stop_price=98.00,
        target_price=104.00,
        risk_amount=200.00
    )

    # Update stop
    trade_database.update_trade_stop(trade_id, 99.00)

    # Verify update
    trade = trade_database.get_trade(trade_id)
    assert trade['stop_price'] == 99.00

    # Cleanup: close trade
    trade_database.record_trade_exit(
        trade_id=trade_id,
        exit_time=datetime.now(),
        exit_price=102.00,
        exit_reason='MANUAL'
    )


def test_realtime_price_triggers_adjustment(fresh_trailing_manager):
    """Test that real-time price updates trigger adjustments."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        # Setup position
        position = Position(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            entry_price=150.00,
            entry_time=datetime.now(),
            stop_price=148.00,
            target_price=154.00,
            current_price=152.00,
            risk_amount=200.00
        )
        mock_om.positions = {'AAPL': position}

        # Enable trailing
        fresh_trailing_manager.enable_trailing_stop(
            symbol='AAPL',
            activation_profit_pct=1.0
        )

        # First check - should activate
        adjustments1 = fresh_trailing_manager.check_and_update_stops()
        assert len(adjustments1) == 1

        # Price moves higher
        position.current_price = 154.00

        # Second check - should adjust again
        adjustments2 = fresh_trailing_manager.check_and_update_stops()
        assert len(adjustments2) == 1
        assert adjustments2[0]['new_stop'] > adjustments1[0]['new_stop']


# ============================================================================
# Test Category 4: ATR Tests (5 tests)
# ============================================================================

def test_get_atr_value(fresh_trailing_manager, mock_historical_manager, mock_indicator_engine):
    """Test ATR value retrieval."""
    with patch('src.data.historical_manager.historical_manager', mock_historical_manager), \
         patch('src.indicators.indicator_engine.indicator_engine', mock_indicator_engine):

        atr = fresh_trailing_manager._get_atr_value('AAPL')

        assert atr is not None
        assert atr == 3.0
        mock_historical_manager.load_symbol_data.assert_called_once()
        mock_indicator_engine.calculate_atr.assert_called_once()


def test_atr_trail_calculation(fresh_trailing_manager, mock_historical_manager, mock_indicator_engine):
    """Test ATR-based trail distance calculation."""
    import sys
    from importlib import import_module

    # Ensure modules are imported to populate sys.modules
    import_module('src.data.historical_manager')
    import_module('src.indicators.indicator_engine')

    hm_module = sys.modules['src.data.historical_manager']
    ie_module = sys.modules['src.indicators.indicator_engine']

    original_hm = hm_module.historical_manager
    original_ie = ie_module.indicator_engine

    try:
        hm_module.historical_manager = mock_historical_manager
        ie_module.indicator_engine = mock_indicator_engine

        fresh_trailing_manager.enable_trailing_stop(
            symbol='AAPL',
            trailing_type='atr',
            trailing_amount=2.0,
            activation_profit_pct=1.0
        )

        # ATR = 3.0, 2x ATR = 6.0, price = 160
        # Trail distance_pct = 6.0 / 160 = 3.75%
        # New stop = 160 * (1 - 0.0375) = 154.0
        new_stop = fresh_trailing_manager._calculate_new_stop_price(
            symbol='AAPL',
            current_price=160.00,
            position_side='BUY',
            entry_price=150.00,
            current_stop=145.00
        )

        # Verify ATR-based calculation
        assert new_stop is not None
        assert abs(new_stop - 154.0) < 0.1  # Approx 160 * (1 - 0.0375) = 154
    finally:
        # Restore original singletons
        hm_module.historical_manager = original_hm
        ie_module.indicator_engine = original_ie


def test_atr_multiplier_variations(fresh_trailing_manager, mock_historical_manager, mock_indicator_engine):
    """Test different ATR multiplier values."""
    import sys
    from importlib import import_module

    # Ensure modules are imported to populate sys.modules
    import_module('src.data.historical_manager')
    import_module('src.indicators.indicator_engine')

    hm_module = sys.modules['src.data.historical_manager']
    ie_module = sys.modules['src.indicators.indicator_engine']

    original_hm = hm_module.historical_manager
    original_ie = ie_module.indicator_engine

    try:
        hm_module.historical_manager = mock_historical_manager
        ie_module.indicator_engine = mock_indicator_engine

        # Test with different ATR multipliers at a price where trail is favorable
        # ATR = 3.0, price = 160, current_stop = 145
        multipliers = [1.0, 2.0, 3.0]
        # For price=160: trail_pct = (mult * 3.0) / 160
        # Expected stops: 160 * (1 - trail_pct) = 160 - (mult * 3.0)
        expected_stops = [157.0, 154.0, 151.0]  # 160 - (multiplier * 3.0)

        for mult, expected in zip(multipliers, expected_stops):
            fresh_trailing_manager.enable_trailing_stop(
                symbol=f'TEST{mult}',
                trailing_type='atr',
                trailing_amount=mult,
                activation_profit_pct=1.0
            )

            new_stop = fresh_trailing_manager._calculate_new_stop_price(
                symbol=f'TEST{mult}',
                current_price=160.00,
                position_side='BUY',
                entry_price=150.00,
                current_stop=145.00
            )

            assert new_stop is not None
            assert abs(new_stop - expected) < 0.1
    finally:
        # Restore original singletons
        hm_module.historical_manager = original_hm
        ie_module.indicator_engine = original_ie


def test_atr_fallback_to_percentage(fresh_trailing_manager):
    """Test fallback to percentage when ATR unavailable."""
    with patch('src.data.historical_manager.historical_manager') as mock_hm:
        # Return None (no data)
        mock_hm.get_bars.return_value = None

        fresh_trailing_manager.enable_trailing_stop(
            symbol='AAPL',
            trailing_type='atr',
            trailing_amount=2.0,
            activation_profit_pct=1.0
        )

        # Should fallback to 2% percentage trail
        new_stop = fresh_trailing_manager._calculate_new_stop_price(
            symbol='AAPL',
            current_price=152.00,
            position_side='BUY',
            entry_price=150.00,
            current_stop=148.00
        )

        # Should calculate as percentage: 152 * 0.98 = 148.96
        assert new_stop is not None
        assert abs(new_stop - 148.96) < 0.01


def test_atr_with_missing_data(fresh_trailing_manager):
    """Test ATR calculation with missing historical data."""
    with patch('src.data.historical_manager.historical_manager') as mock_hm:
        # Return empty DataFrame
        mock_hm.get_bars.return_value = pd.DataFrame()

        atr = fresh_trailing_manager._get_atr_value('AAPL')

        assert atr is None


# ============================================================================
# Test Category 5: Status and History Tests (4 tests)
# ============================================================================

def test_get_trailing_status_enabled(fresh_trailing_manager):
    """Test getting status for enabled trailing stop."""
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='percentage',
        trailing_amount=2.0,
        activation_profit_pct=1.5
    )

    status = fresh_trailing_manager.get_trailing_status('AAPL')

    assert status['enabled'] is True
    assert status['config']['trailing_type'] == 'percentage'
    assert status['config']['trailing_amount'] == 2.0
    assert status['config']['activation_profit_pct'] == 1.5
    assert status['activated'] is False
    assert status['adjustment_count'] == 0


def test_get_trailing_status_disabled(fresh_trailing_manager):
    """Test getting status for non-existent trailing stop."""
    status = fresh_trailing_manager.get_trailing_status('AAPL')

    assert status['enabled'] is False
    assert status['config'] is None
    assert status['activated'] is False


def test_get_adjustment_history(fresh_trailing_manager):
    """Test getting adjustment history."""
    # Create some adjustments
    adjustments = [
        StopAdjustment(
            symbol='AAPL',
            timestamp=datetime.now(),
            old_stop=148.00,
            new_stop=149.00,
            trigger_price=152.00,
            trailing_type='percentage',
            trailing_amount=2.0,
            profit_pct=2.0
        ),
        StopAdjustment(
            symbol='TSLA',
            timestamp=datetime.now(),
            old_stop=198.00,
            new_stop=197.00,
            trigger_price=195.00,
            trailing_type='atr',
            trailing_amount=3.0,
            profit_pct=2.5
        )
    ]

    fresh_trailing_manager.adjustment_history = adjustments

    # Get all history
    history = fresh_trailing_manager.get_adjustment_history()
    assert len(history) == 2

    # Filter by symbol
    history_aapl = fresh_trailing_manager.get_adjustment_history(symbol='AAPL')
    assert len(history_aapl) == 1
    assert history_aapl[0]['symbol'] == 'AAPL'


def test_adjustment_history_filtered(fresh_trailing_manager):
    """Test filtering adjustment history by date."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    adjustments = [
        StopAdjustment(
            symbol='AAPL',
            timestamp=two_days_ago,
            old_stop=148.00,
            new_stop=149.00,
            trigger_price=152.00,
            trailing_type='percentage',
            trailing_amount=2.0,
            profit_pct=2.0
        ),
        StopAdjustment(
            symbol='AAPL',
            timestamp=yesterday,
            old_stop=149.00,
            new_stop=150.00,
            trigger_price=153.00,
            trailing_type='percentage',
            trailing_amount=2.0,
            profit_pct=2.5
        ),
        StopAdjustment(
            symbol='AAPL',
            timestamp=now,
            old_stop=150.00,
            new_stop=151.00,
            trigger_price=154.00,
            trailing_type='percentage',
            trailing_amount=2.0,
            profit_pct=3.0
        )
    ]

    fresh_trailing_manager.adjustment_history = adjustments

    # Filter by date range
    history = fresh_trailing_manager.get_adjustment_history(
        symbol='AAPL',
        start_date=yesterday - timedelta(hours=1)
    )

    # Should get last 2 adjustments
    assert len(history) == 2


# ============================================================================
# Test Category 6: Edge Cases (3 tests)
# ============================================================================

def test_trailing_stop_disabled_symbol(fresh_trailing_manager):
    """Test behavior when trailing stop not enabled for symbol."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        position = Position(
            symbol='AAPL',
            side='BUY',
            quantity=100,
            entry_price=150.00,
            entry_time=datetime.now(),
            stop_price=148.00,
            current_price=153.00,
            risk_amount=200.00
        )
        mock_om.positions = {'AAPL': position}

        # DON'T enable trailing for AAPL

        adjustments = fresh_trailing_manager.check_and_update_stops()

        # Should return empty (no trailing enabled)
        assert len(adjustments) == 0


def test_position_closed_during_check(fresh_trailing_manager):
    """Test handling of position closed during check."""
    with patch('src.execution.order_manager.order_manager') as mock_om:
        mock_om.positions = {}  # No positions

        # But trailing config exists
        fresh_trailing_manager.enable_trailing_stop('AAPL')

        # Should disable trailing for non-existent position
        adjustments = fresh_trailing_manager.check_and_update_stops()

        assert len(adjustments) == 0
        assert 'AAPL' not in fresh_trailing_manager.trailing_configs


def test_invalid_trailing_config(fresh_trailing_manager):
    """Test handling of invalid trailing configurations."""
    # Invalid trailing type
    fresh_trailing_manager.enable_trailing_stop(
        symbol='AAPL',
        trailing_type='invalid',
        trailing_amount=2.0
    )

    # Should not create config
    assert 'AAPL' not in fresh_trailing_manager.trailing_configs

    # Invalid trailing amount (zero)
    fresh_trailing_manager.enable_trailing_stop(
        symbol='TSLA',
        trailing_type='percentage',
        trailing_amount=0.0
    )

    # Should not create config
    assert 'TSLA' not in fresh_trailing_manager.trailing_configs

    # Invalid trailing amount (negative)
    fresh_trailing_manager.enable_trailing_stop(
        symbol='MSFT',
        trailing_type='percentage',
        trailing_amount=-1.0
    )

    # Should not create config
    assert 'MSFT' not in fresh_trailing_manager.trailing_configs


# ============================================================================
# Test Summary
# ============================================================================
# Total Tests: 35
# - Configuration Tests: 5
# - Stop Calculation Tests: 10
# - Integration Tests: 8
# - ATR Tests: 5
# - Status and History Tests: 4
# - Edge Cases: 3
#
# Coverage Target: >80% (aiming for 95%+)
# ============================================================================
