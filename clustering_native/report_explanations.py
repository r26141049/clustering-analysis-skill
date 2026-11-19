"""Observed-data explanations; no fitting, hidden ranking or causal claims."""
from __future__ import annotations
import numpy as np
import pandas as pd


def preprocessing_findings(raw: pd.DataFrame, model: pd.DataFrame, plan: dict) -> str:
    lines = ['### 前處理影響與資料品質', '',
             '以下比較實際封存的原始特徵與建模特徵。僅為資料診斷，不以統計顯著性證明處理正確。', '']
    lines += ['| 特徵 | 原始缺失 | 建模缺失 | 權重 | 其他觀察 |', '|---|---:|---:|---:|---|']
    for col in model.columns:
        source, fitted = raw[col], model[col]
        observations = []
        if source.isna().sum() > fitted.isna().sum():
            observations.append('有缺失值被填補；可能人為增加相似性')
        if pd.api.types.is_numeric_dtype(source):
            nums = pd.to_numeric(source, errors='coerce').dropna()
            if len(nums) >= 4:
                q1, q3 = nums.quantile([.25, .75]); iqr=q3-q1
                if iqr > 0 and np.max(np.abs(nums-np.median(nums))) > 30*iqr:
                    observations.append('有相對 IQR 極端值；可能影響距離尺度')
        else:
            classes = [str(v) for v in source.dropna().unique()]
            duplicates = {x.lower() for x in classes if sum(v.casefold()==x.casefold() for v in classes)>1}
            if duplicates: observations.append('類別大小寫不一致：'+', '.join(sorted(duplicates)))
        action = plan.get('actions', {}).get(col, {})
        if action:
            labels={'missing':'缺失處理','transform':'轉換','scale':'尺度','mapping':'類別正規化'}
            observations.append('；'.join(labels.get(key,key)+'：'+('已建立對照表' if key=='mapping' else str(value)) for key,value in action.items()))
        lines.append(f"| {col} | {int(source.isna().sum())} | {int(fitted.isna().sum())} | {plan['weights'].get(col, 1)} | {'；'.join(observations) or '無額外標記'} |")
    return '\n'.join(lines)+'\n\n'


def dominant_feature_findings(model: pd.DataFrame, labels, schema: dict) -> str:
    if labels is None:
        return '## 分群主導特徵檢查\n\n尚未批准正式分群，無法評估群組與單一特徵的對應程度。\n\n'
    groups = pd.Series(np.asarray(labels), index=model.index)
    lines=['## 分群主導特徵檢查（非獨立驗證）','',
           '以下以每個群組在指定類別特徵中的最大類別比例衡量對應程度。這不是因果分析、特徵重要度或外部驗證；計算所用的特徵本身也參與分群。','',
           '| 模型類別特徵 | 群組加權多數類別比例 | 各群主要類別／比例 |',
           '|---|---:|---|']
    findings=[]
    for col in model:
        if schema[col]['type'] not in {'nominal','ordinal','binary'}:
            continue
        parts=[];matched=0
        for g in sorted(groups.unique()):
            values=model.loc[groups==g,col].fillna('（缺失）').astype(str)
            counts=values.value_counts()
            if counts.empty: continue
            dominant=counts.index[0]; count=int(counts.iloc[0]); matched += count
            parts.append(f'群{g+1}：{dominant} {count}/{len(values)}')
        purity=matched/len(groups) if len(groups) else 0
        findings.append((col,purity))
        groups_summary = '；'.join(parts)
        lines.append(f'| {col} | {purity:.4f} | {groups_summary} |')
    if not findings:
        lines.append('| 無類別特徵 | 不適用 | 改用原始尺度群組輪廓，不推論單一主導特徵 |')
    elif max(p for _,p in findings) >= .9:
        col,degree=max(findings,key=lambda x:x[1])
        lines += ['',f'**重要限制：** `{col}` 在各群的加權多數類別比例為 {degree:.4f}，表示分群與這個既有欄位高度對應。這可能主要反映原始分類或插補結果，不能直接宣稱發現了新的獨立族群。',
                  '此處 0.90 僅作為提醒用的描述性標示，不是通用統計門檻或模型優劣判定。']
    return '\n'.join(lines)+'\n\n'


def selection_warnings(results: list, final_index: int | None) -> str:
    """Data-grounded alerts for the search boundaries and fragile groups."""
    lines=['## 搜尋邊界、小群與指標衝突','']
    if not results:
        return '本輪沒有候選結果，無法進行統計比較。\n'
    valid=[(i,r['metrics']['silhouette']) for i,r in enumerate(results)
           if r['metrics'].get('silhouette') is not None]
    if not valid:
        lines.append('本輪所有候選的 Silhouette 均無定義；不能根據此指標選群。')
    else:
        maximum=max(float(v) for _,v in valid)
        winners=[i for i,v in valid if np.isclose(v,maximum,atol=1e-12,rtol=1e-12)]
        for dimension in ('k','eps','min_samples'):
            observed=sorted(set(r['config'][dimension] for r in results if dimension in r['config']))
            if len(observed)<2:
                continue
            low,high=observed[0],observed[-1]
            winning=[results[i]['config'][dimension] for i in winners if dimension in results[i]['config']]
            touched=[]
            if low in winning: touched.append(f'下界 {dimension}={low}')
            if high in winning: touched.append(f'上界 {dimension}={high}')
            if touched:
                lines.append('**邊界警示：** 本輪最高 Silhouette 候選觸及 '+ '、'.join(touched)+
                    '；此為有限搜尋範圍的結果，不能宣稱全域最佳。擴展或改變參數需新的 Stage 3 授權。')
        if final_index is not None and final_index not in winners:
            lines.append('核准候選並非本輪 Silhouette 最大者；應說明穩定性、群組大小或研究目的的取捨。')
    # For a readable Stage 4 narrative, detail the *chosen* candidate only.
    # Other candidates' group sizes are fully retained in CSV/JSON evidence.
    prefix='D' if results[0].get('method')=='dbscan' else 'C'
    selected=[(final_index,results[final_index])] if final_index is not None else []
    others_small=0
    for i,result in enumerate(results):
        labels=np.asarray(result['labels'])
        groups=sorted(set(int(g) for g in labels)-{-1})
        sizes={int(g):int(np.count_nonzero(labels==g)) for g in groups}
        small={g:n for g,n in sizes.items() if n<=max(1,int(np.ceil(len(labels)*.05)))}
        if i!=final_index:
            if small:others_small+=1
            continue
        if small:
            small_text='、'.join(f'第 {g+1} 群 {count} 人' for g,count in sorted(small.items()))
            lines.append(f'最終候選 {prefix}{i+1} 有小群（不超過全部樣本 5%）：{small_text}。'
                         '5% 僅為描述性提醒，不是自動淘汰門檻。')
        noise=int(np.count_nonzero(labels==-1))
        if noise:
            lines.append(f'最終候選 {prefix}{i+1} 包含 {noise} 筆雜訊；'
                         'Silhouette 的有效觀測集合可能與其他候選不同。')
    if others_small:
        lines.append(f'另有 {others_small} 組非最終候選存在小群；詳細人數見 selection_evidence/cluster_sizes.csv。')
    if len(lines)==2:
        lines.append('本輪未觸發預設描述性警示；仍不能推論已找到自然群數。')
    return '\n'.join(lines)+'\n\n'


def render_approved_distance_comparison(rows: list) -> str:
    """Only pairs differing by metric, with fixed approved linkage and K."""
    if not rows:
        return ('## 距離度量的實證對照\n\n'
                '本輪沒有在相同 K、相同 Linkage 下已核准擬合的不同距離候選。'
                '只能說明距離特性與資料相容性，不可宣稱已比較 Euclidean、Manhattan 或 Gower 的勝負。\n\n')
    lines=['## 距離度量的已批准候選對照','',
           '固定 K 與 Linkage，比較實際核准的不同距離。'
           '不同距離的量尺不同，Silhouette、穩定性與群組解釋只提供探索性對照，不構成因果優勢。', '',
           '| 候選 | Linkage | K | Distance | Silhouette | 重抽樣 ARI |',
           '|---|---|---:|---|---:|---:|']
    for r in rows:
        fmt=lambda v:'NA' if v is None else f'{float(v):.4f}'
        lines.append(f"| {r['candidate_index']+1} | {r['linkage']} | {r['k']} | {r['metric']} | "
                     f"{fmt(r['silhouette'])} | {fmt(r['stability_ari_mean'])} |")
    lines+=['','使用各自距離對模型計算 Silhouette；若研究目的或原始特徵的表示改變，'
            '須另提 Stage 1/3 授權與必要的對照，不得在此偷偷改動。','']
    return '\n'.join(lines)+'\n'


def render_approved_linkage_comparison(rows: list) -> str:
    """Report only *actually fitted and approved* same-metric, same-K linkages."""
    if not rows:
        return ('## Distance／Linkage 的比較證據\n\n'
                '本輪沒有在相同距離與 K 下批准並擬合兩種 linkage；因此僅有事前理論選擇理由，'
                '**不能宣稱所選 linkage 經實證比較優於其他方案**。\n\n')
    lines=['## Distance／Linkage 的實際候選比較', '',
           '以下僅比較使用同一距離定義、同一 K、經 Stage 3 授權且已實際擬合的 linkage。'
           '數值相近不代表兩個分群相同，ARI 為配對全樣本切割一致性，並非重抽樣穩定性。', '',
           '| 候選 | 距離 | K | Linkage | Silhouette | 重抽樣 ARI | 最小群 n |',
           '|---|---|---:|---|---:|---:|---:|']
    for row in rows:
        fmt=lambda v:'NA' if v is None else f'{float(v):.4f}'
        lines.append(f"| {row['candidate_index']+1} | {row['metric']} | {row['k']} | {row['linkage']} | "
                     f"{fmt(row['silhouette'])} | {fmt(row['stability_ari_mean'])} | "
                     f"{row['min_nonnoise_group_size']} |")
    lines += ['', '觀測對照不建立單一分數或自動選定 linkage。'
              '若只測了同一距離的多種 linkage，也**不能**據此推論另一種距離較差。'
              '不同距離使用的尺度可能不同，不能直接把 Silhouette 差異當成距離的因果優勢。', '']
    return '\n'.join(lines)+'\n'


def descriptive_preprocessing_sensitivity(raw: pd.DataFrame, model: pd.DataFrame, plan: dict) -> str:
    """Read-only, observed-value sensitivity diagnostics; never creates alternative fits.

    In particular, a numeric Gower column uses its observed full range, so the
    central 5th--95th percentile span relative to that range describes possible
    attenuation by extremes, not the effect of an unapproved refit.
    """
    lines = [
        '### 前處理與距離尺度的描述性敏感性檢查', '',
        '以下全部根據已批准模型快照與原始值計算，**沒有更動前處理、重估分群或比較替代模型**。',
        '它能揭露數值全距、缺失插補與類別頻率的敏感性，但不能證明改用其他處理後群組仍相同。', '',
        '| 特徵 | 觀察到的對照 | 意義與限制 |', '|---|---|---|'
    ]
    for col in model.columns:
        original = raw[col]
        fitted = model[col]
        if pd.api.types.is_numeric_dtype(original):
            numbers = pd.to_numeric(original, errors='coerce').dropna()
            if len(numbers) >= 3 and np.isfinite(numbers).all():
                low, high = float(numbers.min()), float(numbers.max())
                p05, p95 = map(float, numbers.quantile([.05, .95]))
                full_range = high - low
                span = p95 - p05
                ratio = span / full_range if full_range > 0 else None
                summary = (f'原始範圍 [{low:.6g}, {high:.6g}]；'
                           f'P05～P95 跨度 {span:.6g}；'
                           f'中央跨度／全距 {ratio:.4f}' if ratio is not None
                           else '原始數值全距為零，不可用來定義正規化差異')
                caveat = ('若以全距標準化，中央 90% 觀測的尺度可能被極端值壓縮；'
                          '此比例不是特徵重要度，也不是重擬合結果。')
            else:
                summary = '有效數值不足或含非有限值，無法可靠估計中央跨度／全距'
                caveat = '不能在缺乏有效尺度證據時推論替代前處理的效果。'
            count = int(original.isna().sum() - fitted.isna().sum())
            if count:
                summary += f'；淨減少缺失 {count} 筆'
                caveat += ' 插補值可能增加人工相似性，應視為資料假設。'
        else:
            before = original.dropna().astype(str).value_counts()
            after = fitted.dropna().astype(str).value_counts()
            if len(after):
                top = str(after.index[0]); n = int(after.iloc[0])
                prior = int(before.get(top, 0))
                summary = f'建模最常見類別 {top}：{n}/{len(fitted)}（原始同類 {prior}/{len(original)}）'
                caveat = ('眾數或明示缺失標記可能改變該類別比例及 Gower 不相似度；'
                          '本項只比較實際封存資料，不推定轉換的因果效應。')
            else:
                summary = '建模類別全部缺失'
                caveat = '無法由此欄提供類別相似性。'
            count = int(original.isna().sum()-fitted.isna().sum())
            if count: summary += f'；淨減少缺失 {count} 筆'
        # Avoid unescaped markdown pipes in data-driven table cells.
        summary = summary.replace('|', '／').replace('\n', ' ')
        caveat = caveat.replace('|', '／')
        lines.append(f'| `{str(col).replace("|", "／")}` | {summary} | {caveat} |')
    lines += ['', '**檢查界線：** 若希望比較不含極端值、調整權重或另一種插補方式，'
                 '這是新的研究設定；需依 Stage 1／3 原始 Hard Gate 取得批准，'
                 '不得把上述描述性比率寫成已驗證的群數敏感性。', '']
    return '\n'.join(lines)+'\n'


def actual_metric_contrast(results: list, stability: list) -> dict:
    """Approved Silhouette and repeat-ARI only; no automatic winner."""
    if len(results)!=len(stability):
        raise ValueError('Each candidate requires its own bound stability evidence')
    rows=[]
    for i,(result, evidence) in enumerate(zip(results,stability)):
        valid=[float(r['ari']) for r in evidence.get('runs',[])
               if r.get('ari') is not None and np.isfinite(r['ari'])]
        labels=np.asarray(result['labels'])
        sizes=[int((labels==g).sum()) for g in set(labels)-{-1}]
        rows.append({'candidate_index':i,'config':result['config'],
            'silhouette':result['metrics'].get('silhouette'),
            'ari_mean':float(np.mean(valid)) if valid else None,
            'ari_valid_repeats':len(valid),'resample_failures':evidence.get('failures',0),
            'min_cluster_n':min(sizes) if sizes else None,
            'noise_n':int((labels==-1).sum())})
    extrema={}
    for key,label in [('silhouette','Silhouette'),('ari_mean','重抽樣 ARI')]:
        defined=[(row['candidate_index'],float(row[key])) for row in rows
                 if row.get(key) is not None and np.isfinite(row[key])]
        if defined:
            best=max(v for _,v in defined)
            extrema[key]={'label':label,'candidate_indices':[i for i,v in defined
                      if np.isclose(v,best,rtol=1e-12,atol=1e-12)],'defined_candidates':len(defined)}
    distinct=('silhouette' in extrema and 'ari_mean' in extrema and
             not set(extrema['silhouette']['candidate_indices']) &
                 set(extrema['ari_mean']['candidate_indices']))
    return {'candidates':rows,'metric_extrema':extrema,
            'conflicting_with_silhouette':['重抽樣 ARI'] if distinct else [],
            'interpretation':'Silhouette 比較每個點與同群觀測的平均距離，以及與最近其他群的平均距離；較高通常表示同群較接近、不同群較易區分。重抽樣 ARI 比較重抽樣分群與原分群在共同觀測上的一致性，越接近 1 越一致。兩者衡量不同性質，不建立綜合分數。'}


def render_metric_contrast(contrast: dict, final_index: int | None, prefix='C') -> str:
    lines=['### 候選品質與穩定性的實際比較','',
           '| 候選 | Silhouette（較高較好） | 重抽樣 ARI（較高較穩定） | 最小群 n | 失敗次數 |',
           '|---|---:|---:|---:|---:|']
    fmt=lambda x:'NA' if x is None else f'{float(x):.4f}'
    for row in contrast['candidates']:
        lines.append('| '+' | '.join([prefix+str(row['candidate_index']+1),fmt(row['silhouette']),
            fmt(row['ari_mean']),str(row['min_cluster_n'] or 'NA'),str(row['resample_failures'])])+' |')
    if contrast['conflicting_with_silhouette']:
        a=contrast['metric_extrema']['silhouette']['candidate_indices'][0]
        b=contrast['metric_extrema']['ari_mean']['candidate_indices'][0]
        first,second=contrast['candidates'][a],contrast['candidates'][b]
        lines.append(f'\n**相互競爭的候選：** {prefix}{a+1} 的 Silhouette={fmt(first["silhouette"])}、ARI={fmt(first["ari_mean"])}，'
                     f'{prefix}{b+1} 的 Silhouette={fmt(second["silhouette"])}、ARI={fmt(second["ari_mean"])}；'
                     f'最小群分別為 {first["min_cluster_n"]} 與 {second["min_cluster_n"]} 人。')
        lines.append('\n**指標衝突與選群取捨：** Silhouette 與 ARI 最佳候選不同；分離品質與重抽樣穩定性彼此衝突，'
                     '不能把其中一項當唯一的選群標準。必須同時考量群組大小、研究目的與已核准理由。')
    if final_index is not None:
        lines.append(f'\n正式選擇候選 {prefix}{final_index+1}；此對照不會自動改變已批准結果。')
    lines.append('\n'+contrast['interpretation'])
    return '\n'.join(lines)+'\n\n'


def render_cluster_profiles(raw: pd.DataFrame, model: pd.DataFrame, labels, schema: dict) -> str:
    """Grounded prose for every approved group; no invented segment psychology.

    Use the observed original-unit feature snapshot, not model-space values,
    for descriptions; model-space changes and imputation are discussed separately.
    """
    if labels is None:
        return '本研究沒有選定可解釋的最終分群；不提供臆測的群組輪廓。\n\n'
    labels = np.asarray(labels)
    if len(labels)!=len(raw):
        raise ValueError('Cluster profile label count mismatch')
    groups = sorted(int(g) for g in set(labels))
    n_total = len(labels)
    out=['### 各群實際特徵與研究討論','',
         '以下依已核准的分群指派及原始尺度觀測值撰寫；每個數值均為描述統計，'
         '不表示因果關係或新的獨立驗證。群組標籤只是便於閱讀的編號。','']
    numeric=[c for c in raw if schema[c]['type'] in {'numeric','count'}]
    nominal=[c for c in raw if schema[c]['type'] in {'nominal','ordinal','binary'}]
    global_medians={c:pd.to_numeric(raw[c],errors='coerce').median() for c in numeric}
    global_iqr={c:max(float(pd.to_numeric(raw[c],errors='coerce').quantile(.75)-
                     pd.to_numeric(raw[c],errors='coerce').quantile(.25)),1e-9) for c in numeric}
    medians_by_group={g:{c:float(pd.to_numeric(raw.loc[labels==g,c],errors='coerce').median())
                        for c in numeric if pd.to_numeric(raw.loc[labels==g,c],errors='coerce').count()}
                      for g in groups}
    modes_by_group={g:{} for g in groups}
    for g in groups:
        subset=raw.loc[labels==g]
        name='雜訊觀測' if g==-1 else f'第 {g+1} 群'
        out += [f'#### {name}（n={len(subset)}，占全部 {len(subset)/n_total:.1%}）','']
        if not len(subset):
            continue
        numeric_notes=[]
        for c in numeric:
            values=pd.to_numeric(subset[c],errors='coerce')
            if not values.count():
                numeric_notes.append(f'`{c}` 全部缺失，無法描述數值輪廓')
                continue
            val=float(values.median());medians_by_group[g][c]=val
            overall=global_medians[c]
            if pd.isna(overall):
                numeric_notes.append(f'`{c}` 中位數 {val:.3g}（有效 {values.count()}/{len(subset)}）')
            else:
                comp=('較整體高' if val>overall else '較整體低' if val<overall else '與整體相同')
                numeric_notes.append(f'`{c}` 中位數 {val:.3g}（整體 {overall:.3g}，{comp}，有效 {values.count()}/{len(subset)}）')
        if numeric_notes:
            out.append('**數值特徵：** '+'；'.join(numeric_notes)+'。\n')
        category_notes=[]
        for c in nominal:
            values=subset[c].fillna('（缺失）').astype(str)
            freqs=values.value_counts(dropna=False)
            if not len(freqs):continue
            top,count=str(freqs.index[0]),int(freqs.iloc[0])
            modes_by_group[g][c]=top
            category_notes.append(f'`{c}` 最常見為 {top}（{count}/{len(subset)}，{count/len(subset):.1%}）')
        if category_notes:
            out.append('**類別特徵：** '+'；'.join(category_notes)+'。\n')
        # Find the largest *observed and reproducible* numerical contrast to
        # another group; IQR is only a within-feature ranking denominator.
        comparisons=[]
        for other in groups:
            if other==g or other not in medians_by_group:continue
            for c, val in medians_by_group[g].items():
                if c in medians_by_group[other]:
                    comparisons.append((abs(val-medians_by_group[other][c])/global_iqr[c],other,c,val,medians_by_group[other][c]))
        if comparisons:
            _,other,c,val,other_val=max(comparisons)
            other_name='雜訊觀測' if other==-1 else f'第 {other+1} 群'
            out.append(f'**群間比較：** 相較於{other_name}，`{c}` 的原始尺度中位數為 {val:.3g} 對 {other_val:.3g}；這是觀察到的差異，不能推定形成群組的因果原因。\n')
        if g==-1:
            out.append('這些是 DBSCAN 未指派至任何群組的雜訊點（既非核心點，也非邊界點）；不能視為額外的一群。\n')
        elif len(subset)/n_total <= .05:
            out.append('此群人數不超過樣本 5%，屬需額外審視的小群；5% 是描述性提醒，不是自動淘汰門檻。\n')
    if len(groups)>1:
        # A global comparison paragraph is keyed by observed categorical modes.
        for c in nominal:
            mode_values={v[c] for v in modes_by_group.values() if c in v}
            if len(mode_values)>1:
                out.append(f'**整體發現：** 各群在 `{c}` 的主要類別不完全一致；應結合上表實際比例，不能僅以群名認定它們具有不同的心理或行為機制。\n')
                break
    out.append('**研究界線：** 上述群間差異是使用本次特徵得到的描述性結果，不能當成外部驗證；插補、缺失值、特徵權重或小群不確定性須參照 Stage 1 設定。\n')
    return '\n'.join(out)+'\n'



def render_geometric_research_findings(model, labels, schema, method, approved_visual, info, fitted_preprocessing=None):
    """Evidence-limited Stage 5 geometric interpretation, not a simulated story.

    Do not call every 2D dataset Two Moons. Use ONLY genuinely confirmed
    pre-fit geometry observations and the saved post-fit labels/statistics.
    """
    if labels is None:
        return ''
    labels=np.asarray(labels)
    numeric=[c for c in model if schema[c]['type'] in {'numeric','count'}]
    if len(numeric)<2:
        return ''
    observations=(approved_visual or {}).get('observations',{})
    approved=(approved_visual or {}).get('status')=='OPERATOR_VISUAL_REVIEW_RECORDED'
    nonconvex=approved and observations.get('nonconvex',{}).get('value')=='observed'
    curved=approved and observations.get('curved',{}).get('value')=='observed'
    groups=[int(g) for g in sorted(set(labels)) if g!=-1]
    if not groups:
        return ''
    cols=numeric[:2]
    text=['### 實際群組形狀與幾何研究發現','',
          '此段使用 Stage 1 已確認的幾何觀察、Stage 4 核准的實際群組標籤及建模特徵快照中的數值位置；'
          '沒有重跑模型，也不將圖形上的群組視為自然群組的證明。','']
    # Values below are computed from the stored *model* snapshot.  In particular,
    # for Z-score/robust/log1p runs they are not measurements in the raw unit.
    # Derive this disclosure from fitted parameters, not a proposed setting.
    coordinate_labels = {'standard': 'Z-score 標準化', 'robust': 'Robust 尺度轉換',
                         'none': '未進行尺度標準化'}
    coordinate_info=[]
    for col in cols:
        fitted=(fitted_preprocessing or {}).get(col)
        if not isinstance(fitted,dict):
            coordinate_info.append(f'`{col}`：建模快照（尺度無法由本段單獨確認）')
            continue
        transform=fitted.get('transform','none')
        scale=fitted.get('scale','none')
        steps=[]
        if transform=='log1p':
            steps.append('log1p 轉換')
        steps.append(coordinate_labels.get(scale, f'尺度設定 {scale}'))
        coordinate_info.append(f'`{col}`：'+ ' → '.join(steps))
    text += ['**座標尺度（實際建模空間）：** '+ '；'.join(coordinate_info)+'。'
             '以下範圍與中位數均來自 `model_feature_snapshot`，不可直接當成原始測量單位；'
             '原始單位的群間比較請見前面的群組輪廓與數值比較表。','']
    if not (nonconvex or curved):
        text+=['本次 Stage 1 並未確認非凸或彎曲的幾何結構，故不推定各群屬於彎月、環形或其他特定形狀；'
               '可對照 Stage 4 分群圖檢視位置與分散程度。','']
    else:
        shapes=('彎曲、非凸' if nonconvex and curved else '非凸' if nonconvex else '彎曲')
        text += [f'**研究圖形觀察：** Stage 1 已記錄 {shapes} 的觀測結構。'
                 '對於這類資料，群組的連續彎曲走向比各群單一中心位置更能描述分群特徵；'
                 '應檢查 Stage 4 的分群圖是否將可見的結構切碎、混合或錯誤橋接。','']
    for g in groups:
        subset=model.loc[labels==g,cols]
        x,y=(pd.to_numeric(subset[c],errors='coerce') for c in cols)
        if not len(subset) or not x.count() or not y.count():
            continue
        medx,medy=float(x.median()),float(y.median())
        rngx,rngy=(float(x.min()),float(x.max())),(float(y.min()),float(y.max()))
        other=[h for h in groups if h!=g]
        ycomp=''
        if other:
            yy=[(h,float(pd.to_numeric(model.loc[labels==h,cols[1]],errors='coerce').median()))
                for h in other]
            if yy:
                h,val=min(yy,key=lambda z:abs(z[1]-medy))
                ycomp=(f'；相對於第 {h+1} 群，此群在 `{cols[1]}` 的中位數'
                       f'{"較高" if medy>val else "較低" if medy<val else "相同"}（{medy:.3g} 對 {val:.3g}）')
        text += [f'**第 {g+1} 群（{len(subset)} 筆）：** 在平面上，`{cols[0]}` 範圍約 '
                 f'{rngx[0]:.3g}～{rngx[1]:.3g}、`{cols[1]}` 範圍約 '
                 f'{rngy[0]:.3g}～{rngy[1]:.3g}{ycomp}。'
                 + ('這些描述支持相對位置比較，但二維範圍不能替代密度連通性判斷。' if method=='dbscan'
                  else '這些描述支持相對位置比較，但二維範圍不能代表完整分群距離空間。'),'']
    if (len(groups)==2 and (curved or nonconvex)):
        medy={g:float(pd.to_numeric(model.loc[labels==g,cols[1]],errors='coerce').median())
              for g in groups}
        low,high=sorted(groups,key=lambda g:medy[g])
        text += [f'**兩群之間的幾何對照：** 第 {low+1} 群在 `{cols[1]}` 的中位位置較低，'
                 f'第 {high+1} 群較高；Stage 1 的彎曲結構證據與 Stage 4 的實際分群散佈圖'
                 '應一起用來檢查兩條分布是否各自保持連續。'
                 '此觀察不把中位數位置誤認為密度連通性的證明。','']
    if method=='dbscan':
        noise=int((labels==-1).sum())
        text += [f'**雜訊觀測：** 共 {noise} 筆（{noise/len(labels):.1%}），沒有歸入任何一群。'
                 '不能把它們當成第三群，也不能未經外部資料就判定為異常事件。','']
        if info.get('core_n') is not None:
            text += [f'核准的 DBSCAN 標籤中包含 {info["core_n"]} 個核心點、'
                     f'{info.get("border_n",0)} 個邊界點；這是固定 eps 與 min_samples 下的模型判定。','']
    if len(model.columns)>2:
        text += ['**投影限制：** 上述平面只使用兩個數值特徵，未包含其他建模特徵；'
                 '不能將二維位置視為完整的模型距離空間。','']
    return '\n'.join(text)+'\n'
