"""
Tests for Dashboard Positions Panel Component

Tests the positions panel UI components and data update callback.

Coverage Requirements:
- Component creation (table, summary, panel)
- Callback functionality with various position scenarios
- Error handling
- Data formatting and styling
- Empty positions handling
- Target: >85% coverage

Run:
----
pytest tests/test_dashboard_positions.py -v --cov=src.dashboard.components.positions
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from dash import dash_table
import dash_bootstrap_components as dbc

from src.dashboard.components.positions import (
    create_positions_table,
    create_portfolio_summary_card,
    create_positions_panel,
    update_positions_callback
)
from src.execution.order_manager import Position


class TestPositionsTableCreation:
    """Test positions table component creation."""

    def test_create_positions_table(self):
        """Test positions table is created with correct structure."""
        table = create_positions_table()

        assert table is not None
        assert isinstance(table, dash_table.DataTable)
        assert table.id == 'positions-table'

    def test_positions_table_has_all_columns(self):
        """Test table has all required columns."""
        table = create_positions_table()

        column_ids = [col['id'] for col in table.columns]
        expected_columns = [
            'symbol', 'side', 'quantity', 'entry_price', 'current_price',
            'stop_price', 'target_price', 'unrealized_pnl',
            'unrealized_pnl_pct', 'current_risk'
        ]

        assert len(column_ids) == 10
        for col in expected_columns:
            assert col in column_ids

    def test_positions_table_has_conditional_styling(self):
        """Test table has conditional styling for profit/loss."""
        table = create_positions_table()

        # Should have style_data_conditional
        assert hasattr(table, 'style_data_conditional')
        assert len(table.style_data_conditional) > 0

        # Check for profit/loss styling
        styles = table.style_data_conditional
        assert any('unrealized_pnl' in str(s) for s in styles)

    def test_positions_table_numeric_formatting(self):
        """Test table has numeric formatting for price/P&L columns."""
        table = create_positions_table()

        # Check columns have type and format
        numeric_cols = [
            'quantity', 'entry_price', 'current_price', 'stop_price',
            'target_price', 'unrealized_pnl', 'unrealized_pnl_pct', 'current_risk'
        ]

        for col in table.columns:
            if col['id'] in numeric_cols:
                assert col.get('type') == 'numeric'
                # Price columns should have format
                if 'price' in col['id'] or 'pnl' in col['id'] or 'risk' in col['id']:
                    assert 'format' in col

    def test_positions_table_sortable_filterable(self):
        """Test table is sortable and filterable."""
        table = create_positions_table()

        assert table.sort_action == 'native'
        assert table.filter_action == 'native'

    def test_positions_table_page_size(self):
        """Test table has reasonable page size."""
        table = create_positions_table()

        assert table.page_size == 10


class TestPortfolioSummaryCard:
    """Test portfolio summary card component."""

    def test_create_portfolio_summary_card(self):
        """Test summary card is created."""
        card = create_portfolio_summary_card()

        assert card is not None
        assert isinstance(card, dbc.Card)

    def test_summary_card_has_header(self):
        """Test card has header."""
        card = create_portfolio_summary_card()

        # Card should have CardHeader
        assert len(card.children) > 0
        assert isinstance(card.children[0], dbc.CardHeader)

    def test_summary_card_has_metrics(self):
        """Test card has all metric components with correct IDs."""
        card = create_portfolio_summary_card()

        # Convert card to string to check for IDs
        card_str = str(card)

        # Check for component IDs
        assert 'total-pnl' in card_str
        assert 'unrealized-pnl' in card_str
        assert 'positions-count' in card_str
        assert 'winning-positions' in card_str
        assert 'losing-positions' in card_str


class TestPositionsPanel:
    """Test complete positions panel."""

    def test_create_positions_panel(self):
        """Test panel is created with all components."""
        panel = create_positions_panel()

        assert panel is not None
        assert isinstance(panel, dbc.Card)

    def test_panel_has_header(self):
        """Test panel has header."""
        panel = create_positions_panel()

        assert len(panel.children) > 0
        assert isinstance(panel.children[0], dbc.CardHeader)

    def test_panel_has_body(self):
        """Test panel has body with components."""
        panel = create_positions_panel()

        # Should have CardBody
        assert len(panel.children) > 1
        assert isinstance(panel.children[1], dbc.CardBody)

    def test_panel_has_margin_class(self):
        """Test panel has margin bottom class."""
        panel = create_positions_panel()

        assert 'mb-4' in panel.className


class TestUpdatePositionsCallback:
    """Test positions update callback functionality."""

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_with_no_positions(self, mock_manager):
        """Test callback with no open positions."""
        # Mock empty positions
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

        result = update_positions_callback(0)

        assert len(result) == 8
        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        assert table_data == []
        assert total_pnl == "$+0.00"
        assert unrealized == "$+0.00"
        assert pos_count == "0"
        assert winning == "0"
        assert losing == "0"

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_with_profitable_position(self, mock_manager):
        """Test callback with profitable position."""
        # Create mock position DataFrame
        df = pd.DataFrame([{
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

        mock_manager.get_positions_dataframe.return_value = df
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

        result = update_positions_callback(0)

        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        # Check table data
        assert len(table_data) == 1
        assert table_data[0]['symbol'] == 'AAPL'
        assert table_data[0]['unrealized_pnl'] == 500.0

        # Check P&L formatting
        assert "$" in total_pnl
        assert "500" in total_pnl
        assert "text-success" in total_pnl_class

        # Check counts
        assert pos_count == "1"
        assert winning == "1"
        assert losing == "0"

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_with_losing_position(self, mock_manager):
        """Test callback with losing position."""
        # Create mock position DataFrame
        df = pd.DataFrame([{
            'symbol': 'TSLA',
            'side': 'BUY',
            'quantity': 50,
            'entry_price': 200.0,
            'current_price': 195.0,
            'stop_price': 192.0,
            'target_price': 210.0,
            'unrealized_pnl': -250.0,
            'unrealized_pnl_pct': -2.5,
            'current_risk': 150.0,
            'entry_time': datetime.now(),
            'last_update': datetime.now()
        }])

        mock_manager.get_positions_dataframe.return_value = df
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': -250.0,
            'total_pnl': -250.0,
            'positions_count': 1,
            'winning_positions': 0,
            'losing_positions': 1,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        # Check table data
        assert len(table_data) == 1
        assert table_data[0]['unrealized_pnl'] == -250.0

        # Check P&L formatting with negative
        assert "$" in total_pnl
        assert "250" in total_pnl
        assert "text-danger" in total_pnl_class

        # Check counts
        assert pos_count == "1"
        assert winning == "0"
        assert losing == "1"

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_with_multiple_positions(self, mock_manager):
        """Test callback with multiple positions (mixed P&L)."""
        # Create mock positions DataFrame
        df = pd.DataFrame([
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
            },
            {
                'symbol': 'TSLA',
                'side': 'BUY',
                'quantity': 50,
                'entry_price': 200.0,
                'current_price': 195.0,
                'stop_price': 192.0,
                'target_price': 210.0,
                'unrealized_pnl': -250.0,
                'unrealized_pnl_pct': -2.5,
                'current_risk': 150.0,
                'entry_time': datetime.now(),
                'last_update': datetime.now()
            },
            {
                'symbol': 'MSFT',
                'side': 'BUY',
                'quantity': 75,
                'entry_price': 300.0,
                'current_price': 305.0,
                'stop_price': 295.0,
                'target_price': 315.0,
                'unrealized_pnl': 375.0,
                'unrealized_pnl_pct': 1.67,
                'current_risk': 750.0,
                'entry_time': datetime.now(),
                'last_update': datetime.now()
            }
        ])

        mock_manager.get_positions_dataframe.return_value = df
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 625.0,  # 500 - 250 + 375
            'total_pnl': 625.0,
            'positions_count': 3,
            'winning_positions': 2,
            'losing_positions': 1,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        # Check table data
        assert len(table_data) == 3
        assert table_data[0]['symbol'] == 'AAPL'
        assert table_data[1]['symbol'] == 'TSLA'
        assert table_data[2]['symbol'] == 'MSFT'

        # Check portfolio P&L
        assert "625" in total_pnl
        assert "text-success" in total_pnl_class

        # Check counts
        assert pos_count == "3"
        assert winning == "2"
        assert losing == "1"

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_with_realized_and_unrealized_pnl(self, mock_manager):
        """Test callback with both realized and unrealized P&L."""
        df = pd.DataFrame([{
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

        mock_manager.get_positions_dataframe.return_value = df
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 1000.0,  # From closed trades
            'unrealized_pnl': 500.0,  # From open positions
            'total_pnl': 1500.0,
            'positions_count': 1,
            'winning_positions': 1,
            'losing_positions': 0,
            'closed_trades_count': 2,
            'winning_trades': 2,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        # Total P&L should be 1500
        assert "1,500" in total_pnl or "1500" in total_pnl
        # Unrealized should be 500
        assert "500" in unrealized

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_pnl_formatting_positive(self, mock_manager):
        """Test P&L formatting with positive values."""
        mock_manager.get_positions_dataframe.return_value = pd.DataFrame()
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 1234.56,
            'total_pnl': 1234.56,
            'positions_count': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        _, total_pnl, total_pnl_class, unrealized, unrealized_class, _, _, _ = result

        # Check formatting
        assert "$" in total_pnl
        assert "1,234.56" in total_pnl or "1234.56" in total_pnl
        assert "+" in total_pnl  # Plus sign for positive
        assert "text-success" in total_pnl_class

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_pnl_formatting_negative(self, mock_manager):
        """Test P&L formatting with negative values."""
        mock_manager.get_positions_dataframe.return_value = pd.DataFrame()
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': -1234.56,
            'total_pnl': -1234.56,
            'positions_count': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        _, total_pnl, total_pnl_class, unrealized, unrealized_class, _, _, _ = result

        # Check formatting
        assert "$" in total_pnl
        assert "1,234.56" in total_pnl or "1234.56" in total_pnl
        assert "-" in total_pnl  # Minus sign for negative
        assert "text-danger" in total_pnl_class

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_pnl_formatting_zero(self, mock_manager):
        """Test P&L formatting with zero values."""
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

        result = update_positions_callback(0)

        _, total_pnl, total_pnl_class, unrealized, unrealized_class, _, _, _ = result

        # Check formatting
        assert "$" in total_pnl
        assert "0.00" in total_pnl
        assert "text-success" in total_pnl_class  # Zero is >= 0, so success class

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_error_handling(self, mock_manager):
        """Test callback handles errors gracefully."""
        # Make get_positions_dataframe raise an error
        mock_manager.get_positions_dataframe.side_effect = Exception("Database error")

        result = update_positions_callback(0)

        # Should return safe defaults
        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        assert table_data == []
        assert total_pnl == "$0.00"
        assert pos_count == "0"
        assert winning == "0"
        assert losing == "0"

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_none_dataframe(self, mock_manager):
        """Test callback with None DataFrame."""
        mock_manager.get_positions_dataframe.return_value = None
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

        result = update_positions_callback(0)

        table_data, _, _, _, _, _, _, _ = result

        # Should handle None gracefully
        assert table_data == []

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_large_pnl_values(self, mock_manager):
        """Test formatting with large P&L values."""
        mock_manager.get_positions_dataframe.return_value = pd.DataFrame()
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 123456.78,
            'total_pnl': 123456.78,
            'positions_count': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        _, total_pnl, _, _, _, _, _, _ = result

        # Should have comma separators for thousands
        assert "$" in total_pnl
        assert "123,456.78" in total_pnl or "123456.78" in total_pnl

    @patch('src.execution.order_manager.order_manager')
    def test_update_positions_short_position(self, mock_manager):
        """Test callback with short position."""
        df = pd.DataFrame([{
            'symbol': 'TSLA',
            'side': 'SELL',  # Short position
            'quantity': 50,
            'entry_price': 200.0,
            'current_price': 195.0,  # Price down = profit for short
            'stop_price': 205.0,
            'target_price': 185.0,
            'unrealized_pnl': 250.0,  # Profit on short
            'unrealized_pnl_pct': 2.5,
            'current_risk': -500.0,
            'entry_time': datetime.now(),
            'last_update': datetime.now()
        }])

        mock_manager.get_positions_dataframe.return_value = df
        mock_manager.get_portfolio_pnl.return_value = {
            'realized_pnl': 0.0,
            'unrealized_pnl': 250.0,
            'total_pnl': 250.0,
            'positions_count': 1,
            'winning_positions': 1,
            'losing_positions': 0,
            'closed_trades_count': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        result = update_positions_callback(0)

        table_data, _, total_pnl_class, _, _, _, winning, _ = result

        # Check short position
        assert len(table_data) == 1
        assert table_data[0]['side'] == 'SELL'
        assert table_data[0]['unrealized_pnl'] == 250.0

        # Should be winning
        assert winning == "1"
        assert "text-success" in total_pnl_class


class TestCallbackIntegration:
    """Test callback integration scenarios."""

    @patch('src.execution.order_manager.order_manager')
    def test_callback_return_types(self, mock_manager):
        """Test callback returns correct types."""
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

        result = update_positions_callback(0)

        # Should return tuple of 8 elements
        assert isinstance(result, tuple)
        assert len(result) == 8

        table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
            pos_count, winning, losing = result

        # Check types
        assert isinstance(table_data, list)
        assert isinstance(total_pnl, str)
        assert isinstance(total_pnl_class, str)
        assert isinstance(unrealized, str)
        assert isinstance(unrealized_class, str)
        assert isinstance(pos_count, str)
        assert isinstance(winning, str)
        assert isinstance(losing, str)

    @patch('src.execution.order_manager.order_manager')
    def test_callback_with_multiple_intervals(self, mock_manager):
        """Test callback works with multiple interval calls."""
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

        # Simulate multiple interval updates
        for n in range(10):
            result = update_positions_callback(n)
            assert len(result) == 8
            assert result is not None
