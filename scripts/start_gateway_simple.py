#!/usr/bin/env python3
"""
Simple IB Gateway Startup Script using ib_insync
Screener Trading System - Paper Trading Mode

This script uses ib_insync's IBC integration to start IB Gateway
in headless mode for paper trading on port 4002.

Requirements:
- IB Gateway installed at ~/Jts/
- ib_insync package (already in venv)
- IB credentials (username/password)

Usage:
    python scripts/start_gateway_simple.py

Environment Variables:
    IB_USERNAME: IB account username (optional, will prompt if not set)
    IB_PASSWORD: IB account password (optional, will prompt if not set)
"""

import os
import sys
import time
import socket
from pathlib import Path
from getpass import getpass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ib_insync import IBC, IB
from loguru import logger


# Configuration
IB_GATEWAY_DIR = Path.home() / "Jts"
TRADING_MODE = "paper"  # Always paper for safety
PAPER_PORT = 4002
TIMEOUT = 120  # seconds


def check_port_available(port: int) -> bool:
    """Check if a port is already in use."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True  # Port is in use
    except (socket.error, socket.timeout):
        return False  # Port is not in use


def get_credentials():
    """Get IB credentials from environment or prompt user."""
    username = os.getenv("IB_USERNAME")
    password = os.getenv("IB_PASSWORD")

    if not username:
        print("\nIB Gateway Credentials Required")
        print("=" * 50)
        username = input("IB Username: ").strip()

    if not password:
        password = getpass("IB Password: ").strip()

    if not username or not password:
        logger.error("Username and password are required")
        sys.exit(1)

    return username, password


def start_gateway():
    """Start IB Gateway using IBC."""
    logger.info("=" * 60)
    logger.info("IB Gateway Startup - Screener Trading System")
    logger.info("=" * 60)
    logger.info(f"Trading Mode:  {TRADING_MODE}")
    logger.info(f"Target Port:   {PAPER_PORT}")
    logger.info(f"Gateway Dir:   {IB_GATEWAY_DIR}")
    logger.info("=" * 60)

    # Check if already running
    if check_port_available(PAPER_PORT):
        logger.warning(f"Port {PAPER_PORT} is already in use")
        logger.warning("IB Gateway may already be running")
        logger.info("")
        response = input("Use existing gateway? (y/n): ").strip().lower()
        if response == 'y':
            logger.info("Using existing gateway connection")
            return True
        else:
            logger.error("Please stop the existing gateway first")
            logger.error(f"Command: pkill -f ibgateway")
            return False

    # Verify IB Gateway installation
    if not IB_GATEWAY_DIR.exists():
        logger.error(f"IB Gateway not found at {IB_GATEWAY_DIR}")
        logger.error("Please install IB Gateway from:")
        logger.error("https://www.interactivebrokers.com/en/trading/ibgateway-stable.php")
        return False

    # Get credentials
    logger.info("\n[1/3] Getting credentials...")
    username, password = get_credentials()
    logger.info(f"Username: {username}")

    # Create IBC instance
    logger.info("\n[2/3] Configuring IBC...")
    try:
        ibc = IBC(
            twsVersion=1040,  # IB Gateway 10.40 (update if needed)
            gateway=True,
            tradingMode=TRADING_MODE,
            userid=username,
            password=password,
            twsPath=str(IB_GATEWAY_DIR),
            ibcPath=None,  # Will download if needed
        )

        logger.info("IBC configuration created")
        logger.info(f"  Gateway version: 1040")
        logger.info(f"  Trading mode: {TRADING_MODE}")
        logger.info(f"  Gateway path: {IB_GATEWAY_DIR}")

    except Exception as e:
        logger.error(f"Failed to create IBC configuration: {e}")
        return False

    # Start IB Gateway
    logger.info("\n[3/3] Starting IB Gateway...")
    try:
        ibc.start()
        logger.info("Gateway process started")
        logger.info("Waiting for API socket...")

        # Wait for port to become available
        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            if check_port_available(PAPER_PORT):
                elapsed = time.time() - start_time
                logger.success(f"\n✓ API socket listening on port {PAPER_PORT}")
                logger.success(f"  Startup time: {elapsed:.1f}s")
                break

            # Progress indicator
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                logger.info(f"  ... still waiting ({elapsed}s elapsed)")

            time.sleep(2)
        else:
            logger.error(f"\nERROR: Gateway did not start within {TIMEOUT}s")
            logger.error("Common issues:")
            logger.error("  - Wrong credentials")
            logger.error("  - 2FA timeout (check your phone/authenticator)")
            logger.error("  - Gateway already running")
            logger.error("  - Java not installed")
            ibc.terminate()
            return False

        # Test connection
        logger.info("\n[4/4] Testing connection...")
        ib = IB()
        try:
            ib.connect('127.0.0.1', PAPER_PORT, clientId=999)
            logger.success("✓ Successfully connected to IB Gateway")
            logger.info(f"  Account: {ib.managedAccounts()}")
            ib.disconnect()
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            logger.warning("Gateway may still be initializing")

        # Success
        logger.info("")
        logger.success("=" * 60)
        logger.success("✓ IB Gateway READY for Screener")
        logger.success("=" * 60)
        logger.success(f"Mode:     {TRADING_MODE}")
        logger.success(f"Port:     {PAPER_PORT}")
        logger.success(f"Status:   Running")
        logger.success("=" * 60)
        logger.info("")
        logger.info("Gateway will continue running in the background")
        logger.info("To stop: ibc.terminate() or pkill -f ibgateway")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run tests: pytest tests/test_ib_manager_comprehensive.py -v")
        logger.info("  2. Run screener: python src/main.py")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"Failed to start gateway: {e}")
        logger.error("Check that:")
        logger.error("  - Java is installed (java -version)")
        logger.error("  - IB Gateway is properly installed")
        logger.error("  - No other gateway process is running")
        return False


def main():
    """Main entry point."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    try:
        success = start_gateway()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
