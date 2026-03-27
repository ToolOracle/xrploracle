# ◈ xrplOracle

**XRP Ledger Intelligence MCP Server** — 8 tools | Part of [ToolOracle](https://tooloracle.io)

![Tools](https://img.shields.io/badge/MCP_Tools-8-10B898?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-00C853?style=flat-square)
![Chain](https://img.shields.io/badge/Chain-XRPL-0085C0?style=flat-square)
![Tier](https://img.shields.io/badge/Tier-Free-2196F3?style=flat-square)

RLUSD compliance, payment/settlement intelligence, AMM liquidity, tokenized assets, issuer trust analysis, native DEX order book, escrow monitoring. Evidence-grade data for programmable money and regulated tokenization on XRPL.

## Quick Connect

```bash
npx -y mcp-remote https://feedoracle.io/mcp/xrploracle/
```

```json
{
  "mcpServers": {
    "xrploracle": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://feedoracle.io/mcp/xrploracle/"]
    }
  }
}
```

## Tools (8)

| Tool | Description |
|------|-------------|
| `xrpl_overview` | XRPL network overview: XRP price, ledger stats, reserve requirements, base fee |
| `xrpl_rlusd` | RLUSD stablecoin compliance: peg health (STABLE ✓), supply, NYDFS regulation |
| `xrpl_account_intel` | Account intelligence: XRP balance, trust lines, offers, escrows, flags |
| `xrpl_dex_orderbook` | Native DEX order book: bids/asks for any currency pair on-chain |
| `xrpl_amm_pools` | AMM liquidity pools: reserves, trading fee, LP token supply |
| `xrpl_payment_intel` | Cross-border payment: ODL routing, 3-5s settlement, cost analysis |
| `xrpl_token_check` | Issued currency risk: issuer trust, supply, freeze capability, compliance |
| `xrpl_escrow_monitor` | Escrow intelligence: locked XRP amounts, conditions, expiry, total value |

## Highlight: RLUSD Compliance

RLUSD (Ripple's USD stablecoin) is monitored in real-time:
- **Peg status**: STABLE (deviation < 0.5%)
- **Risk grade**: A
- **Regulator**: NYDFS (New York Department of Financial Services)
- **Compliance**: KYC required, blacklist/freeze capability

## Part of FeedOracle / ToolOracle

**Blockchain Oracle Suite:**
- [ethOracle](https://github.com/tooloracle/ethoracle) — Ethereum
- [xlmOracle](https://github.com/tooloracle/xlmoracle) — Stellar
- [xrplOracle](https://github.com/tooloracle/xrploracle) — XRP Ledger (this repo)
- [bnbOracle](https://github.com/tooloracle/bnboracle) — BNB Chain
- [aptOracle](https://github.com/tooloracle/aptoracle) — Aptos
- [baseOracle](https://github.com/tooloracle/baseoracle) — Base L2

## Links

- 🌐 Live: `https://feedoracle.io/mcp/xrploracle/`
- 🏠 Platform: [feedoracle.io](https://feedoracle.io)

---
*Built by [FeedOracle](https://feedoracle.io) — Evidence by Design*
