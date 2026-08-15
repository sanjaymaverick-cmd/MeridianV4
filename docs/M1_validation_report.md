# M1 Validation Report – Meridian V4 Meta Labels
**Generated:** 2026-08-15T11:13:17.927557+00:00

## Summary
- Total rows: **199**
- Clean rows (non-futures, valid price/ATR): **157**
- Futures rows: 42 (contaminated: 42)
- Short holds (<120s): 173
- Quality holds (≥300s): 16

## Clean Subset Metrics (primary training set)
- Win rate: **0.6%**
- Avg honest PnL: ₹-8.70
- Median hold: 60.1s
- ATR coverage (full set): 100.0%

## Hold Buckets
```
{
  "1-2m": 162,
  ">15m": 16,
  "<1m": 11,
  "2-5m": 10
}
```

## Top Symbols
```
{
  "INFY.F": 34,
  "BHARTIARTL": 17,
  "HCLTECH": 17,
  "BNBUSDT": 17,
  "M&M": 16,
  "BAJAJFINSV": 16,
  "GRASIM": 16,
  "INFY": 14,
  "NESTLEIND": 12,
  "BRITANNIA": 10
}
```

## Notes for M2 (mlfinlab)
- Use `is_clean == 1` as the base filter before triple-barrier.
- `is_quality_hold` is the target regime we want to increase.
- Contaminated futures must stay excluded until mark pipeline is fixed.
- `feature_hash` enables exact reproducibility of decision-time features.

## Next
Proceed to M2 – full mlfinlab-style meta-label pipeline on the clean subset.