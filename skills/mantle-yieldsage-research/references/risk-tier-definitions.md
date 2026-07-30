# Risk Tier Definitions

YieldSage classifies every tracked Solana DeFi pool into one of three risk tiers.
Use these definitions when explaining or filtering recommendations.

---

## stable

**What it means:** Low-volatility pools composed entirely of dollar-pegged assets or
highly liquid stablecoin pairs. Price risk is minimal; the primary remaining risk is
smart-contract risk.

**Asset composition examples:**
- USDC / USDT
- USDC / DAI
- USDT / USDT0
- cmETH / mETH (stable liquid staking pair)

**Auto-detected by:** YieldSage checks whether the pool asset name contains `usd` or
`dai` (case-insensitive). The AI scorer may promote or demote the initial classification
based on TVL depth and APY stability.

**Typical APY range:** 3 % – 25 %

**User profile:** Capital-preservation focused. Suitable for users who want predictable
yield without significant impermanent loss or price exposure.

---

## moderate

**What it means:** Pools with a mix of blue-chip assets where one leg may fluctuate
against the other, or native-token staking strategies. Impermanent loss is possible
but bounded by asset correlation.

**Asset composition examples:**
- SOL / USDC
- JitoSOL / USDC
- mSOL staking (single-asset)
- WBTC / USDT

**Typical APY range:** 8 % – 60 %

**User profile:** Yield-growth focused. Suitable for users comfortable with moderate
price exposure and some impermanent loss in exchange for higher returns.

---

## aggressive

**What it means:** Pools with high-volatility or low-liquidity assets where price
divergence, IL, and liquidity risk are all materially elevated. APY figures can be
large but fluctuate rapidly.

**Asset composition examples:**
- New or low-TVL token pairs
- Long-tail asset / stablecoin pairs
- Concentrated liquidity positions in volatile ranges

**Typical APY range:** 20 % – 500 %+

**User profile:** Risk-tolerant. Suitable for users actively managing positions and
willing to accept potential principal loss in exchange for outsized returns.

---

## AI Override

The YieldSage AI scorer reads the initial auto-detected tag and may override it in either
direction based on:

- **TVL depth**: A pool with `usd` in the name but < $50 k TVL may be reclassified to
  `moderate` due to liquidity risk.
- **APY anomalies**: An unusually high APY spike on a stable pair triggers a `moderate`
  override with a warning note in `ai_reasoning`.
- **Reward token risk**: If the reward APY component is paid in a low-liquidity token,
  the effective risk tier is raised.

The `ai_reasoning` field in each recommendation always explains any override decision.

---

## Usage in this Skill

When filtering `/api/yields/leaderboard` or `/api/recommendations/latest`:

- Pass `risk_tag=stable` for capital-preservation requests
- Pass `risk_tag=moderate` for balanced yield/risk requests
- Pass `risk_tag=aggressive` for maximum-yield requests
- Omit `risk_tag` to return all tiers grouped in output
