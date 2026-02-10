---
description: Calculate position size and risk management parameters
---

# ClawBot Risk Skill

## Purpose
Calculate optimal position size based on account balance tier and AI confidence. Provides risk config to AI for decision making.

## Risk Tiers (Dynamic by Balance)

| Balance | Risk/Trade | Example |
|---------|-----------|---------|
| <$50 | 20% | $50 → $10 margin |
| $50-100 | 10% | $100 → $10 margin |
| $100-300 | 7% | $200 → $14 margin |
| $300-1000 | 4% | $500 → $20 margin |
| >$1000 | 2.5% | $2000 → $50 margin |

## Usage
```python
from src.utils.config import settings

risk_pct = settings.get_risk_pct(balance=150)  # Returns 7.0
margin = balance * (risk_pct / 100)  # $150 × 7% = $10.50
notional = margin * settings.LEVERAGE  # $10.50 × 20 = $210
```

## Rules
- AI decides final margin within the suggested range
- No daily loss limit — AI manages risk per trade
- After multiple losses: AI assesses whether to continue
- Min order: 5 USDT (configurable)
- Counter-trend trades require higher confidence
