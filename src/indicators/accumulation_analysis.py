"""
Accumulation Analysis (SABR20 Component 3)

Novel component that detects institutional accumulation using Stoch/RSI signal frequency ratio.

Theory:
-------
When institutional investors accumulate shares, they create a characteristic pattern:
- Frequent Stoch RSI oversold signals (< 20) as they buy on dips
- But RSI doesn't stay oversold (< 30) because buying prevents deep selloffs
- Result: High ratio of Stoch oversold signals to RSI oversold signals

This ratio is a unique detector of accumulation phases that precede trend expansion.

Accumulation Phases:
--------------------
1. Early Accumulation (18 pts)
   - Ratio > 5.0 (very high Stoch/RSI signal frequency)
   - RSI < 45 (still in oversold territory)
   - Best entry point - heavy accumulation before breakout

2. Mid Accumulation (14 pts)
   - Ratio 3.0-5.0 (high signal frequency)
   - RSI < 50 (neutral to slightly oversold)
   - High probability setup - accumulation ongoing

3. Late Accumulation (10 pts)
   - Ratio 1.5-3.0 (moderate signal frequency)
   - RSI 40-55 (neutral zone)
   - Setup maturing - accumulation slowing

4. Breakout (6 pts)
   - Ratio 0.8-1.5 (low signal frequency)
   - RSI > 50 (bullish momentum)
   - Confirmed breakout but late entry

Usage:
------
from src.indicators.accumulation_analysis import accumulation_analyzer

# Analyze accumulation phase
result = accumulation_analyzer.analyze(df)
print(result['phase'])  # 'early', 'mid', 'late', 'breakout', or 'none'
print(result['ratio'])  # Current Stoch/RSI signal ratio
print(result['points'])  # SABR20 points (0-18)

# Get historical ratio series
df_with_ratio = accumulation_analyzer.calculate_ratio_series(df, window=50)
print(df_with_ratio['accumulation_ratio'])
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from src.config import config


class AccumulationAnalyzer:
    """
    Accumulation phase analyzer using Stoch/RSI signal frequency ratio.

    Detects institutional accumulation by comparing frequency of
    Stochastic RSI oversold signals vs RSI oversold signals.

    Attributes:
    -----------
    window : int
        Lookback window for signal counting (default: 50 bars)
    stoch_oversold : float
        Stoch RSI oversold threshold (default: 20)
    rsi_oversold : float
        RSI oversold threshold (default: 30)
    phases : dict
        Accumulation phase definitions and scoring
    """

    def __init__(self):
        """Initialize accumulation analyzer with configuration."""
        # Load configuration
        acc_config = config.trading.indicators.accumulation
        self.window = acc_config.window
        self.stoch_oversold = acc_config.stoch_oversold
        self.rsi_oversold = acc_config.rsi_oversold

        # Load phase definitions from SABR20 config
        sabr_config = config.trading.sabr20.accumulation_phases
        self.phases = {
            'early': {
                'min_ratio': sabr_config.early.min_ratio,
                'max_rsi': sabr_config.early.max_rsi,
                'points': sabr_config.early.points,
                'description': 'Early Accumulation - Best Entry'
            },
            'mid': {
                'min_ratio': sabr_config.mid.min_ratio,
                'max_ratio': sabr_config.mid.max_ratio,
                'max_rsi': sabr_config.mid.max_rsi,
                'points': sabr_config.mid.points,
                'description': 'Mid Accumulation - High Probability'
            },
            'late': {
                'min_ratio': sabr_config.late.min_ratio,
                'max_ratio': sabr_config.late.max_ratio,
                'min_rsi': sabr_config.late.min_rsi,
                'max_rsi': sabr_config.late.max_rsi,
                'points': sabr_config.late.points,
                'description': 'Late Accumulation - Setup Maturing'
            },
            'breakout': {
                'min_ratio': sabr_config.breakout.min_ratio,
                'max_ratio': sabr_config.breakout.max_ratio,
                'min_rsi': sabr_config.breakout.min_rsi,
                'points': sabr_config.breakout.points,
                'description': 'Breakout - Confirmed but Late'
            }
        }

        logger.info(
            f"Accumulation analyzer initialized (window={self.window}, "
            f"stoch_threshold={self.stoch_oversold}, rsi_threshold={self.rsi_oversold})"
        )

    def calculate_ratio_series(
        self,
        df: pd.DataFrame,
        window: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate accumulation ratio series over sliding window.

        The ratio is calculated as:
        ratio = count(Stoch RSI < 20) / count(RSI < 30)

        A higher ratio indicates more frequent Stoch oversold signals
        relative to RSI oversold signals, suggesting accumulation.

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data with calculated indicators (must have 'stoch_rsi' and 'rsi')
        window : int, optional
            Lookback window for signal counting. If None, uses config default.

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added columns:
            - accumulation_ratio: Stoch/RSI signal frequency ratio
            - stoch_signals: Count of Stoch oversold signals in window
            - rsi_signals: Count of RSI oversold signals in window

        Examples:
        ---------
        >>> df_with_ratio = accumulation_analyzer.calculate_ratio_series(df, window=50)
        >>> print(df_with_ratio[['close', 'accumulation_ratio']].tail())
        """
        try:
            if window is None:
                window = self.window

            # Validate required columns
            required_cols = ['stoch_rsi', 'rsi']
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Make a copy
            df_calc = df.copy()

            # Detect Stoch RSI oversold signals (< threshold)
            stoch_oversold_flags = (df_calc['stoch_rsi'] < self.stoch_oversold).astype(int)

            # Detect RSI oversold signals (< threshold)
            rsi_oversold_flags = (df_calc['rsi'] < self.rsi_oversold).astype(int)

            # Count signals in rolling window
            df_calc['stoch_signals'] = stoch_oversold_flags.rolling(
                window=window,
                min_periods=window // 2  # Allow partial windows early on
            ).sum()

            df_calc['rsi_signals'] = rsi_oversold_flags.rolling(
                window=window,
                min_periods=window // 2
            ).sum()

            # Calculate ratio (avoid division by zero)
            # If no RSI signals, use a small number to avoid inf
            df_calc['accumulation_ratio'] = df_calc['stoch_signals'] / (
                df_calc['rsi_signals'].replace(0, 0.1)
            )

            # Handle edge cases
            # If both are zero, ratio should be 0 (no signals at all)
            df_calc.loc[
                (df_calc['stoch_signals'] == 0) & (df_calc['rsi_signals'] == 0),
                'accumulation_ratio'
            ] = 0

            # Cap extreme ratios (for display purposes)
            df_calc['accumulation_ratio'] = df_calc['accumulation_ratio'].clip(0, 20)

            return df_calc

        except Exception as e:
            logger.error(f"Error calculating accumulation ratio series: {e}")
            raise

    def classify_phase(
        self,
        ratio: float,
        rsi: float
    ) -> Dict[str, Any]:
        """
        Classify accumulation phase based on ratio and RSI.

        Parameters:
        -----------
        ratio : float
            Current Stoch/RSI signal frequency ratio
        rsi : float
            Current RSI value

        Returns:
        --------
        dict
            Phase classification with keys:
            - phase: Phase name ('early', 'mid', 'late', 'breakout', 'none')
            - points: SABR20 points (0-18)
            - description: Human-readable description

        Examples:
        ---------
        >>> phase_info = accumulation_analyzer.classify_phase(ratio=5.5, rsi=42)
        >>> print(phase_info['phase'])
        'early'
        >>> print(phase_info['points'])
        18
        """
        # Early Accumulation (highest priority - best entry)
        if ratio >= self.phases['early']['min_ratio'] and rsi <= self.phases['early']['max_rsi']:
            return {
                'phase': 'early',
                'points': self.phases['early']['points'],
                'description': self.phases['early']['description']
            }

        # Mid Accumulation
        mid_phase = self.phases['mid']
        if (mid_phase['min_ratio'] <= ratio < mid_phase.get('max_ratio', float('inf'))
            and rsi <= mid_phase['max_rsi']):
            return {
                'phase': 'mid',
                'points': mid_phase['points'],
                'description': mid_phase['description']
            }

        # Late Accumulation
        late_phase = self.phases['late']
        if (late_phase['min_ratio'] <= ratio < late_phase.get('max_ratio', float('inf'))
            and late_phase.get('min_rsi', 0) <= rsi <= late_phase['max_rsi']):
            return {
                'phase': 'late',
                'points': late_phase['points'],
                'description': late_phase['description']
            }

        # Breakout
        breakout_phase = self.phases['breakout']
        if (breakout_phase['min_ratio'] <= ratio < breakout_phase.get('max_ratio', float('inf'))
            and rsi >= breakout_phase['min_rsi']):
            return {
                'phase': 'breakout',
                'points': breakout_phase['points'],
                'description': breakout_phase['description']
            }

        # No accumulation detected
        return {
            'phase': 'none',
            'points': 0,
            'description': 'No Accumulation Detected'
        }

    def analyze(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze current accumulation phase.

        This is the primary method for accumulation analysis. It calculates
        the ratio series and classifies the current (latest) bar's phase.

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data with indicators (must have 'stoch_rsi' and 'rsi')
        symbol : str, optional
            Symbol name (for logging)

        Returns:
        --------
        dict
            Accumulation analysis with keys:
            - phase: Current phase ('early', 'mid', 'late', 'breakout', 'none')
            - ratio: Current accumulation ratio
            - points: SABR20 Component 3 points (0-18)
            - description: Phase description
            - stoch_signals: Count of Stoch oversold signals in window
            - rsi_signals: Count of RSI oversold signals in window
            - rsi: Current RSI value
            - history: Last 10 ratio values (for trend analysis)

        Examples:
        ---------
        >>> result = accumulation_analyzer.analyze(df, symbol='AAPL')
        >>> print(f"Phase: {result['phase']} ({result['points']} pts)")
        >>> print(f"Ratio: {result['ratio']:.2f}")
        >>> print(f"Description: {result['description']}")
        """
        try:
            # Validate input
            if df is None or df.empty:
                logger.warning(f"Empty DataFrame for {symbol}")
                return self._empty_result()

            required_cols = ['stoch_rsi', 'rsi']
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                logger.warning(
                    f"Missing indicators for {symbol}: {missing_cols}"
                )
                return self._empty_result()

            # Calculate ratio series
            df_with_ratio = self.calculate_ratio_series(df)

            # Get latest values
            latest = df_with_ratio.iloc[-1]
            ratio = latest['accumulation_ratio']
            rsi = latest['rsi']
            stoch_signals = latest['stoch_signals']
            rsi_signals = latest['rsi_signals']

            # Classify phase
            phase_info = self.classify_phase(ratio, rsi)

            # Get recent ratio history (for trend analysis)
            history = df_with_ratio['accumulation_ratio'].tail(10).tolist()

            result = {
                'phase': phase_info['phase'],
                'ratio': float(ratio),
                'points': phase_info['points'],
                'description': phase_info['description'],
                'stoch_signals': int(stoch_signals),
                'rsi_signals': int(rsi_signals),
                'rsi': float(rsi),
                'history': history
            }

            logger.debug(
                f"{symbol}: Accumulation phase={result['phase']} "
                f"ratio={result['ratio']:.2f} points={result['points']}"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing accumulation for {symbol}: {e}")
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """
        Return empty/default result for error cases.

        Returns:
        --------
        dict
            Default result with phase='none' and 0 points
        """
        return {
            'phase': 'none',
            'ratio': 0.0,
            'points': 0,
            'description': 'Insufficient Data',
            'stoch_signals': 0,
            'rsi_signals': 0,
            'rsi': 50.0,
            'history': []
        }

    def batch_analyze(
        self,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze accumulation for multiple symbols in batch.

        Parameters:
        -----------
        data_dict : dict
            Dictionary mapping symbols to DataFrames with indicators
            {symbol: df_with_indicators}

        Returns:
        --------
        dict
            Dictionary mapping symbols to accumulation results
            {symbol: analysis_result}

        Examples:
        ---------
        >>> data = {
        ...     'AAPL': df_aapl_with_indicators,
        ...     'MSFT': df_msft_with_indicators
        ... }
        >>> results = accumulation_analyzer.batch_analyze(data)
        >>> for symbol, result in results.items():
        ...     print(f"{symbol}: {result['phase']} ({result['points']} pts)")
        """
        results = {}

        for symbol, df in data_dict.items():
            try:
                results[symbol] = self.analyze(df, symbol)
            except Exception as e:
                logger.error(f"Error in batch analysis for {symbol}: {e}")
                results[symbol] = self._empty_result()

        return results

    def get_phase_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of all accumulation phases and their criteria.

        Returns:
        --------
        dict
            Phase definitions with criteria and scoring

        Examples:
        ---------
        >>> summary = accumulation_analyzer.get_phase_summary()
        >>> for phase, info in summary.items():
        ...     print(f"{phase}: {info['points']} points - {info['description']}")
        """
        return self.phases.copy()


# Global singleton instance
accumulation_analyzer = AccumulationAnalyzer()
