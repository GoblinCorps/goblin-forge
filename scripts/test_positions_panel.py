#!/usr/bin/env python
"""
Manual Test Script for Positions Panel

Creates mock positions and displays the positions panel data to verify
formatting and styling work correctly.

Run:
----
python scripts/test_positions_panel.py
"""

from datetime import datetime
from src.execution.order_manager import order_manager, Position
from src.dashboard.components.positions import update_positions_callback


def create_mock_positions():
    """Create mock positions for testing."""
    # Clear any existing positions
    order_manager.positions.clear()
    order_manager.closed_trades.clear()

    # Create profitable position
    pos1 = Position(
        symbol='AAPL',
        side='BUY',
        quantity=100,
        entry_price=150.0,
        entry_time=datetime.now(),
        stop_price=148.0,
        target_price=160.0,
        current_price=155.0,
        last_update=datetime.now()
    )
    order_manager.positions['AAPL'] = pos1

    # Create losing position
    pos2 = Position(
        symbol='TSLA',
        side='BUY',
        quantity=50,
        entry_price=200.0,
        entry_time=datetime.now(),
        stop_price=192.0,
        target_price=210.0,
        current_price=195.0,
        last_update=datetime.now()
    )
    order_manager.positions['TSLA'] = pos2

    # Create another profitable position
    pos3 = Position(
        symbol='MSFT',
        side='BUY',
        quantity=75,
        entry_price=300.0,
        entry_time=datetime.now(),
        stop_price=295.0,
        target_price=315.0,
        current_price=305.0,
        last_update=datetime.now()
    )
    order_manager.positions['MSFT'] = pos3

    print("✓ Created 3 mock positions (2 profitable, 1 losing)")


def test_positions_panel():
    """Test positions panel callback."""
    print("\n" + "="*60)
    print("TESTING POSITIONS PANEL CALLBACK")
    print("="*60)

    # Create mock positions
    create_mock_positions()

    # Call update callback
    result = update_positions_callback(0)

    # Unpack results
    table_data, total_pnl, total_pnl_class, unrealized, unrealized_class, \
        pos_count, winning, losing = result

    # Display results
    print("\nPORTFOLIO SUMMARY:")
    print(f"  Total P&L: {total_pnl} (class: {total_pnl_class})")
    print(f"  Unrealized P&L: {unrealized} (class: {unrealized_class})")
    print(f"  Open Positions: {pos_count}")
    print(f"  Winning: {winning}")
    print(f"  Losing: {losing}")

    print("\nPOSITIONS TABLE DATA:")
    print(f"  Rows: {len(table_data)}")

    for i, row in enumerate(table_data, 1):
        print(f"\n  Position {i}:")
        print(f"    Symbol: {row['symbol']}")
        print(f"    Side: {row['side']}")
        print(f"    Quantity: {row['quantity']}")
        print(f"    Entry: ${row['entry_price']:.2f}")
        print(f"    Current: ${row['current_price']:.2f}")
        print(f"    Stop: ${row['stop_price']:.2f}")
        print(f"    Target: ${row['target_price']:.2f}")
        print(f"    P&L $: ${row['unrealized_pnl']:+,.2f}")
        print(f"    P&L %: {row['unrealized_pnl_pct']:+.2f}%")
        print(f"    Risk $: ${row['current_risk']:,.2f}")

    # Verify calculations
    print("\nVERIFICATION:")
    expected_total_pnl = 500.0 - 250.0 + 375.0  # AAPL - TSLA + MSFT
    print(f"  Expected total P&L: ${expected_total_pnl:+,.2f}")
    print(f"  Actual total P&L: {total_pnl}")

    if "$625" in total_pnl or "$625.00" in total_pnl:
        print("  ✓ P&L calculation correct!")
    else:
        print("  ✗ P&L calculation mismatch!")

    if "text-success" in total_pnl_class:
        print("  ✓ Positive P&L class correct (text-success)")
    else:
        print("  ✗ P&L class incorrect")

    if pos_count == "3" and winning == "2" and losing == "1":
        print("  ✓ Position counts correct!")
    else:
        print("  ✗ Position counts incorrect")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


def test_empty_positions():
    """Test with no positions."""
    print("\n" + "="*60)
    print("TESTING EMPTY POSITIONS")
    print("="*60)

    # Clear positions
    order_manager.positions.clear()
    order_manager.closed_trades.clear()

    # Call callback
    result = update_positions_callback(0)

    table_data, total_pnl, _, unrealized, _, pos_count, winning, losing = result

    print(f"  Table rows: {len(table_data)}")
    print(f"  Total P&L: {total_pnl}")
    print(f"  Unrealized P&L: {unrealized}")
    print(f"  Open positions: {pos_count}")
    print(f"  Winning: {winning}")
    print(f"  Losing: {losing}")

    if len(table_data) == 0 and pos_count == "0":
        print("  ✓ Empty positions handled correctly!")
    else:
        print("  ✗ Empty positions not handled correctly")

    print("="*60)


if __name__ == '__main__':
    test_positions_panel()
    test_empty_positions()
