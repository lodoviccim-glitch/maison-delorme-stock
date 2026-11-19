"""Maison Delorme VFINAL pilot: transparent forecast-driven purchase order proposals.

No supplier orders are transmitted. All quantities are proposals for human validation.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil, sqrt
from statistics import NormalDist
import calendar
import numpy as np
import pandas as pd

MONTHS = ['Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep'] * 2


def _forecast(history: np.ndarray, horizon_months: int = 8):
    """Choose simple baseline via rolling-origin MAE (12 test months)."""
    history = np.asarray(history, dtype=float)
    if history.size != 24 or not np.isfinite(history).all() or (history < 0).any():
        raise ValueError('24 monthly demand values >= 0 required')

    def predict(a, method):
        if method == 'Recent 3-month mean':
            return float(np.mean(a[-min(3, len(a)):]))
        if method == '12-month seasonal naive':
            return float(a[-12]) if len(a) >= 12 else float(np.mean(a[-3:]))
        if method == '6-month moving average':
            return float(np.mean(a[-min(6, len(a)):]))
        raise ValueError(method)

    methods = ['Recent 3-month mean', '6-month moving average', '12-month seasonal naive']
    errors = {}
    for method in methods:
        diffs = [abs(history[i] - predict(history[:i], method)) for i in range(12,24)]
        errors[method] = float(np.mean(diffs))
    best = min(methods, key=lambda method: (errors[method], methods.index(method)))
    if best == '12-month seasonal naive':
        forecast = [float(history[-12 + (j % 12)]) for j in range(horizon_months)]
    else:
        a = list(history)
        forecast = []
        for _ in range(horizon_months):
            p = predict(np.asarray(a), best)
            forecast.append(p)
            a.append(p)
    # Conservative empirical one-step forecast uncertainty (not a confidence guarantee)
    residuals = np.asarray([history[i] - predict(history[:i], best) for i in range(12,24)])
    residual_sd = float(np.std(residuals, ddof=1)) if len(residuals)>1 else 0.0
    return best, np.asarray(forecast), errors[best], residual_sd


def _month_shift(year, month, offset):
    idx = year*12 + month-1 + offset
    return idx//12, idx%12+1


def _daily_forecast(start: date, months: np.ndarray):
    """Oct 2026 is the first future month after the source's Sep 2026 history."""
    result = {}
    for j, qty in enumerate(months):
        year, month = _month_shift(2026, 10, j)
        days = calendar.monthrange(year, month)[1]
        for day in range(1, days+1):
            dt = date(year,month,day)
            if dt >= start:
                result[dt] = float(qty)/days
    return result


def _num(row, name, fallback=None):
    value = row.get(name, None)
    if value is None or pd.isna(value) or str(value).strip() == '':
        return fallback
    try:
        n=float(value)
        return n if np.isfinite(n) else fallback
    except (TypeError,ValueError):
        return fallback


def generate_plan(products: pd.DataFrame, demand: pd.DataFrame, *,
                  as_of: date = date(2026,10,1), weeks: int = 12,
                  service_target: float = 0.95, review_days: int = 7,
                  use_current_stock: bool = True):
    """Forecast demand then project stock and generate dated proposals.

    Uses weekly review/order-up-to, daily forecast, deterministic lead times.
    No existing inbound POs are provided: assumes zero. No MOQ/pack constraints.
    Starting snapshot 2026-10-01, aligned with demand ending Sep 2026.
    """
    if not (date(2026,10,1) <= as_of <= date(2027,3,31)):
        raise ValueError('Select a planning date between 2026-10-01 and 2027-03-31 for this dataset.')
    if not (0.5 < service_target < 1):
        raise ValueError('Service target must be between 50% and 100%.')
    if weeks < 1 or weeks > 24 or review_days < 1:
        raise ValueError('Invalid planning horizon or review interval.')
    z=NormalDist().inv_cdf(service_target)
    daily_by_sku = {}
    details=[]
    proposals=[]
    demand_ids = demand.iloc[:,0].astype(str).str.strip()
    demand_values = demand.iloc[:,3:27].apply(pd.to_numeric,errors='coerce')
    if demand_ids.duplicated().any():
        raise ValueError('Duplicate SKUs in demand table')
    demand_lookup = {sku: demand_values.iloc[i].to_numpy(dtype=float) for i,sku in enumerate(demand_ids)}
    if products['SKU'].astype(str).str.strip().duplicated().any():
        raise ValueError('Duplicate SKUs in product table')
    for _, row in products.iterrows():
        sku=str(row['SKU']).strip()
        if sku not in demand_lookup:
            raise ValueError(f'Missing demand history for {sku}')
        history=demand_lookup[sku]
        method, fc, mae, sd = _forecast(history,8)
        daily=_daily_forecast(as_of,fc)
        lead_weeks=_num(row,'Lead time weeks')
        if lead_weeks is None or lead_weeks < 0:
            raise ValueError(f'Invalid lead time for {sku}')
        lead_days=max(1,ceil(lead_weeks*7))
        stock_field='Quantity_On_Hand' if use_current_stock else 'Initial Stock'
        stock=_num(row,stock_field)
        if stock is None or stock<0:
            raise ValueError(f'Invalid {stock_field} for {sku}')
        unit_cost=_num(row,'Unit cost',0.0)
        if unit_cost is None or unit_cost<0:
            raise ValueError(f'Invalid unit cost for {sku}')
        stock=float(stock)
        arrivals={}
        first_order=None
        projected_min=stock
        lost_units=0.0
        first_risk=None
        end=as_of+timedelta(days=weeks*7)
        for i in range((end-as_of).days):
            day=as_of+timedelta(days=i)
            stock+=arrivals.pop(day,0.0)
            day_demand=daily.get(day,0.0)
            supplied=min(stock,day_demand)
            lost_units+=max(0.0,day_demand-supplied)
            stock-=supplied
            projected_min=min(projected_min,stock)
            if supplied+1e-9 < day_demand and first_risk is None:
                first_risk=day
            if i % review_days != 0:
                continue
            # Protection period = lead time + time until next review
            protection_days=lead_days+review_days
            window=[day+timedelta(days=k) for k in range(protection_days)]
            expected=sum(daily.get(x,0.0) for x in window)
            # Scale historical monthly forecast errors into day-scale uncertainty
            # Simplification: sqrt of days/30; uncertainty may be autocorrelated.
            safety=z*(sd/sqrt(30.0))*sqrt(protection_days)
            target=ceil(expected+safety)
            pipeline=sum(q for arrival,q in arrivals.items() if arrival>=day)
            position=stock+pipeline
            qty=max(0,ceil(target-position))
            if qty>0:
                delivery=day+timedelta(days=lead_days)
                arrivals[delivery]=arrivals.get(delivery,0)+qty
                proposals.append({
                    'SKU':sku,'Product':str(row.get('Name','')),
                    'Supplier':str(row.get('Supplier Name','')),
                    'Order date':day.isoformat(), 'Expected delivery':delivery.isoformat(),
                    'Quantity (bottles)':qty,'Unit cost (USD)':round(unit_cost,2),
                    'Purchase value (USD)':round(qty*unit_cost,2),
                    'Service target (%)':round(service_target*100,1),
                    'Forecast model':method,'Order-up-to target':target,
                    'Safety stock (approx.)':ceil(safety),
                    'Status':'PROPOSAL - NOT SENT',
                })
                if first_order is None: first_order=(day,qty)
        details.append({
            'SKU':sku,'Product':str(row.get('Name','')),
            'Forecast model':method,'Backtest MAE (bottles/month)':round(mae,1),
            'Next 30d forecast (bottles)':round(sum(daily.get(as_of+timedelta(days=k),0) for k in range(30))),
            'Starting stock (bottles)':round(float(_num(row,stock_field)),1),
            'Lead time (days)':lead_days,'Forecast stockout risk':first_risk.isoformat() if first_risk else 'None in horizon',
            'Projected lost sales (bottles)':round(lost_units,1),
            'First suggested order':first_order[0].isoformat() if first_order else 'None',
            'First order quantity':first_order[1] if first_order else 0,
            'ABC':str(row.get('ABC','')).strip(),
        })
    orders=pd.DataFrame(proposals)
    if not orders.empty:
        orders=orders.sort_values(['Order date','SKU']).reset_index(drop=True)
    return pd.DataFrame(details), orders
