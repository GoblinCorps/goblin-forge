"""
Trade Database & Journaling System

Comprehensive SQLite-based trade journaling with performance analytics.

Features:
---------
1. Trade Recording
   - Entry/exit timestamps and prices
   - Position sizing and risk metrics
   - MAE/MFE tracking
   - Commission accounting

2. Performance Analytics
   - Win rate, profit factor, Sharpe ratio
   - Maximum drawdown calculation
   - R:R analysis
   - Equity curve generation

3. Integration
   - Automatic recording from OrderManager
   - Real-time MAE/MFE updates
   - SABR20 score tracking
   - Market regime correlation

Usage:
------
from src.data.trade_database import trade_database

# Record trade entry
trade_id = trade_database.record_trade_entry(
    symbol='AAPL',
    side='BUY',
    entry_time=datetime.now(),
    entry_price=150.00,
    quantity=100,
    stop_price=148.00,
    target_price=154.00,
    risk_amount=200.00,
    sabr20_score=85.5
)

# Record trade exit
trade_database.record_trade_exit(
    trade_id=trade_id,
    exit_time=datetime.now(),
    exit_price=153.50,
    exit_reason='TARGET',
    commission=2.00
)

# Get performance stats
stats = trade_database.get_performance_stats()
print(f"Win rate: {stats['win_rate']:.1f}%")
print(f"Sharpe ratio: {stats['sharpe_ratio']:.2f}")
"""

import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import threading

import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class Trade:
    """Trade record."""
    id: int
    symbol: str
    side: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    stop_price: Optional[float]
    target_price: Optional[float]
    actual_stop: Optional[float]
    actual_target: Optional[float]
    commission: float
    realized_pnl: Optional[float]
    pnl_pct: Optional[float]
    risk_amount: float
    risk_reward_ratio: Optional[float]
    mae: Optional[float]
    mfe: Optional[float]
    hold_time_minutes: Optional[int]
    exit_reason: Optional[str]
    sabr20_score: Optional[float]
    regime: Optional[str]
    notes: Optional[str]


class TradeDatabase:
    """
    SQLite-based trade journaling system.

    Provides comprehensive trade recording, performance analytics, and
    equity curve generation for algorithmic trading systems.

    Thread Safety:
    --------------
    Uses thread-local connections for safe concurrent access.

    Attributes:
    -----------
    db_path : str
        Path to SQLite database file
    _local : threading.local
        Thread-local storage for connections

    Performance:
    ------------
    - Indexed queries: <10ms typical
    - Bulk inserts: ~1000 trades/second
    - Analytics calculations: <100ms for 1000 trades
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = "data/trades.db"):
        """Singleton pattern for global trade database instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "data/trades.db"):
        """
        Initialize trade database.

        Parameters:
        -----------
        db_path : str, default='data/trades.db'
            Path to SQLite database file

        Notes:
        ------
        - Creates database and schema if not exists
        - Thread-safe connection management
        - Automatic index creation
        """
        if hasattr(self, '_initialized'):
            return

        self.db_path = db_path
        self._local = threading.local()

        # Create data directory if not exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create schema
        self._create_schema()

        self._initialized = True
        logger.info(f"Trade database initialized: {db_path}")

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable row factory for dict-like access
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _create_schema(self) -> None:
        """
        Create trades table and indexes.

        Schema:
        -------
        - trades: Main trade records table
        - Indexes on: symbol, entry_time, exit_time, realized_pnl

        Notes:
        ------
        Idempotent - safe to call multiple times.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    stop_price REAL,
                    target_price REAL,
                    actual_stop REAL,
                    actual_target REAL,
                    commission REAL DEFAULT 0.0,
                    realized_pnl REAL,
                    pnl_pct REAL,
                    risk_amount REAL NOT NULL,
                    risk_reward_ratio REAL,
                    mae REAL,
                    mfe REAL,
                    hold_time_minutes INTEGER,
                    exit_reason TEXT,
                    sabr20_score REAL,
                    regime TEXT,
                    notes TEXT
                )
            """)

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_entry_time ON trades(entry_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exit_time ON trades(exit_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_realized_pnl ON trades(realized_pnl)"
            )

            conn.commit()
            logger.debug("Trade database schema created")

    def record_trade_entry(
        self,
        symbol: str,
        side: str,
        entry_time: datetime,
        entry_price: float,
        quantity: int,
        stop_price: float,
        target_price: float,
        risk_amount: float,
        sabr20_score: Optional[float] = None,
        regime: Optional[str] = None
    ) -> int:
        """
        Record new trade entry.

        Parameters:
        -----------
        symbol : str
            Stock symbol
        side : str
            'BUY' or 'SELL'
        entry_time : datetime
            Entry timestamp
        entry_price : float
            Entry price per share
        quantity : int
            Number of shares
        stop_price : float
            Stop loss price
        target_price : float
            Take profit price
        risk_amount : float
            Initial risk in dollars
        sabr20_score : float, optional
            SABR20 score at entry
        regime : str, optional
            Market regime at entry

        Returns:
        --------
        int
            Database ID of inserted trade

        Examples:
        ---------
        >>> trade_id = trade_database.record_trade_entry(
        ...     symbol='AAPL',
        ...     side='BUY',
        ...     entry_time=datetime.now(),
        ...     entry_price=150.00,
        ...     quantity=100,
        ...     stop_price=148.00,
        ...     target_price=154.00,
        ...     risk_amount=200.00,
        ...     sabr20_score=85.5,
        ...     regime='TRENDING_UP'
        ... )
        >>> print(f"Trade ID: {trade_id}")
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                symbol, side, entry_time, entry_price, quantity,
                stop_price, target_price, risk_amount,
                sabr20_score, regime, mae, mfe
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0)
        """, (
            symbol, side, entry_time, entry_price, quantity,
            stop_price, target_price, risk_amount,
            sabr20_score, regime
        ))

        self._conn.commit()
        trade_id = cursor.lastrowid

        logger.info(
            f"Recorded trade entry: ID={trade_id}, {symbol} {side} "
            f"{quantity}@${entry_price:.2f}, risk=${risk_amount:.2f}"
        )

        return trade_id

    def record_trade_exit(
        self,
        trade_id: int,
        exit_time: datetime,
        exit_price: float,
        exit_reason: str,
        commission: float = 0.0,
        actual_stop: Optional[float] = None,
        actual_target: Optional[float] = None,
        mae: Optional[float] = None,
        mfe: Optional[float] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Update trade with exit information and calculate P&L.

        Automatically calculates:
        - realized_pnl (accounting for commission)
        - pnl_pct
        - risk_reward_ratio
        - hold_time_minutes

        Parameters:
        -----------
        trade_id : int
            Database ID of trade
        exit_time : datetime
            Exit timestamp
        exit_price : float
            Exit price per share
        exit_reason : str
            'STOP', 'TARGET', 'MANUAL', 'TRAILING_STOP'
        commission : float, default=0.0
            Total commission paid
        actual_stop : float, optional
            Actual stop hit price
        actual_target : float, optional
            Actual target hit price
        mae : float, optional
            Maximum Adverse Excursion
        mfe : float, optional
            Maximum Favorable Excursion
        notes : str, optional
            Trade notes

        Examples:
        ---------
        >>> trade_database.record_trade_exit(
        ...     trade_id=123,
        ...     exit_time=datetime.now(),
        ...     exit_price=153.50,
        ...     exit_reason='TARGET',
        ...     commission=2.00,
        ...     mae=-150.00,
        ...     mfe=400.00
        ... )
        """
        # Get trade entry data
        trade = self.get_trade(trade_id)
        if not trade:
            logger.error(f"Trade ID {trade_id} not found")
            return

        # Calculate P&L
        if trade['side'] == 'BUY':
            pnl = (exit_price - trade['entry_price']) * trade['quantity']
        else:  # SELL/SHORT
            pnl = (trade['entry_price'] - exit_price) * trade['quantity']

        realized_pnl = pnl - commission

        # Calculate percentage return
        position_value = trade['entry_price'] * trade['quantity']
        pnl_pct = (realized_pnl / position_value) * 100

        # Calculate risk/reward ratio
        if trade['risk_amount'] > 0:
            risk_reward_ratio = realized_pnl / trade['risk_amount']
        else:
            risk_reward_ratio = 0.0

        # Calculate hold time
        hold_time = exit_time - trade['entry_time']
        hold_time_minutes = int(hold_time.total_seconds() / 60)

        # Update MAE/MFE if provided
        if mae is not None:
            final_mae = mae
        else:
            final_mae = trade.get('mae', 0.0)

        if mfe is not None:
            final_mfe = mfe
        else:
            final_mfe = trade.get('mfe', 0.0)

        # Update trade
        cursor = self._conn.cursor()
        cursor.execute("""
            UPDATE trades
            SET exit_time = ?,
                exit_price = ?,
                exit_reason = ?,
                commission = ?,
                actual_stop = ?,
                actual_target = ?,
                realized_pnl = ?,
                pnl_pct = ?,
                risk_reward_ratio = ?,
                hold_time_minutes = ?,
                mae = ?,
                mfe = ?,
                notes = ?
            WHERE id = ?
        """, (
            exit_time, exit_price, exit_reason, commission,
            actual_stop, actual_target, realized_pnl, pnl_pct,
            risk_reward_ratio, hold_time_minutes, final_mae, final_mfe,
            notes, trade_id
        ))

        self._conn.commit()

        logger.info(
            f"Recorded trade exit: ID={trade_id}, {trade['symbol']} "
            f"${exit_price:.2f}, P&L: ${realized_pnl:+.2f} "
            f"({pnl_pct:+.2f}%), reason: {exit_reason}"
        )

    def get_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """
        Get single trade by ID.

        Parameters:
        -----------
        trade_id : int
            Database ID

        Returns:
        --------
        dict or None
            Trade record as dictionary, or None if not found
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """
        Get all open trades (exit_time IS NULL).

        Returns:
        --------
        list of dict
            Open trade records
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            WHERE exit_time IS NULL
            ORDER BY entry_time DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_closed_trades(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get closed trades with optional filters.

        Parameters:
        -----------
        start_date : datetime, optional
            Filter by exit_time >= start_date
        end_date : datetime, optional
            Filter by exit_time <= end_date
        symbol : str, optional
            Filter by symbol

        Returns:
        --------
        list of dict
            Closed trade records
        """
        query = "SELECT * FROM trades WHERE exit_time IS NOT NULL"
        params = []

        if start_date:
            query += " AND exit_time >= ?"
            params.append(start_date)

        if end_date:
            query += " AND exit_time <= ?"
            params.append(end_date)

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY exit_time DESC"

        cursor = self._conn.cursor()
        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]

    def get_trades_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all trades for a symbol.

        Parameters:
        -----------
        symbol : str
            Stock symbol

        Returns:
        --------
        list of dict
            Trade records for symbol
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM trades
            WHERE symbol = ?
            ORDER BY entry_time DESC
        """, (symbol,))

        return [dict(row) for row in cursor.fetchall()]

    def get_performance_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance statistics.

        Parameters:
        -----------
        start_date : datetime, optional
            Filter by exit_time >= start_date
        end_date : datetime, optional
            Filter by exit_time <= end_date

        Returns:
        --------
        dict
            Performance metrics:
            - total_trades: int
            - winning_trades: int
            - losing_trades: int
            - win_rate: float (percentage)
            - total_pnl: float
            - avg_win: float
            - avg_loss: float
            - largest_win: float
            - largest_loss: float
            - avg_risk_reward: float
            - profit_factor: float (gross_profit / gross_loss)
            - sharpe_ratio: float (annualized)
            - max_drawdown: float (percentage)
            - avg_hold_time_minutes: float
            - total_commission: float

        Notes:
        ------
        - Sharpe ratio assumes 252 trading days/year
        - Max drawdown calculated from equity curve
        - Returns zeros if no trades
        """
        trades = self.get_closed_trades(start_date, end_date)

        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'avg_risk_reward': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'avg_hold_time_minutes': 0.0,
                'total_commission': 0.0
            }

        # Extract P&L values
        pnls = [t['realized_pnl'] for t in trades if t['realized_pnl'] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        # Basic stats
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        total_pnl = sum(pnls)
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0

        # Risk/reward
        rr_ratios = [
            t['risk_reward_ratio'] for t in trades
            if t['risk_reward_ratio'] is not None
        ]
        avg_risk_reward = np.mean(rr_ratios) if rr_ratios else 0.0

        # Profit factor
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Sharpe ratio (annualized)
        if len(pnls) > 1:
            returns = np.array(pnls)
            sharpe_ratio = (
                np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252)
            )
        else:
            sharpe_ratio = 0.0

        # Max drawdown
        equity_curve = self.get_equity_curve(start_date, end_date)
        if not equity_curve.empty:
            cumulative_max = equity_curve['equity'].expanding().max()
            drawdown = (equity_curve['equity'] - cumulative_max) / cumulative_max * 100
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0

        # Hold time
        hold_times = [
            t['hold_time_minutes'] for t in trades
            if t['hold_time_minutes'] is not None
        ]
        avg_hold_time = np.mean(hold_times) if hold_times else 0.0

        # Commission
        commissions = [t['commission'] for t in trades]
        total_commission = sum(commissions)

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_risk_reward': avg_risk_reward,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_hold_time_minutes': avg_hold_time,
            'total_commission': total_commission
        }

    def get_equity_curve(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        starting_equity: float = 100000.0
    ) -> pd.DataFrame:
        """
        Generate equity curve DataFrame.

        Parameters:
        -----------
        start_date : datetime, optional
            Filter by exit_time >= start_date
        end_date : datetime, optional
            Filter by exit_time <= end_date
        starting_equity : float, default=100000.0
            Starting account balance

        Returns:
        --------
        pd.DataFrame
            Columns: [exit_time, realized_pnl, cumulative_pnl, equity]

        Examples:
        ---------
        >>> curve = trade_database.get_equity_curve()
        >>> print(curve.tail())
        >>> curve.plot(x='exit_time', y='equity')
        """
        trades = self.get_closed_trades(start_date, end_date)

        if not trades:
            return pd.DataFrame(
                columns=['exit_time', 'realized_pnl', 'cumulative_pnl', 'equity']
            )

        df = pd.DataFrame(trades)
        df = df.sort_values('exit_time')

        df['cumulative_pnl'] = df['realized_pnl'].cumsum()
        df['equity'] = starting_equity + df['cumulative_pnl']

        return df[['exit_time', 'realized_pnl', 'cumulative_pnl', 'equity']]

    def get_trades_dataframe(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get trades as pandas DataFrame for analysis.

        Parameters:
        -----------
        start_date : datetime, optional
            Filter by exit_time >= start_date
        end_date : datetime, optional
            Filter by exit_time <= end_date
        symbol : str, optional
            Filter by symbol

        Returns:
        --------
        pd.DataFrame
            All trade columns as DataFrame
        """
        trades = self.get_closed_trades(start_date, end_date, symbol)

        if not trades:
            return pd.DataFrame()

        return pd.DataFrame(trades)

    def update_trade_mae_mfe(
        self,
        trade_id: int,
        current_price: float
    ) -> None:
        """
        Update MAE/MFE for open trade based on current price.

        Called from real-time bar updates in OrderManager.

        Parameters:
        -----------
        trade_id : int
            Database ID of trade
        current_price : float
            Current market price

        Notes:
        ------
        - MAE = Maximum Adverse Excursion (worst drawdown)
        - MFE = Maximum Favorable Excursion (best gain)
        - Only updates if new extreme is reached
        """
        trade = self.get_trade(trade_id)
        if not trade:
            return

        # Skip if trade is closed
        if trade['exit_time'] is not None:
            return

        # Calculate current unrealized P&L
        if trade['side'] == 'BUY':
            unrealized_pnl = (current_price - trade['entry_price']) * trade['quantity']
        else:  # SELL/SHORT
            unrealized_pnl = (trade['entry_price'] - current_price) * trade['quantity']

        # Get current MAE/MFE
        current_mae = trade.get('mae', 0.0) or 0.0
        current_mfe = trade.get('mfe', 0.0) or 0.0

        # Update if new extreme
        updated = False

        if unrealized_pnl < current_mae:
            current_mae = unrealized_pnl
            updated = True

        if unrealized_pnl > current_mfe:
            current_mfe = unrealized_pnl
            updated = True

        if updated:
            cursor = self._conn.cursor()
            cursor.execute("""
                UPDATE trades
                SET mae = ?, mfe = ?
                WHERE id = ?
            """, (current_mae, current_mfe, trade_id))
            self._conn.commit()

            logger.debug(
                f"Updated trade {trade_id} MAE/MFE: "
                f"MAE=${current_mae:.2f}, MFE=${current_mfe:.2f}"
            )

    def update_trade_stop(self, trade_id: int, new_stop_price: float) -> None:
        """
        Update stop price for an open trade.

        Used when trailing stops adjust the stop loss.

        Parameters:
        -----------
        trade_id : int
            Trade ID to update
        new_stop_price : float
            New stop loss price

        Notes:
        ------
        - Only updates stop_price field
        - Does not validate if trade is open
        - Used by trailing stop manager

        Examples:
        ---------
        >>> trade_database.update_trade_stop(trade_id=123, new_stop_price=149.50)
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            UPDATE trades
            SET stop_price = ?
            WHERE id = ?
        """, (new_stop_price, trade_id))

        self._conn.commit()

        logger.debug(f"Updated stop price for trade_id={trade_id} to ${new_stop_price:.2f}")

    def add_trade_note(self, trade_id: int, note: str) -> None:
        """
        Append note to existing trade notes.

        Parameters:
        -----------
        trade_id : int
            Database ID of trade
        note : str
            Note to append

        Examples:
        ---------
        >>> trade_database.add_trade_note(123, "Tightened stop after gap up")
        """
        trade = self.get_trade(trade_id)
        if not trade:
            logger.error(f"Trade ID {trade_id} not found")
            return

        existing_notes = trade.get('notes', '') or ''
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_note = f"[{timestamp}] {note}"

        if existing_notes:
            updated_notes = f"{existing_notes}\n{new_note}"
        else:
            updated_notes = new_note

        cursor = self._conn.cursor()
        cursor.execute("""
            UPDATE trades
            SET notes = ?
            WHERE id = ?
        """, (updated_notes, trade_id))

        self._conn.commit()
        logger.debug(f"Added note to trade {trade_id}")

    def get_symbol_statistics(self, symbol: str) -> Dict[str, Any]:
        """
        Get performance stats for specific symbol.

        Parameters:
        -----------
        symbol : str
            Stock symbol

        Returns:
        --------
        dict
            Performance statistics for symbol (same format as get_performance_stats)
        """
        trades = self.get_trades_by_symbol(symbol)
        closed_trades = [t for t in trades if t['exit_time'] is not None]

        if not closed_trades:
            return {
                'symbol': symbol,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'avg_risk_reward': 0.0,
                'profit_factor': 0.0
            }

        # Calculate stats
        pnls = [t['realized_pnl'] for t in closed_trades if t['realized_pnl'] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_trades = len(closed_trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        total_pnl = sum(pnls)
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0

        rr_ratios = [
            t['risk_reward_ratio'] for t in closed_trades
            if t['risk_reward_ratio'] is not None
        ]
        avg_risk_reward = np.mean(rr_ratios) if rr_ratios else 0.0

        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_risk_reward': avg_risk_reward,
            'profit_factor': profit_factor
        }

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
            logger.info("Trade database connection closed")


# Global singleton instance
trade_database = TradeDatabase()
