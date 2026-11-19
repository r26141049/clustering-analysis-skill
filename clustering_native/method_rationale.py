"""User-facing, evidence-bound Stage 2 method recommendations.

The structured operator EDA is kept in the session audit. No free-form
operator dict, unreviewed claim or Stage 4 result is used as a method reason.
"""
from __future__ import annotations

NAMES = {'kmeans': 'K-means', 'hierarchical': 'Hierarchical',
         'dbscan': 'DBSCAN', 'pam': 'K-medoids (PAM 演算法)'}


def _flags(visual):
    if not isinstance(visual, dict) or visual.get('status') != 'OPERATOR_VISUAL_REVIEW_RECORDED':
        return set()
    observations = visual.get('observations', {})
    return {key for key, value in observations.items()
            if isinstance(value, dict) and value.get('value') == 'observed'}


def summarize_visual_geometry(visual):
    """Summarize only the confirmed flags; do not print the source dictionary.

    A specific 'two interleaved' claim requires that content to appear in the
    operator's recorded reason, not merely a nonconvex status.
    """
    flags = _flags(visual)
    if not flags:
        return '目前沒有已確認的特定幾何形狀；演算法能執行不代表適合恢復自然群組。'
    obs = visual.get('observations', {})
    parts = []
    nonconvex_reason = ' '.join(str(obs.get(k, {}).get('reason', ''))
                                for k in ('nonconvex', 'curved') if k in flags).lower()
    if {'curved', 'nonconvex'} <= flags and ('two interleav' in nonconvex_reason or
                                        'two intertwined' in nonconvex_reason):
        parts.append('經核准的散佈圖觀察顯示兩條相互交錯的彎曲、非凸帶狀結構')
    else:
        if 'nonconvex' in flags: parts.append('經核准的圖形觀察顯示非凸形狀')
        if 'curved' in flags: parts.append('存在彎曲或弧形走向')
    if 'unequal_density' in flags: parts.append('觀察到局部密度不均')
    if 'isolated_regions' in flags: parts.append('觀察到相對孤立的區域')
    if 'coarse_fine_structure' in flags: parts.append('觀察到粗細層級的結構')
    parts.append('這些是擬合前的探索性觀察，不證明真實群數或最佳方法')
    return '；'.join(parts)+'。'


def _short_reason(method, flags, purpose):
    curves = 'curved' in flags or 'nonconvex' in flags
    if method == 'dbscan':
        if curves:
            return '以局部密度連通形成群組，可追蹤彎曲、非凸結構並標示低密度觀測；須檢查 eps、碎群及橋接。'
        if purpose == 'density_noise_exploration':
            return '研究目的重視密度結構與雜訊辨識；須以近鄰距離規劃 eps，不預設分群數。'
        return '可探索密度與雜訊，但目前幾何尚不足以證明單一 eps 能穩定分群。'
    if method == 'kmeans':
        return ('可執行中心型切分，但可能把彎曲群組截成緊密區塊。' if curves else
                '適合探索緊密的中心型數值分群，仍須檢查尺度和初始化。')
    if method == 'hierarchical':
        return ('Single 可保留局部連通，但可能鏈化；Ward／Complete 偏緊密，可能切開彎曲結構。'
                if curves else '可研究群組合併層級，須依所選距離與 Linkage 檢查合併特性。')
    if method == 'pam':
        return ('K-medoids 使用實際觀測作代表點，但不保證恢復彎曲非凸群形。' if curves else
                'K-medoids 使用實際觀測作代表點；採 PAM 演算法及 Gower 距離適合混合型資料，仍須審查尺度與分群意義。')
    return '目前沒有足夠資料支持方法比較。'


def render_stage2_method_decision(assessment, chosen):
    """Narrative and four-method priority table from prefit Stage 2 evidence."""
    rows = assessment.get('methods', []) if isinstance(assessment, dict) else []
    if not rows:
        return (f'**方法選擇：** 已核准 {NAMES.get(chosen, chosen)}。'
                '未封存完整 Stage 2 比較與視覺證據，不補寫事後推薦理由。\n\n')
    visual = assessment.get('eda_handoff', {}).get('visual', {})
    flags = _flags(visual)
    purpose = assessment.get('purpose', 'exploratory_partition')
    rec = assessment.get('recommendation', {})
    preferred = rec.get('primary', [])
    chosen_is_primary = chosen in preferred
    main = _short_reason(chosen, flags, purpose)
    synopsis = summarize_visual_geometry(visual)
    summary = [
        '### 方法選擇的資料證據與理由', '',
        '**EDA 觀察：** '+synopsis, '',
        f'**本次核准方法：{NAMES.get(chosen, chosen)}。** '+main,
    ]
    if chosen_is_primary:
        summary.append('這個選擇符合 Stage 2 的優先探索建議，但仍只是擬合前適合性判斷，'
                       '不是已證明勝過其他演算法。')
    elif preferred:
        summary.append('此方法由使用者核准，與 Stage 2 的優先探索建議不同；'
                       '應同時保留適合性限制，不得改寫歷史推薦。')
    else:
        summary.append('Stage 2 未建立唯一的推薦首選；此方法是使用者核准的探索性選擇。')
    summary += ['', '### 四種方法的推薦優先度（擬合前）', '',
                '| 方法 | 推薦優先度 | 資料適用性 | 與本次資料相關的理由 |', '|---|---|---|---|']
    for row in rows:
        method = row.get('method')
        if method not in NAMES: continue
        priority = row.get('recommendation_priority')
        if not priority:
            priority = ('優先建議' if method in preferred else
                        '次優先考慮' if method in rec.get('secondary', []) else
                        '目前不適用' if row.get('status') == '不適合' else '其他可評估方案')
        reason = _short_reason(method, flags, purpose)
        if row.get('status') == '不適合':
            reason = '目前資料／距離條件不適用；'+reason
        summary.append(f'| {NAMES[method]} | {priority} | {row.get("status","待確認")} | {reason} |')
    summary += ['', '優先度可並列，選項編號不是推薦排名；'
                   '只有獲得使用者授權的演算法會進入後續候選模型規劃。', '']
    return '\n'.join(summary)+'\n'


def render_stage2_method_comparison(assessment, options=None):
    """A concise, approval-ready menu preview, without preselecting a method."""
    rows=assessment.get('methods', []) if isinstance(assessment,dict) else []
    if not rows:return '本次 Stage 2 尚未取得四方法適合性資料。\n'
    visual=assessment.get('eda_handoff',{}).get('visual',{})
    flags=_flags(visual)
    purpose=assessment.get('purpose','exploratory_partition')
    out=['### 四方法適合性與優先度', '',
         '**已核准 EDA：** '+summarize_visual_geometry(visual),'',
         '| 選單編號 | 分群方法 | 推薦優先度 | 適用性 | 本次資料理由 |',
         '|---|---|---|---|---|']
    option_by_method={method: option for option,method in (options or {}).items()}
    for row in rows:
        method=row.get('method')
        if method not in NAMES:continue
        option=option_by_method.get(method, '—（本輪不可選）')
        out.append(f'| {option} | {NAMES[method]} | {row.get("recommendation_priority","待評估")} '
                   f'| {row.get("status","待確認")} | {_short_reason(method,flags,purpose)} |')
    out+=['','選單編號不等於推薦名次；方法可執行與是否適合恢復資料形狀是兩件事。'
         '同級可以並列，最後由使用者選定方法，無法以此表授權擬合。','']
    return '\n'.join(out)+'\n'
