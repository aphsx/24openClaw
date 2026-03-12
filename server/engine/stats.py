import numpy as np
import pandas as pd
import statsmodels.tsa.stattools as ts
from typing import Tuple, Optional


def compute_pair_stats(
    a: list, b: list
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Returns: (correlation, beta, half_life, hurst, zscore, adf_pvalue)
    Any value may be None if it cannot be computed.
    """
    if len(a) < 60 or len(b) < 60:
        return None, None, None, None, None, None

    a_arr = np.array(a, dtype=float)
    b_arr = np.array(b, dtype=float)

    # 1. Pearson Correlation
    corr = float(np.corrcoef(a_arr, b_arr)[0, 1])
    if np.isnan(corr):
        return None, None, None, None, None, None

    # 2. Hedge Ratio beta via OLS: A = alpha + beta*B
    cov_mat = np.cov(b_arr, a_arr, ddof=1)
    var_b   = cov_mat[0, 0]
    if var_b == 0:
        return corr, None, None, None, None, None
    beta = float(cov_mat[0, 1] / var_b)
    if np.isnan(beta) or beta <= 0:
        return corr, None, None, None, None, None

    # 3. Spread
    spreads = a_arr - beta * b_arr

    # 4. Half-Life (Ornstein-Uhlenbeck)
    lag   = spreads[:-1]
    delta = spreads[1:] - lag
    dev   = lag - np.mean(lag)
    var_d = np.var(dev, ddof=0)

    hl = None
    if var_d > 0:
        cov_dl = np.cov(dev, delta, ddof=0)[0, 1]
        lam    = cov_dl / var_d
        if lam < 0 and not np.isnan(lam):
            hl = float(-np.log(2) / lam)

    # 5. Hurst Exponent via R/S analysis
    def hurst(series):
        if len(series) < 20:
            return None
        m     = np.mean(series)
        d     = series - m
        cum   = np.cumsum(d)
        r     = float(np.max(cum) - np.min(cum))
        s     = float(np.std(series, ddof=0))
        if s == 0 or r == 0:
            return None
        h = np.log(r / s) / np.log(len(series))
        return float(h) if not np.isnan(h) else None

    hurst_val = hurst(spreads)

    # 6. Z-Score (rolling 60-period)
    recent  = spreads[-60:]
    mean_60 = float(np.mean(recent))
    std_60  = float(np.std(recent, ddof=0))
    zscore  = float((spreads[-1] - mean_60) / std_60) if std_60 > 0 else None

    # 7. Cointegration via ADF test on spread
    pval = None
    try:
        adf_result = ts.adfuller(spreads, maxlag=1, autolag=None)
        raw_pval   = float(adf_result[1])
        pval       = raw_pval if not np.isnan(raw_pval) else None
    except Exception:
        pass

    return corr, beta, hl, hurst_val, zscore, pval


def classify_zone(z, config: dict) -> dict:
    """
    Classify a z-score into a trading zone.

    Zone logic (per guide):
      safe_max   = zscore_sl - safe_buffer
      caution_at = zscore_entry + 0.6 * (safe_max - zscore_entry)

      |z| < entry          -> neutral  (no signal)
      entry  <= |z| < caution_at -> safe    (100% size)
      caution_at <= |z| < safe_max -> caution (50% size)
      |z| >= safe_max      -> danger   (blocked)
    """
    if z is None:
        return {"zone": "neutral", "can_open": False, "size_pct": 0}

    abs_z   = abs(z)
    entry   = float(config.get('zscore_entry', 2.0))
    sl      = float(config.get('zscore_sl',    3.0))
    buffer  = float(config.get('safe_buffer',  0.5))

    safe_max   = sl - buffer
    caution_at = entry + 0.6 * (safe_max - entry)

    if safe_max <= entry:
        safe_max   = entry + 0.1
        caution_at = entry + 0.06

    if abs_z >= safe_max:
        return {"zone": "danger",   "can_open": False, "size_pct": 0}
    elif abs_z >= caution_at:
        return {"zone": "caution",  "can_open": True,  "size_pct": 0.5}
    elif abs_z >= entry:
        return {"zone": "safe",     "can_open": True,  "size_pct": 1.0}
    else:
        return {"zone": "neutral",  "can_open": False, "size_pct": 0}
