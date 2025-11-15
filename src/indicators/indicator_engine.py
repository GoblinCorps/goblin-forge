"""
Indicator Calculation Engine

Calculates all technical indicators required for SABR20 scoring system.

Indicators Calculated:
----------------------
1. Bollinger Bands (BB)
   - bb_upper: Upper band
   - bb_middle: Middle band (SMA)
   - bb_lower: Lower band
   - bb_width: Band width (upper - lower)
   - bb_position: Price position within bands (0-1 scale)

2. Stochastic RSI
   - stoch_rsi: Raw Stochastic RSI
   - stoch_rsi_k: %K line (smoothed)
   - stoch_rsi_d: %D line (signal)

3. MACD
   - macd: MACD line
   - macd_signal: Signal line
   - macd_hist: Histogram (MACD - signal)

4. RSI
   - rsi: Relative Strength Index

5. ATR
   - atr: Average True Range

Features:
---------
- TA-Lib integration for accurate calculations
- Batch processing (calculate all indicators at once)
- Data validation (minimum bars required)
- NaN handling (forward-fill strategy)
- Configuration-driven parameters
- Comprehensive error handling

Usage:
------
from src.indicators.indicator_engine import indicator_engine

# Calculate all indicators
df_with_indicators = indicator_engine.calculate_all(df)

# Calculate specific indicator
df_with_bb = indicator_engine.calculate_bollinger_bands(df)

# Validate if sufficient data available
if indicator_engine.validate_data(df):
    df = indicator_engine.calculate_all(df)
"""

from typing import Optional
import pandas as pd
import numpy as np
import talib
from loguru import logger

from src.config import config


class IndicatorEngine:
    """
    Technical indicator calculation engine.

    Calculates all indicators required for SABR20 scoring using TA-Lib.
    Handles data validation, NaN values, and configuration management.

    Attributes:
    -----------
    params : dict
        Indicator parameters from configuration
    min_bars_required : int
        Minimum number of bars needed for calculations
    """

    def __init__(self):
        """Initialize indicator engine with configuration."""
        # Load indicator parameters from config
        self.params = config.trading.indicators

        # Calculate minimum bars required (max of all indicator periods)
        self.min_bars_required = max([
            self.params.bollinger_bands.period,
            self.params.stochastic_rsi.rsi_period + self.params.stochastic_rsi.stoch_period,
            self.params.macd.slow_period + self.params.macd.signal_period,
            self.params.rsi.period,
            self.params.atr.period
        ]) + 50  # Extra buffer for smoothing

        logger.info(
            f"Indicator engine initialized (min bars required: {self.min_bars_required})"
        )

    def validate_data(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None
    ) -> bool:
        """
        Validate that DataFrame has sufficient data for indicator calculations.

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        symbol : str, optional
            Symbol name (for logging)

        Returns:
        --------
        bool
            True if data is valid and sufficient, False otherwise
        """
        try:
            # Check if DataFrame is empty
            if df is None or df.empty:
                logger.warning(f"Empty DataFrame for {symbol}")
                return False

            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                logger.warning(
                    f"Missing columns for {symbol}: {missing_cols}"
                )
                return False

            # Check sufficient bars
            if len(df) < self.min_bars_required:
                logger.warning(
                    f"Insufficient bars for {symbol}: {len(df)} < {self.min_bars_required}"
                )
                return False

            # Check for all NaN columns
            for col in required_cols:
                if df[col].isna().all():
                    logger.warning(
                        f"All NaN values in {col} for {symbol}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating data for {symbol}: {e}")
            return False

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate Bollinger Bands.

        Bollinger Bands consist of:
        - Middle band: SMA(period)
        - Upper band: SMA + (std_dev × stddev)
        - Lower band: SMA - (std_dev × stddev)

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'close' column)

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added columns:
            - bb_upper, bb_middle, bb_lower, bb_width, bb_position

        Notes:
        ------
        bb_position = (close - lower) / (upper - lower)
        - 0.0 = at lower band
        - 0.5 = at middle band
        - 1.0 = at upper band
        """
        try:
            period = self.params.bollinger_bands.period
            std_dev = self.params.bollinger_bands.std_dev

            # Calculate Bollinger Bands
            upper, middle, lower = talib.BBANDS(
                df['close'].values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0  # SMA
            )

            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower

            # Calculate band width
            df['bb_width'] = df['bb_upper'] - df['bb_lower']

            # Calculate price position within bands (0-1 scale)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (
                df['bb_upper'] - df['bb_lower']
            )

            # Handle edge cases (division by zero)
            df['bb_position'] = df['bb_position'].clip(0, 1)

            return df

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            raise

    def calculate_stochastic_rsi(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate Stochastic RSI.

        Stochastic RSI applies Stochastic oscillator formula to RSI values.
        Oscillates between 0 and 100, with oversold < 20 and overbought > 80.

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'close' column)

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added columns:
            - stoch_rsi_k: %K line (fast)
            - stoch_rsi_d: %D line (slow/signal)

        Notes:
        ------
        Used in SABR20 Component 2 (Bottom Phase) and Component 3 (Accumulation).
        Oversold threshold (< 20) is key signal for reversal setups.
        """
        try:
            rsi_period = self.params.stochastic_rsi.rsi_period
            stoch_period = self.params.stochastic_rsi.stoch_period
            k_smooth = self.params.stochastic_rsi.k_smooth
            d_smooth = self.params.stochastic_rsi.d_smooth

            # Calculate Stochastic RSI
            stoch_rsi_k, stoch_rsi_d = talib.STOCHRSI(
                df['close'].values,
                timeperiod=rsi_period,
                fastk_period=stoch_period,
                fastd_period=d_smooth,
                fastd_matype=0  # SMA
            )

            df['stoch_rsi_k'] = stoch_rsi_k
            df['stoch_rsi_d'] = stoch_rsi_d

            # Also calculate raw stochastic RSI for reference
            df['stoch_rsi'] = stoch_rsi_k

            return df

        except Exception as e:
            logger.error(f"Error calculating Stochastic RSI: {e}")
            raise

    def calculate_macd(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD consists of:
        - MACD line: EMA(fast) - EMA(slow)
        - Signal line: EMA(MACD, signal_period)
        - Histogram: MACD - Signal

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'close' column)

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added columns:
            - macd: MACD line
            - macd_signal: Signal line
            - macd_hist: Histogram

        Notes:
        ------
        Used in SABR20 Component 4 (Trend Momentum).
        Rising histogram indicates strengthening momentum.
        """
        try:
            fast = self.params.macd.fast_period
            slow = self.params.macd.slow_period
            signal = self.params.macd.signal_period

            # Calculate MACD
            macd, macd_signal, macd_hist = talib.MACD(
                df['close'].values,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal
            )

            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist

            return df

        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            raise

    def calculate_rsi(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate RSI (Relative Strength Index).

        RSI measures momentum, oscillating between 0 and 100.
        - RSI < 30: Oversold
        - RSI > 70: Overbought

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'close' column)

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added column:
            - rsi: RSI values

        Notes:
        ------
        Used in SABR20 Component 2 (Bottom Phase) and Component 3 (Accumulation).
        Key indicator for identifying oversold conditions.
        """
        try:
            period = self.params.rsi.period

            # Calculate RSI
            rsi = talib.RSI(df['close'].values, timeperiod=period)

            df['rsi'] = rsi

            return df

        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            raise

    def calculate_atr(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate ATR (Average True Range).

        ATR measures volatility, used for:
        - Stop loss placement (e.g., 1.5 × ATR below entry)
        - Position sizing adjustments
        - Volatility regime classification

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'high', 'low', 'close' columns)

        Returns:
        --------
        pd.DataFrame
            Input DataFrame with added column:
            - atr: ATR values

        Notes:
        ------
        Used in trade execution for stop loss calculation.
        Higher ATR = higher volatility = wider stops needed.
        """
        try:
            period = self.params.atr.period

            # Calculate ATR
            atr = talib.ATR(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                timeperiod=period
            )

            df['atr'] = atr

            return df

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            raise

    def calculate_all(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Calculate all indicators in batch.

        This is the primary method to use. It calculates all indicators
        required for SABR20 scoring in one pass.

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data (must have 'open', 'high', 'low', 'close', 'volume')
        symbol : str, optional
            Symbol name (for logging)

        Returns:
        --------
        pd.DataFrame or None
            DataFrame with all original columns plus indicator columns.
            Returns None if data validation fails.

        Raises:
        -------
        ValueError
            If data validation fails or calculations error

        Examples:
        ---------
        >>> df = pd.DataFrame({
        ...     'date': pd.date_range('2024-01-01', periods=200, freq='15min'),
        ...     'open': np.random.randn(200).cumsum() + 100,
        ...     'high': np.random.randn(200).cumsum() + 101,
        ...     'low': np.random.randn(200).cumsum() + 99,
        ...     'close': np.random.randn(200).cumsum() + 100,
        ...     'volume': np.random.randint(100000, 1000000, 200)
        ... })
        >>> df_with_indicators = indicator_engine.calculate_all(df, symbol='AAPL')
        >>> print(df_with_indicators.columns)
        Index(['date', 'open', 'high', 'low', 'close', 'volume',
               'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
               'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
               'macd', 'macd_signal', 'macd_hist',
               'rsi', 'atr'], dtype='object')
        """
        try:
            # Validate input data
            if not self.validate_data(df, symbol):
                logger.warning(f"Data validation failed for {symbol}")
                return None

            # Make a copy to avoid modifying original
            df_calc = df.copy()

            # Calculate all indicators
            df_calc = self.calculate_bollinger_bands(df_calc)
            df_calc = self.calculate_stochastic_rsi(df_calc)
            df_calc = self.calculate_macd(df_calc)
            df_calc = self.calculate_rsi(df_calc)
            df_calc = self.calculate_atr(df_calc)

            # Handle NaN values (forward fill for initial periods)
            # This is safe because we've validated sufficient bars exist
            indicator_cols = [
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
                'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
                'macd', 'macd_signal', 'macd_hist',
                'rsi', 'atr'
            ]

            for col in indicator_cols:
                if col in df_calc.columns:
                    # Fill leading NaNs with first valid value
                    df_calc[col] = df_calc[col].fillna(method='bfill', limit=10)

            # Log successful calculation
            nan_count = df_calc[indicator_cols].isna().sum().sum()
            if nan_count > 0:
                logger.warning(
                    f"{symbol}: {nan_count} NaN values in indicators after calculation"
                )
            else:
                logger.debug(
                    f"Successfully calculated all indicators for {symbol} "
                    f"({len(df_calc)} bars)"
                )

            return df_calc

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return None

    def get_indicator_list(self) -> list:
        """
        Get list of all indicator column names.

        Returns:
        --------
        list of str
            List of indicator column names that will be added to DataFrame

        Examples:
        ---------
        >>> indicator_engine.get_indicator_list()
        ['bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
         'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
         'macd', 'macd_signal', 'macd_hist', 'rsi', 'atr']
        """
        return [
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'stoch_rsi_k', 'stoch_rsi_d', 'stoch_rsi',
            'macd', 'macd_signal', 'macd_hist',
            'rsi', 'atr'
        ]


# Global singleton instance
indicator_engine = IndicatorEngine()
