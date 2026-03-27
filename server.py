#!/usr/bin/env python3
"""XRPLOracle MCP Server v1.0.0 — Port 11401
XRP Ledger Intelligence for AI Agents.
RLUSD compliance, payment/settlement intelligence, AMM liquidity,
tokenized assets, issuer trust analysis, DEX order book, escrow
monitoring, institutional DeFi. Evidence-grade data for programmable
money, cross-border payments, and regulated tokenization on XRPL.
"""
import os, sys, json, logging, aiohttp, asyncio
from datetime import datetime, timezone

sys.path.insert(0, "/root/whitelabel")
from shared.utils.mcp_base import WhitelabelMCPServer

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [XRPLOracle] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("/root/whitelabel/logs/xrploracle.log", mode="a")])
logger = logging.getLogger("XRPLOracle")

PRODUCT_NAME = "XRPLOracle"
VERSION      = "1.0.0"
PORT_MCP     = 11401
PORT_HEALTH  = 11402

XRPL_RPC = "https://xrplcluster.com"
XRPL_S2  = "https://s2.ripple.com:51234"
CG       = "https://api.coingecko.com/api/v3"
LLAMA    = "https://api.llama.fi"
HEADERS  = {"User-Agent": "XRPLOracle-ToolOracle/1.0", "Accept": "application/json", "Content-Type": "application/json"}

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

async def xrpl(method, params=None, timeout=15):
    body = {"method": method, "params": [params or {}]}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(XRPL_RPC, json=body, headers=HEADERS,
                              timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                if r.status == 200:
                    d = await r.json(content_type=None)
                    return d.get("result", {})
    except Exception as e:
        logger.warning(f"XRPL RPC error: {e}")
    return {}

async def get(url, params=None, timeout=15):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params,
                             headers={"User-Agent": "XRPLOracle-ToolOracle/1.0", "Accept": "application/json"},
                             timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
                return {"error": f"HTTP {r.status}"}
    except Exception as e:
        return {"error": str(e)}

def drops_to_xrp(drops):
    try:
        return round(int(drops) / 1_000_000, 6)
    except:
        return 0

def risk_grade(score):
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    if score >= 20: return "D"
    return "F"

# Known XRPL issuers/tokens
KNOWN_ISSUERS = {
    "RLUSD": {"issuer": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De", "issuer_name": "Ripple",
              "type": "stablecoin", "regulated": True, "peg": "USD"},
    "USDC":  {"issuer": "rcEGREd8NmkKRE8GE424sksyt1tJVFZwu", "issuer_name": "Circle (Bridge)",
              "type": "stablecoin", "regulated": True, "peg": "USD"},
    "SOLO":  {"issuer": "rHZwvHEs56GCmHupwjA4RY7oPA3EoAJWuW", "issuer_name": "Sologenic",
              "type": "token", "regulated": False},
    "CSC":   {"issuer": "rCSCManTZ8ME9EoLrSHHYKW8PPwWMgkwr", "issuer_name": "CasinoCoin",
              "type": "token", "regulated": False},
}

async def handle_overview(args):
    """XRPL network overview: XRP price, ledger stats, reserve, fee"""
    price_task = get(f"{CG}/simple/price", {
        "ids": "ripple", "vs_currencies": "usd,eur",
        "include_24hr_change": "true", "include_market_cap": "true", "include_24hr_vol": "true"
    })
    server_task = xrpl("server_info")
    fee_task    = xrpl("fee")

    price_data, server_data, fee_data = await asyncio.gather(price_task, server_task, fee_task)

    xrp = price_data.get("ripple", {}) if isinstance(price_data, dict) else {}
    info = server_data.get("info", {}) if isinstance(server_data, dict) else {}
    validated = info.get("validated_ledger", {})
    fee = fee_data.get("drops", {}) if isinstance(fee_data, dict) else {}

    return {
        "chain": "XRPL",
        "network": "mainnet",
        "timestamp": ts(),
        "price": {
            "usd": xrp.get("usd"),
            "eur": xrp.get("eur"),
            "change_24h_pct": xrp.get("usd_24h_change"),
            "market_cap_usd": xrp.get("usd_market_cap"),
            "volume_24h_usd": xrp.get("usd_24h_vol")
        },
        "network": {
            "latest_ledger": validated.get("seq"),
            "ledger_hash": validated.get("hash", "")[:16] + "...",
            "tps": info.get("load_factor"),
            "reserve_base_xrp": drops_to_xrp(validated.get("reserve_base", 0)),
            "reserve_increment_xrp": drops_to_xrp(validated.get("reserve_inc", 0)),
            "server_state": info.get("server_state"),
            "peers": info.get("peers")
        },
        "fees": {
            "base_fee_drops": fee.get("base_fee"),
            "median_fee_drops": fee.get("median_fee"),
            "open_ledger_fee_drops": fee.get("open_ledger_fee"),
            "base_fee_xrp": drops_to_xrp(fee.get("base_fee", 0))
        },
        "source": "CoinGecko + XRPL Cluster"
    }

async def handle_rlusd(args):
    """RLUSD stablecoin compliance and risk intelligence — Ripple's USD stablecoin"""
    RLUSD_ISSUER = KNOWN_ISSUERS["RLUSD"]["issuer"]

    # Get RLUSD from CoinGecko (xrp market)
    # Also check issuer account info
    price_task = get(f"{CG}/coins/markets", {
        "vs_currency": "usd", "ids": "ripple-usd",
        "include_24hr_change": "true"
    })
    issuer_task = xrpl("account_info", {"account": RLUSD_ISSUER, "ledger_index": "validated"})
    obligations_task = xrpl("gateway_balances", {
        "account": RLUSD_ISSUER, "ledger_index": "validated",
        "hotwallet": []
    })

    price_data, issuer_data, obligations_data = await asyncio.gather(
        price_task, issuer_task, obligations_task
    )

    price_list = price_data if isinstance(price_data, list) else []
    rlusd_mkt = price_list[0] if price_list else {}
    price = rlusd_mkt.get("current_price")
    peg_dev = abs(price - 1.0) if price else None
    peg_status = "STABLE" if peg_dev is not None and peg_dev < 0.005 else \
                 "MINOR_DEVIATION" if peg_dev is not None and peg_dev < 0.02 else "DEPEGGED"

    obligations = obligations_data.get("obligations", {}) if isinstance(obligations_data, dict) else {}
    rlusd_supply = obligations.get("RLUSD", "0")

    score = 90 if peg_status == "STABLE" else 50
    issuer_acc = issuer_data.get("account_data", {}) if isinstance(issuer_data, dict) else {}

    return {
        "asset": "RLUSD",
        "issuer": RLUSD_ISSUER,
        "issuer_name": "Ripple Labs",
        "type": "regulated_stablecoin",
        "peg": "USD",
        "price_usd": price,
        "peg_deviation": round(peg_dev, 6) if peg_dev is not None else None,
        "peg_deviation_pct": round(peg_dev * 100, 4) if peg_dev is not None else None,
        "peg_status": peg_status,
        "circulating_supply": rlusd_supply,
        "market_cap_usd": rlusd_mkt.get("market_cap"),
        "volume_24h_usd": rlusd_mkt.get("total_volume"),
        "issuer_xrp_balance": drops_to_xrp(issuer_acc.get("Balance", 0)),
        "issuer_flags": issuer_acc.get("Flags"),
        "compliance": {
            "regulated": True,
            "regulator": "NYDFS",
            "mica_status": "Under assessment (non-EU issuer)",
            "kyc_required": True,
            "blacklist_capability": True,
            "freeze_capability": True
        },
        "risk_score": score,
        "risk_grade": risk_grade(score),
        "timestamp": ts(),
        "source": "CoinGecko + XRPL Cluster"
    }

async def handle_account_intel(args):
    """XRPL account intelligence: XRP balance, offers, trust lines, escrows"""
    address = args.get("address", "").strip()
    if not address:
        return {"error": "address required (XRPL classic address r...)"}

    acc, lines, offers, escrows = await asyncio.gather(
        xrpl("account_info", {"account": address, "ledger_index": "validated"}),
        xrpl("account_lines", {"account": address, "ledger_index": "validated", "limit": 20}),
        xrpl("account_offers", {"account": address, "ledger_index": "validated", "limit": 10}),
        xrpl("account_escrows", {"account": address, "ledger_index": "validated"}),
    )

    acc_data = acc.get("account_data", {}) if isinstance(acc, dict) else {}
    balance_drops = acc_data.get("Balance", "0")
    trust_lines = lines.get("lines", []) if isinstance(lines, dict) else []
    open_offers = offers.get("offers", []) if isinstance(offers, dict) else []
    escrow_list = escrows.get("account_escrows", []) if isinstance(escrows, dict) else []

    flags = acc_data.get("Flags", 0)
    # Flag decoding (XRPL account flags)
    flag_names = []
    if flags & 0x00100000: flag_names.append("lsfDefaultRipple")
    if flags & 0x00200000: flag_names.append("lsfDepositAuth")
    if flags & 0x00400000: flag_names.append("lsfDisableMaster")
    if flags & 0x00800000: flag_names.append("lsfNoFreeze")
    if flags & 0x02000000: flag_names.append("lsfGlobalFreeze")

    score = 60
    if len(trust_lines) > 0: score += 5
    if len(escrow_list) > 0: score -= 5

    return {
        "address": address,
        "xrp_balance": drops_to_xrp(balance_drops),
        "sequence": acc_data.get("Sequence"),
        "trust_lines": len(trust_lines),
        "tokens": [{"currency": tl.get("currency"),
                    "issuer": tl.get("account", "")[:12] + "...",
                    "balance": tl.get("balance"),
                    "limit": tl.get("limit")} for tl in trust_lines[:10]],
        "open_offers": len(open_offers),
        "active_escrows": len(escrow_list),
        "flags_raw": flags,
        "flags_decoded": flag_names,
        "risk_score": score,
        "risk_grade": risk_grade(score),
        "timestamp": ts(),
        "source": "XRPL Cluster"
    }

async def handle_dex_orderbook(args):
    """XRPL DEX order book intelligence for any trading pair"""
    base_currency = args.get("base_currency", "XRP")
    base_issuer   = args.get("base_issuer", "")
    quote_currency = args.get("quote_currency", "RLUSD")
    quote_issuer   = args.get("quote_issuer", KNOWN_ISSUERS["RLUSD"]["issuer"])
    limit = min(args.get("limit", 10), 20)

    base = {"currency": "XRP"} if base_currency == "XRP" else \
           {"currency": base_currency, "issuer": base_issuer}
    quote = {"currency": "XRP"} if quote_currency == "XRP" else \
            {"currency": quote_currency, "issuer": quote_issuer}

    bids_task = xrpl("book_offers", {"taker_gets": quote, "taker_pays": base, "limit": limit})
    asks_task = xrpl("book_offers", {"taker_gets": base, "taker_pays": quote, "limit": limit})

    bids_data, asks_data = await asyncio.gather(bids_task, asks_task)

    def parse_offers(offers_data):
        offers = offers_data.get("offers", []) if isinstance(offers_data, dict) else []
        result = []
        for o in offers[:5]:
            tg = o.get("TakerGets", {})
            tp = o.get("TakerPays", {})
            tg_val = drops_to_xrp(tg) if isinstance(tg, str) else float(tg.get("value", 0))
            tp_val = drops_to_xrp(tp) if isinstance(tp, str) else float(tp.get("value", 0))
            result.append({"get": round(tg_val, 4), "pay": round(tp_val, 4),
                           "quality": o.get("quality")})
        return result

    return {
        "pair": f"{base_currency}/{quote_currency}",
        "bids": parse_offers(bids_data),
        "asks": parse_offers(asks_data),
        "timestamp": ts(),
        "note": "XRPL has a native on-chain DEX — no AMM required for basic order matching",
        "source": "XRPL Cluster book_offers"
    }

async def handle_amm_pools(args):
    """XRPL AMM liquidity pool intelligence"""
    # AMM instance info via account_info with amm flag
    asset = args.get("asset", "RLUSD")
    asset2 = args.get("asset2", "XRP")

    issuer1 = KNOWN_ISSUERS.get(asset, {}).get("issuer", "")
    asset_obj1 = {"currency": "XRP"} if asset == "XRP" else {"currency": asset, "issuer": issuer1}
    asset_obj2 = {"currency": "XRP"} if asset2 == "XRP" else {"currency": asset2, "issuer": KNOWN_ISSUERS.get(asset2, {}).get("issuer", "")}

    amm = await xrpl("amm_info", {"asset": asset_obj1, "asset2": asset_obj2, "ledger_index": "validated"})

    if isinstance(amm, dict) and amm.get("amm"):
        a = amm["amm"]
        lp_token = a.get("lp_token", {})
        amount1 = a.get("amount", {})
        amount2 = a.get("amount2", {})

        xrp_amount = drops_to_xrp(amount1) if isinstance(amount1, str) else None
        token_amount = float(amount2.get("value", 0)) if isinstance(amount2, dict) else drops_to_xrp(amount2)

        return {
            "pair": f"{asset}/{asset2}",
            "amm_account": a.get("account"),
            "xrp_reserve": xrp_amount,
            "token_reserve": token_amount,
            "lp_token": lp_token.get("currency"),
            "lp_supply": lp_token.get("value"),
            "trading_fee_pct": round(a.get("trading_fee", 0) / 1000, 3),
            "vote_slots": len(a.get("vote_slots", [])),
            "timestamp": ts(),
            "source": "XRPL Cluster AMM"
        }

    return {
        "pair": f"{asset}/{asset2}",
        "error": "AMM pool not found or not yet active",
        "known_assets": list(KNOWN_ISSUERS.keys()),
        "timestamp": ts()
    }

async def handle_payment_intel(args):
    """XRPL cross-border payment intelligence: routes, costs, settlement times"""
    amount_xrp = args.get("amount_xrp", 1000)
    from_currency = args.get("from_currency", "USD")
    to_currency   = args.get("to_currency", "EUR")

    # XRP price for conversion
    price_data = await get(f"{CG}/simple/price",
                           {"ids": "ripple", "vs_currencies": "usd,eur"})
    xrp_usd = price_data.get("ripple", {}).get("usd", 0) if isinstance(price_data, dict) else 0
    xrp_eur = price_data.get("ripple", {}).get("eur", 0) if isinstance(price_data, dict) else 0

    return {
        "payment_scenario": f"{from_currency} → XRPL → {to_currency}",
        "xrp_used_as_bridge": amount_xrp,
        "xrp_price_usd": xrp_usd,
        "xrp_price_eur": xrp_eur,
        "usd_equivalent": round(amount_xrp * xrp_usd, 2),
        "eur_equivalent": round(amount_xrp * xrp_eur, 2),
        "settlement_finality": "3-5 seconds",
        "transaction_cost_xrp": 0.000012,
        "transaction_cost_usd": round(0.000012 * xrp_usd, 6),
        "corridors": {
            "USD→EUR": "RLUSD → AMM → EURC (experimental)",
            "USD→XRP→fiat": "Via on-demand liquidity (ODL) partners",
            "Any→Any": "Path-finding via XRPL path payment"
        },
        "institutional_use": {
            "ODL": "On-Demand Liquidity — Ripple's cross-border product",
            "CBDC_bridge": "XRPL has CBDC sandbox for central bank pilots",
            "Payment_v3": "Hooks amendment enables programmable payments"
        },
        "timestamp": ts(),
        "source": "CoinGecko + ToolOracle"
    }

async def handle_token_check(args):
    """XRPL token / issued currency risk check and issuer analysis"""
    currency = args.get("currency", "").upper()
    issuer   = args.get("issuer", "")

    if currency in KNOWN_ISSUERS and not issuer:
        info = KNOWN_ISSUERS[currency]
        issuer = info["issuer"]

    if not issuer:
        return {
            "known_tokens": {k: {"issuer": v["issuer"][:12] + "...", "type": v["type"],
                                 "regulated": v["regulated"]}
                             for k, v in KNOWN_ISSUERS.items()},
            "message": "Provide currency and issuer, or use a known token symbol"
        }

    issuer_info, obligations = await asyncio.gather(
        xrpl("account_info", {"account": issuer, "ledger_index": "validated"}),
        xrpl("gateway_balances", {"account": issuer, "ledger_index": "validated", "hotwallet": []})
    )

    acc = issuer_info.get("account_data", {}) if isinstance(issuer_info, dict) else {}
    obligations_dict = obligations.get("obligations", {}) if isinstance(obligations, dict) else {}
    supply = obligations_dict.get(currency, "0")

    flags = acc.get("Flags", 0)
    has_freeze   = bool(flags & 0x01000000)  # lsfGlobalFreeze-capable
    has_nofreeze = bool(flags & 0x00800000)  # lsfNoFreeze

    known = KNOWN_ISSUERS.get(currency, {})
    score = 50
    if known.get("regulated"): score += 25
    if not has_freeze: score += 10  # No freeze = more decentralized
    if float(supply or 0) > 0: score += 5

    return {
        "currency": currency,
        "issuer": issuer,
        "issuer_name": known.get("issuer_name", "Unknown"),
        "type": known.get("type", "unknown"),
        "regulated": known.get("regulated", False),
        "peg": known.get("peg"),
        "total_supply_issued": supply,
        "issuer_xrp_balance": drops_to_xrp(acc.get("Balance", 0)),
        "freeze_capability": has_freeze,
        "no_freeze_flag": has_nofreeze,
        "risk_score": score,
        "risk_grade": risk_grade(score),
        "timestamp": ts(),
        "source": "XRPL Cluster"
    }

async def handle_escrow_monitor(args):
    """XRPL escrow intelligence: locked XRP, conditions, expiry"""
    address = args.get("address", "").strip()
    if not address:
        return {"error": "address required"}

    escrows = await xrpl("account_escrows", {"account": address, "ledger_index": "validated"})
    escrow_list = escrows.get("account_escrows", []) if isinstance(escrows, dict) else []

    total_locked = 0
    details = []
    for e in escrow_list[:20]:
        amt = drops_to_xrp(e.get("Amount", 0))
        total_locked += amt
        details.append({
            "sequence": e.get("Sequence"),
            "amount_xrp": amt,
            "destination": e.get("Destination"),
            "finish_after": e.get("FinishAfter"),
            "cancel_after": e.get("CancelAfter"),
            "has_condition": bool(e.get("Condition"))
        })

    price_data = await get(f"{CG}/simple/price", {"ids": "ripple", "vs_currencies": "usd"})
    xrp_usd = price_data.get("ripple", {}).get("usd", 0) if isinstance(price_data, dict) else 0

    return {
        "address": address,
        "active_escrows": len(escrow_list),
        "total_locked_xrp": round(total_locked, 6),
        "total_locked_usd": round(total_locked * xrp_usd, 2),
        "escrows": details,
        "timestamp": ts(),
        "source": "XRPL Cluster"
    }



def build_server():
    server = WhitelabelMCPServer(
        product_name=PRODUCT_NAME,
        product_slug="xrploracle",
        version=VERSION,
        port_mcp=PORT_MCP,
        port_health=PORT_HEALTH,
    )
    server.register_tool("xrpl_overview",
        "XRPL network overview: XRP price, ledger stats, reserve requirements, base fee",
        {"type": "object", "properties": {}, "required": []}, handle_overview)
    server.register_tool("xrpl_rlusd",
        "RLUSD stablecoin compliance and risk intelligence: peg health, supply, NYDFS compliance",
        {"type": "object", "properties": {}, "required": []}, handle_rlusd)
    server.register_tool("xrpl_account_intel",
        "XRPL account intelligence: XRP balance, trust lines, open offers, escrows, flags",
        {"type": "object", "properties": {"address": {"type": "string", "description": "XRPL classic address (r...)"}}, "required": ["address"]}, handle_account_intel)
    server.register_tool("xrpl_dex_orderbook",
        "XRPL native DEX order book: bids/asks for any currency pair",
        {"type": "object", "properties": {"base_currency": {"type": "string", "default": "XRP"}, "base_issuer": {"type": "string", "default": ""}, "quote_currency": {"type": "string", "default": "RLUSD"}, "quote_issuer": {"type": "string", "default": ""}, "limit": {"type": "integer", "default": 10}}, "required": []}, handle_dex_orderbook)
    server.register_tool("xrpl_amm_pools",
        "XRPL AMM liquidity pool intelligence: reserves, trading fee, LP token supply",
        {"type": "object", "properties": {"asset": {"type": "string", "default": "RLUSD"}, "asset2": {"type": "string", "default": "XRP"}}, "required": []}, handle_amm_pools)
    server.register_tool("xrpl_payment_intel",
        "XRPL cross-border payment intelligence: routing, ODL, settlement speed, cost",
        {"type": "object", "properties": {"amount_xrp": {"type": "number", "default": 1000}, "from_currency": {"type": "string", "default": "USD"}, "to_currency": {"type": "string", "default": "EUR"}}, "required": []}, handle_payment_intel)
    server.register_tool("xrpl_token_check",
        "XRPL issued currency risk check: issuer trust, supply, freeze capability, compliance",
        {"type": "object", "properties": {"currency": {"type": "string"}, "issuer": {"type": "string"}}, "required": []}, handle_token_check)
    server.register_tool("xrpl_escrow_monitor",
        "XRPL escrow intelligence: locked XRP amounts, conditions, expiry, total value",
        {"type": "object", "properties": {"address": {"type": "string"}}, "required": ["address"]}, handle_escrow_monitor)
    return server

if __name__ == "__main__":
    srv = build_server()
    srv.run()
