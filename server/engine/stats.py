import numpy as np
import pandas as pd
import statsmodels.tsa.stattools as ts
from typing import Tuple, Optional

def compute_pair_stats(a: list, b: list) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    if len(a) < 60 or len(b) < 60:
        return None, None, None, None, None, None

    a_arr = np.array(a)
    b_arr = np.array(b)

    # 1. Correlation
    corr = np.corrcoef(a_arr, b_arr)[0, 1]
    if pd.isna(corr): corr = None

    # 2. Hedge Ratio (Beta)
    cov_matrix = np.cov(b_arr, a_arr)
    var_b = cov_matrix[0, 0]
    beta = cov_matrix[0, 1] / var_b if var_b != 0 else None
    if beta is not None and pd.isna(beta): beta = None

    if beta is None:
        return float(corr) if corr is not None else None, None, None, None, None, None

    # 3. Spread
    spreads = a_arr - beta * b_arr

    # 4. Half Life (OU Process)
    lag = spreads[:-1]
    delta = spreads[1:] - lag
    dev_lag = lag - np.mean(lag)
    var_lag = np.var(dev_lag, ddof=0)
    
    hl = None
    if var_lag != 0:
        cov_delta_lag = np.cov(dev_lag, delta, ddof=0)[0, 1]
        lambda_val = cov_delta_lag / var_lag
        if lambda_val < 0 and not pd.isna(lambda_val):
            hl = -np.log(2) / lambda_val

    # 5. Hurst Exponent
    def calculate_hurst(series):
        if len(series) < 20: return None
        m = np.mean(series)
        dev = series - m
        cum_dev = np.cumsum(dev)
        range_val = np.max(cum_dev) - np.min(cum_dev)
        std_val = np.std(series, ddof=0)
        if std_val == 0 or range_val == 0: return None
        res = np.log(range_val / std_val) / np.log(len(series))
        return float(res) if not pd.isna(res) else None

    hurst = calculate_hurst(spreads)

    # 6. Z-Score (60 period)
    recent = spreads[-60:]
    mean_val = np.mean(recent)
    std_val = np.std(recent, ddof=0)
    zscore = (spreads[-1] - mean_val) / std_val if std_val != 0 else None

    # 7. Cointegration (ADF)
    p_value = None
    try:
        res = ts.adfuller(spreads, maxlag=1, autolag=None)
        p_value = float(res[1]) if not pd.isna(res[1]) else None
    except:
        pass

    return corr, beta, hl, hurst, zscore, p_value

def classify_zone(z: float, config: dict) -> dict:
    abs_z = abs(z)
    entry = config.get('zscore_entry', 2.0)
    sl = config.get('zscore_sl', 3.5)
    buffer = config.get('safe_buffer', 0.2)

    zone = "neutral"
    can_open = False
    size_pct = 0

    if abs_z >= sl:
        zone = "danger"
    elif abs_z >= entry:
        zone = "safe"
        can_open = True
        size_pct = 1.0 # 100% of allocated
    elif abs_z >= entry - buffer:
        zone = "caution"
        can_open = True
        size_pct = 0.5 # 50%
    
    return {"zone": zone, "can_open": can_open, "size_pct": size_pct}
