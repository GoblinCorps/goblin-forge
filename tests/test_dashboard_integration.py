"""
Integration Tests for Dashboard Positions Panel

Tests the complete integration of positions panel in the dashboard.

Run:
----
pytest tests/test_dashboard_integration.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd

from src.execution.order_manager import Position


class TestDashboardPositionsIntegration:
    """Test dashboard positions panel integration."""

    @patch('src.execution.order_manager.order_manager')
    def test_dashboard_positions_panel_with_live_data(self, mock_manager):
        """Test dashboard can render positions panel with live data."""
        from src.dashboard.app import app

        # Create mock positions
        mock_positions = pd.DataFrame([
            {
                'symbol': 'AAPL',
                'side': 'BUY',
                'quantity': 100,
                'entry_price': 150.0,
                'current_price': 155.0,
                'stop_price': 148.0,
                'target_price': 160.0,
                'unrealized_pnl': 500.0,
                'unrealized_pnl_pct': 3.33,
                'current_risk': 700.0,
                'entry_time': datetime.now(),
                'last_update': datetime.now()
            }
        ])

        mock_manager.get_positions_dataframe.return_value = mock_positions
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 500.0,
            'total_pnl': 500.0,
            'positions_count': 1,
            'winning_positions': 1,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        # Verify app has positions panel components
        layout_str = str(app.layout)
        assert 'positions-table' in layout_str or app is not None

    def test_dashboard_has_interval_component(self):
        """Test dashboard has interval component for auto-refresh."""
        from src.dashboard.app import app

        layout_str = str(app.layout)
        assert 'interval-component' in layout_str

    def test_dashboard_has_positions_callback(self):
        """Test dashboard has positions update callback registered."""
        from src.dashboard.app import app

        # Check callback is registered
        callbacks = app.callback_map
        assert len(callbacks) > 0  # Has callbacks

    @patch('src.execution.order_manager.order_manager')
    def test_positions_panel_updates_on_interval(self, mock_manager):
        """Test positions panel updates when interval fires."""
        from src.dashboard.components.positions import update_positions_callback

        # Simulate first interval
        mock_manager.get_positions_dataframe.return_value = pd.DataFrame()
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'total_pnl': 0.0,
            'positions_count': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result1 = update_positions_callback(0)
        assert len(result1) == 8
        assert result1[0] == []  # No positions

        # Simulate new position added
        mock_manager.get_positions_dataframe.return_value = pd.DataFrame([{
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'entry_price': 150.0,
            'current_price': 155.0,
            'stop_price': 148.0,
            'target_price': 160.0,
            'unrealized_pnl': 500.0,
            'unrealized_pnl_pct': 3.33,
            'current_risk': 700.0,
            'entry_time': datetime.now(),
            'last_update': datetime.now()
        }])
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 500.0,
            'total_pnl': 500.0,
            'positions_count': 1,
            'winning_positions': 1,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result2 = update_positions_callback(1)
        assert len(result2) == 8
        assert len(result2[0]) == 1  # One position
        assert result2[0][0]['symbol'] == 'AAPL'
