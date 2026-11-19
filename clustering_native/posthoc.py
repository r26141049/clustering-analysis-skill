"""Stage 5 descriptive, post-clustering comparisons of archived source observations.

Never changes feature selection, weights, final labels, or approval-bound results.
Supplementary features are only disclosed after an independent Stage 1 role gate.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _num(s):
    return pd.to_numeric(s, errors='coerce').replace([np.inf,-np.inf],np.nan)


def _label(group):
    return '雜訊' if int(group)==-1 else f'第 {int(group)+1} 群'


def _summary(s):
    a=_num(s).dropna()
    if len(a)==0:
        return 'NA'
    return (f'平均 {a.mean():.3g}；中位數 {a.median():.3g}；'
            f'SD {a.std(ddof=1):.3g}；Q1–Q3 {a.quantile(.25):.3g}–{a.quantile(.75):.3g}'
            f'（有效 {len(a)}）')


def render_numeric_comparisons(raw, labels, clustering_cols, supplementary_cols=()):
    """Compare actual groups using source units; never imply independent validation."""
    if labels is None:
        return ''
    labels=np.asarray(labels)
    if len(raw)!=len(labels):
        raise ValueError('Archived raw observations and approved labels are misaligned')
    selected=[c for c in clustering_cols if c in raw and pd.api.types.is_numeric_dtype(raw[c])]
    extra=[c for c in supplementary_cols if c in raw and pd.api.types.is_numeric_dtype(raw[c])]
    columns=list(dict.fromkeys(extra+selected))[:24]
    if not columns:
        return ''
    text=['### 真實數值特徵的群間比較（原始單位）','',
          '以下直接以已核准的分群標籤與封存的原始觀測計算，沒有重新擬合模型。'
          '群數為分群結果，差異為描述統計，不表示因果或顯著性。','']
    for col in columns:
        role=('事後分析變數（**未參與分群**）' if col in extra else
              '分群特徵（**已參與分群**，不應視為獨立新發現）')
        text += [f'#### `{col}`：{role}','',
                 '| 群組 | 人數 | 平均數 | 中位數 | 標準差 | Q1 | Q3 | 有效筆數 |',
                 '|---|---:|---:|---:|---:|---:|---:|---:|']
        numeric=_num(raw[col])
        means=[]
        for g in sorted(set(labels)):
            a=numeric[labels==g].dropna(); n=int(np.sum(labels==g))
            fmt=lambda v:'NA' if pd.isna(v) else f'{float(v):.3g}'
            text.append(f'| {_label(g)} | {n} | {fmt(a.mean())} | {fmt(a.median())} | '
                        f'{fmt(a.std(ddof=1))} | {fmt(a.quantile(.25))} | '
                        f'{fmt(a.quantile(.75))} | {len(a)} |')
            if len(a): means.append((int(g),float(a.mean()),len(a)))
        text.append('')
        if len(means)>1:
            top=max(means,key=lambda a:a[1]);low=min(means,key=lambda a:a[1])
            text.append(f'**觀察到的差異：** {_label(top[0])}的平均值最高（{top[1]:.3g}），'
                        f'{_label(low[0])}最低（{low[1]:.3g}），差距 {top[1]-low[1]:.3g} 原始單位。'
                        '應同時比較組內變異和樣本數；未進行顯著性檢定。')
            text.append('')
    return '\n'.join(text)+'\n'


def supplementary_exploration(raw, labels, supplementary_cols, association_pairs=()):
    """User-declared follow-up roles and pairs only: no fixed domain assumptions."""
    labels=np.asarray(labels)
    if len(labels)!=len(raw):
        raise ValueError('Supplementary analysis row alignment failed')
    text=['### 事後分析與研究目的對照','',
          '以下變數未參與候選 K、距離、Medoid 或選群品質評估。'
          '事後觀察可提供外部描述線索，但仍不證明自然群或因果關係。','']
    for col in supplementary_cols:
        if col not in raw: raise ValueError(f'Missing approved supplementary variable {col}')
        if pd.api.types.is_numeric_dtype(raw[col]): continue
        text += [f'**`{col}` 群間類別組合（最多列出每群前三個實際類別）：**','',
                 '| 群組 | 非缺失筆數 | 主要類別與群內比例 |','|---|---:|---|']
        for g in sorted(set(labels)):
            s=raw.loc[labels==g,col]
            counts=s.value_counts(dropna=True).head(3)
            composition='；'.join(f'{v}: {int(n)}/{len(s)} ({n/len(s):.1%})' for v,n in counts.items()) or '無有效類別'
            text.append(f'| {_label(g)} | {s.count()} | {composition} |')
        text.append('')
    if association_pairs:
        from scipy.stats import spearmanr
        text += ['#### 事前指明的探索性變數關聯','',
                 'Spearman 係數以原始觀測逐對完整值計算；只有相關性，不代表因果關係。', '',
                 '| 變數 A | 變數 B | 完整觀測筆數 | Spearman ρ | 判讀 |',
                 '|---|---|---:|---:|---|']
        for a,b in association_pairs:
            if a not in raw or b not in raw: raise ValueError('Association pair contains absent feature')
            x,y=_num(raw[a]),_num(raw[b]);v=x.notna() & y.notna()
            if int(v.sum())<5 or x[v].nunique()<2 or y[v].nunique()<2:
                rho=None
            else:
                rho=float(spearmanr(x[v],y[v]).statistic)
                if not np.isfinite(rho):rho=None
            label=('無法可靠估計（不足 5 筆或變異不足）' if rho is None else
                   '正相關' if rho>0 else '負相關' if rho<0 else '近零相關')
            text.append(f'| `{a}` | `{b}` | {int(v.sum())} | '
                        f'{"NA" if rho is None else f"{rho:.3f}"} | {label} |')
        text += ['', '關聯分析屬探索性補充，不提供調整共變數後的因果效果；若需額外統計模型，應另定研究問題及授權。','']
    return '\n'.join(text)+'\n'
