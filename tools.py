import random
from typing import Optional, Dict, Any
import inspect


def deployToken(
    name: str,
    uri: str,
    symbol: str,
    decimal: int,
    initial_supply: Optional[float] = None,
) -> Dict[str, str]:
    """
    Simulates deploying a fungible token on the Solana blockchain.
    """
    mint_address = f"FakeMintAddress_{random.randint(100000, 999999)}"
    response = {
        "mint": mint_address,
        "name": name,
        "symbol": symbol,
        "decimals": decimal,
        "uri": uri,
        "initial_supply": initial_supply if initial_supply else "Not provided",
    }
    return response


def getBalance(token_address: Optional[str] = None) -> float:
    """
    Simulates retrieving the balance of SOL or a specific token in a wallet.
    """
    balance = round(random.uniform(0.1, 1000), 4)
    asset = "SOL" if not token_address else f"Token ({token_address})"
    return f"Balance retrieved: {balance} {asset}"


def getTokenDataByAddress(mint: str) -> Optional[Dict[str, str]]:
    """
    Simulates fetching token metadata from the Jupiter API using a mint address.
    """
    return {"name": "Simulated Token", "symbol": "SIM", "address": mint}


def getTokenAddressFromTicker(ticker: str) -> Optional[str]:
    """
    Simulates fetching the mint address of a token based on its ticker symbol.
    """
    return f"FakeMintAddress_{ticker}"


def transfer(to: str, amount: float, mint: Optional[str] = None) -> str:
    """
    Simulates transferring SOL or SPL tokens to a recipient.
    """
    asset = "SOL" if not mint else f"Token ({mint})"
    return f"Payment transferred: {amount} {asset} to {to}"


def lend_asset(amount: float) -> str:
    """
    Simulates lending USDC tokens for yield.
    """
    return f"Lent {amount} USDC successfully"


def flash_open_trade(
    token: str, side: str, collateral_usd: float, leverage: float
) -> Dict[str, Any]:
    """
    Simulates opening a flash trade.
    """
    return {
        "success": True,
        "transaction": f"SimulatedFlashOpenTx_{random.randint(1000, 9999)}",
        "message": f"Flash trade opened: {side} {token} with {collateral_usd} USD at {leverage}x leverage",
    }


def trade(
    output_mint: str,
    input_amount: float,
    input_mint: str = "USDC",
    slippage_bps: int = 300,
) -> str:
    """
    Simulates swapping tokens using Jupiter Exchange.
    """
    return f"Traded {input_amount} {input_mint} for {output_mint} with {slippage_bps} bps slippage"


def flash_close_trade(token: str, side: str) -> Dict[str, Any]:
    """
    Simulates closing a flash trade.
    """
    return {
        "success": True,
        "transaction": f"SimulatedFlashCloseTx_{random.randint(1000, 9999)}",
        "message": f"Flash trade closed: {side} {token}",
    }


tool_func_dict = {
    "getBalance": getBalance,
    "deployToken": deployToken,
    "getTokenAddressFromTicker": getTokenAddressFromTicker,
    "transfer": transfer,
    "lend_asset": lend_asset,
    "flash_open_trade": flash_open_trade,
    "trade": trade,
    "flash_close_trade": flash_close_trade,
}


def check_missing(data, func):
    missing_params = []
    for param, value in data.items():
        func_params = inspect.signature(tool_func_dict[func]).parameters
        if value is None or value == "None":
            if "optional" in str(func_params[param].annotation).lower():
                pass
            else:
                missing_params.append(param)
    return missing_params
