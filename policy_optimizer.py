"""Maison Delorme: forecast-driven ROP vs periodic review comparison.

Offline planning scenarios only. No supplier orders are sent.
Assumptions: deterministic lead times, no inbound POs, no MOQ/case packs,
forecast mean demand and backtest-derived daily uncertainty. Policies are
ranked by simulated fill rate then average stock; this is NOT cost optimality.
"""
from __future__ import annotations
from datetime import date, timedelta
from math import ceil, sqrt
from statistics import NormalDist
import numpy as np
import pandas as pd
from replenishment_engine import _forecast, _daily_forecast, _num


def _simulate(daily, start, days, stock0, lead_days, policy, *, q=0, rop=0, review=7, target=0):
    stock=float(stock0)
    arrivals={}
    rows=[]
    orders=[]
    requested=served=lost=0.0
    for i in range(days):
        day=start+timedelta(days=i)
        stock+=arrivals.pop(day,0)
        demand=float(daily.get(day,0))
        fulfilled=min(stock,demand)
        stock-=fulfilled
        requested+=demand; served+=fulfilled; lost+=demand-fulfilled
        position=stock+sum(arrivals.values())
        amount=0
        if policy=='ROP' and position <= rop:
            # Fixed quantity; repeated daily checks, one order per crossing.
            amount=int(q)
        elif policy=='Periodic Review' and i % review == 0:
            amount=max(0,ceil(target-position))
        if amount>0:
            delivery=day+timedelta(days=lead_days)
            arrivals[delivery]=arrivals.get(delivery,0)+amount
            orders.append((day,delivery,amount))
        rows.append((day,stock,demand,fulfilled))
    return {
        'fill_rate':100*served/requested if requested>0 else 100.,
        'lost':lost,
        'avg_stock':float(np.mean([r[1] for r in rows])),
        'orders':orders,
        'rows':rows,
    }


def _candidates(avg_daily, sd_month, lead_days, review, z):
    # Baseline is computed from expected lead-time demand and an approximate
    # standard deviation. Monthly residuals do not imply independent daily errors.
    sd_daily=sd_month/sqrt(30)
    lead_demand=avg_daily*lead_days
    rop_base=lead_demand+z*sd_daily*sqrt(lead_days)
    q_base=max(1,round(avg_daily*14))
    qs=sorted(set(max(1,round(q_base*m)) for m in (0.5,1,1.5,2,3)))
    rops=sorted(set(max(0,ceil(rop_base*m)) for m in (0.65,0.85,1,1.2,1.5)))
    targets=[]
    for r in (review, max(1,review*2), max(1,review//2)):
        protection=lead_days+r
        base=avg_daily*protection+z*sd_daily*sqrt(protection)
        for factor in (0.85,1,1.2,1.5):
            targets.append((r,max(1,ceil(base*factor))))
    return [(q,rop) for q in qs for rop in rops], sorted(set(targets))


def compare_and_plan(products:pd.DataFrame, demand:pd.DataFrame, *,
                     as_of:date=date(2026,10,1), weeks:int=12,
                     service_target:float=0.95, review_days:int=7):
    """Return (comparison, selected_policy_by_sku, purchase_proposals).

    Evaluation uses forecast demand (not realized demand): results are scenario
    estimates, not validated future service levels. Stock snapshots must be dated
    to as_of. Baseline historical snapshot is assumed 2026-10-01.
    """
    if not date(2026,10,1)<=as_of<=date(2027,3,31):
        raise ValueError('Planning date must be from 2026-10-01 through 2027-03-31.')
    if not 0.5<service_target<1 or not 1<=weeks<=24 or review_days<1:
        raise ValueError('Invalid service target, horizon or review interval.')
    z=NormalDist().inv_cdf(service_target)
    ids=demand.iloc[:,0].astype(str).str.strip()
    if ids.duplicated().any(): raise ValueError('Duplicate demand SKUs.')
    history_map={sku:pd.to_numeric(demand.iloc[i,3:27],errors='coerce').to_numpy(dtype=float) for i,sku in enumerate(ids)}
    if products['SKU'].astype(str).str.strip().duplicated().any(): raise ValueError('Duplicate product SKUs.')
    comparisons=[]; selected=[]; proposed=[]
    for _,row in products.iterrows():
        sku=str(row['SKU']).strip()
        if sku not in history_map: raise ValueError(f'Missing history for {sku}.')
        model, forecast, mae, sd=_forecast(history_map[sku],8)
        daily=_daily_forecast(as_of,forecast)
        stock=_num(row,'Quantity_On_Hand')
        lead=_num(row,'Lead time weeks')
        unit_cost=_num(row,'Unit cost',0)
        if stock is None or stock<0 or lead is None or lead<0 or unit_cost is None or unit_cost<0:
            raise ValueError(f'Invalid stock, lead time or unit cost for {sku}.')
        lead_days=max(1,ceil(lead*7))
        days=weeks*7
        avg_daily=float(np.mean([daily.get(as_of+timedelta(days=k),0) for k in range(days)]))
        rop_grid,periodic_grid=_candidates(avg_daily,sd,lead_days,review_days,z)
        candidates=[]
        for q,rop in rop_grid:
            res=_simulate(daily,as_of,days,stock,lead_days,'ROP',q=q,rop=rop)
            candidates.append(('ROP',q,rop,0,0,res))
        for r,s in periodic_grid:
            res=_simulate(daily,as_of,days,stock,lead_days,'Periodic Review',review=r,target=s)
            candidates.append(('Periodic Review',0,0,r,s,res))
        best_by_policy={}
        for policy in ('ROP','Periodic Review'):
            group=[c for c in candidates if c[0]==policy]
            eligible=[c for c in group if c[5]['fill_rate']+1e-8>=service_target*100]
            pool=eligible if eligible else group
            best=min(pool,key=lambda c:(c[5]['avg_stock'],-c[5]['fill_rate'],len(c[5]['orders']))) if eligible else min(pool,key=lambda c:(-c[5]['fill_rate'],c[5]['avg_stock'],len(c[5]['orders'])))
            best_by_policy[policy]=best
            comparisons.append({
                'SKU':sku,'Product':str(row.get('Name','')),'Policy':policy,
                'Forecast model':model,'Backtest MAE (monthly bottles)':round(mae,1),
                'Forecast fill rate (%)':round(best[5]['fill_rate'],2),
                'Forecast lost sales (bottles)':round(best[5]['lost'],1),
                'Average stock (bottles)':round(best[5]['avg_stock'],1),
                'Average inventory value (USD)':round(best[5]['avg_stock']*unit_cost,2),
                'Orders':len(best[5]['orders']),
                'Meets target':best[5]['fill_rate']+1e-8>=service_target*100,
                'Q':best[1] if policy=='ROP' else None,
                'ROP':best[2] if policy=='ROP' else None,
                'R (days)':best[3] if policy=='Periodic Review' else None,
                'S':best[4] if policy=='Periodic Review' else None,
            })
        winners=list(best_by_policy.values())
        eligible=[c for c in winners if c[5]['fill_rate']+1e-8>=service_target*100]
        if eligible:
            chosen=min(eligible,key=lambda c:(c[5]['avg_stock'],len(c[5]['orders'])))
            reason='Target met; lowest average inventory among eligible policies'
        else:
            chosen=min(winners,key=lambda c:(-c[5]['fill_rate'],c[5]['avg_stock']))
            reason='Neither meets target; highest forecast fill rate (review required)'
        policy,q,rop,r,s,res=chosen
        selected.append({'SKU':sku,'Product':str(row.get('Name','')),'Selected policy':policy,
                         'Forecast fill rate (%)':round(res['fill_rate'],2),
                         'Average stock (bottles)':round(res['avg_stock'],1),
                         'Meets target':res['fill_rate']+1e-8>=service_target*100,
                         'Q':q if policy=='ROP' else None,'ROP':rop if policy=='ROP' else None,
                         'R (days)':r if policy=='Periodic Review' else None,
                         'S':s if policy=='Periodic Review' else None,
                         'Selection rationale':reason})
        for order_date,delivery,qty in res['orders']:
            proposed.append({'SKU':sku,'Product':str(row.get('Name','')),
                             'Supplier':str(row.get('Supplier Name','')),
                             'Selected policy':policy,'Order date':order_date.isoformat(),
                             'Expected delivery':delivery.isoformat(),
                             'Quantity (bottles)':qty,'Purchase value (USD)':round(qty*unit_cost,2),
                             'Status':'PROPOSAL - NOT SENT'})
    orders=pd.DataFrame(proposed,columns=['SKU','Product','Supplier','Selected policy','Order date','Expected delivery','Quantity (bottles)','Purchase value (USD)','Status'])
    if not orders.empty: orders=orders.sort_values(['Order date','SKU']).reset_index(drop=True)
    return pd.DataFrame(comparisons),pd.DataFrame(selected),orders
