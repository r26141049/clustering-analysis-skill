"""Conservative scoped language recognizer, not a general semantic oracle.
Unknown or mixed clauses require clarification. Never extract an affirmative
substring from an unrecognized reply. Token/session validation remains in Gate.
"""
import re

AFFIRMATIVE = {'a', '同意', '批准', '確認', '是', 'approve', 'yes', 'confirm'}
SCOPES = {
 'preprocess': r'(?:目前的?|上述的?|這份)?(?:前處理|預處理)(?:方案|設定)',
 'method': r'(?:目前的?|當前的?)?(?:方法選擇|分群方法|方法)',
 'candidates': r'(?:目前的?|上述的?|這批|這八組|這六組)?(?:候選(?:方案|設定|參數)?|執行方案|計算預算|預算)',
 'results': r'(?:目前的?|上述的?|這批)?(?:執行結果|候選結果|本輪結果|結果)',
 'final': r'(?:目前的?|上述的?)?(?:最終模型|最終方案|最終研究方案|候選\s*\d+)',
 'delivery': r'(?:目前的?|上述的?|修訂版的?)?(?:最終交付|交付|研究報告|報告|修訂版)' }
NEXT = {'preprocess':2,'method':3,'results':4,'final':5}
METHODS = {'dbscan','kmeans','hierarchical','pam'}


def _legacy_classify(response, item, payload=None):
    """Return APPROVE/REJECT/REVISE/CLARIFY plus an earliest revision stage."""
    payload = payload or {}
    if not isinstance(response,str) or not response.strip():
        return {'value':'CLARIFY','reason':'missing response'}
    text=response.strip(); low=text.casefold()
    if re.search(r'(?:不要|不想|不需|不用|不必)(?:先)?(?:修改|調整|更改)',text):
        return {'value':'CLARIFY','reason':'negated revision request needs clarification'}
    if re.search(r'(?:修改|調整|更改|改成|改為|修訂|變更|revise|modify|change)',low):
        stage=1 if re.search(r'前處理|預處理|特徵|權重|縮放',text) else 2 if re.search(r'方法',text) else 3 if re.search(r'eps|min_samples|候選|參數|範圍',low) else {'preprocess':1,'method':2,'candidates':3,'results':3,'final':4,'delivery':5}[item]
        return {'value':'REVISE','stage':stage,'reason':'revision takes precedence over approval'}
    if low in AFFIRMATIVE:return {'value':'APPROVE','reason':'exact affirmative for current pending item'}
    if low in {'b','修改'}:return {'value':'REVISE','stage':{'preprocess':1,'method':2,'candidates':3,'results':3,'final':4,'delivery':5}[item],'reason':'revise option'}
    if low in {'c','拒絕','不同意','reject','no'} or re.fullmatch(r'(?:我)?不同意[，,。\s]*(?:請)?(?:先)?(?:不要|不得)執行[。！!\s]*',text):
        return {'value':'REJECT','reason':'explicit rejection'}
    if re.search(r'不同意|拒絕',text) and not re.search(r'(?<!不)同意|批准|確認|(?:^|[，, ])A(?:$|[，, ])',text):
        return {'value':'REJECT','reason':'explicit rejection without contradictory approval'}
    if re.search(r'不要|不同意|不得|暫停|先別|不授權|不能|拒絕|not |never|但|如果|除非|也許|好像|似乎|吧|可能|\?|？|「|」|"',low):
        return {'value':'CLARIFY','reason':'qualified, negative, quoted, contradictory or ambiguous reply'}
    # Split only punctuation. Every clause must match the current item.
    clauses=[c.strip() for c in re.split(r'[，,。；;！!\n]+',text) if c.strip()]
    selected=payload.get('method')
    affirmative=False
    for c in clauses:
        if c.casefold() in AFFIRMATIVE:
            affirmative=True;continue
        if item=="candidates" and c=="請執行":continue
        if re.fullmatch(r'(?:我)?(?:明確)?(?:同意|批准|確認|接受)'+SCOPES[item],c):
            affirmative=True;continue
        if item=='method':
            m=re.fullmatch(r'(?:我)?(?:明確)?(?:確認)?選(?:擇)?\s*([A-Za-z-]+)(?:\s*作為當前方法選擇)?',c)
            if m and m.group(1).lower().replace('-','')==str(selected).replace('-',''):
                affirmative=True;continue
            if c=='請於 Stage 3 中使用該方法':continue
        if item in NEXT and re.fullmatch(r'請進入\s*Stage\s*'+str(NEXT[item])+r'(?:\s*(?:規劃|診斷|製作報告))?',c,re.I):continue
        if item=='candidates' and re.fullmatch(r'(?:我)?(?:明確)?(?:同意|批准|授權)執行(?:上述|目前的?)?(?:候選|候選方案|這批候選)(?:與預算)?',c):
            affirmative=True;continue
        if item=='delivery' and re.fullmatch(r'(?:我)?確認交付(?:並完成分析)?',c):
            affirmative=True;continue
        return {'value':'CLARIFY','reason':'unrecognized or out-of-scope clause'}
    return {'value':'APPROVE' if affirmative else 'CLARIFY','reason':'all clauses match pending scope' if affirmative else 'no explicit approval of pending item'}


# Scope-aware extension. Every clause must be recognized in full; unknown
# clauses fail closed. This is deliberately a bounded grammar, not keyword consent.
EXECUTION_LIMIT = re.compile(r"(?:除此之外[，,]\s*)?(?:本次只授權方法選擇與 Stage 3 規劃[，,]\s*)?(?:不授權執行任何候選分群模型|尚未批准執行模型擬合|不授權執行任何候選模型)")

def _scoped_classify(response, item, payload=None):
    payload = payload or {}
    legacy = _legacy_classify(response, item, payload)
    if legacy['value'] != 'CLARIFY' or not isinstance(response, str):
        return legacy
    if item not in {'preprocess','method'}:
        return legacy
    # No quoted or conditional assent, and modification is always handled first.
    if re.search(r'[「」"？?]|如果|除非|也許|好像|似乎', response):
        return legacy
    clauses = [c.strip() for c in re.split(r'[。；;！!\n]+',response.strip()) if c.strip()]
    restrictions=[]; affirmative=False
    for clause in clauses:
        if EXECUTION_LIMIT.fullmatch(clause):
            if '本次只授權方法選擇' in clause and item != 'method':
                return {'value':'CLARIFY','reason':'exclusive method scope conflicts with current pending item'}
            restrictions.append({'scope':'candidates','operation':'fit_candidates','decision':'NOT_AUTHORIZED','text':clause})
            continue
        if item=='preprocess':
            if re.fullmatch(r'我已審閱 Stage 1 的前處理建議',clause):
                continue
            if re.fullmatch(r'我明確同意目前提出的前處理方案[，,]授權依照該方案完成 Stage 1 並進入 Stage 2',clause):
                affirmative=True;continue
        if item=='method':
            if clause=='我已審閱 Stage 2 的方法推薦及統計理由':
                continue
            m=re.fullmatch(r'本次為 rc[0-9]+ 的 ([A-Za-z-]+) 回歸驗收[，,]因此我決定選擇 ([A-Za-z-]+)[，,]而不是優先推薦的 ([A-Za-z-]+)',clause)
            if m and m[1].lower().replace('-','')==m[2].lower().replace('-','')==str(payload.get('method')).lower().replace('-','') and m[3].lower().replace('-','')!=m[2].lower().replace('-',''):
                affirmative=True;continue
            m=re.fullmatch(r'請進入 Stage 3[，,]提出 ([A-Za-z-]+) 候選參數[、,，]設定依據及計算預算',clause)
            if m and m[1].lower().replace('-','')==str(payload.get('method')).lower().replace('-',''):
                continue
        # Recognize the existing narrow grammar clause by clause, without
        # extracting an affirmative substring from an unknown clause.
        parsed=_legacy_classify(clause,item,payload)
        if parsed['value']=='APPROVE':
            affirmative=True;continue
        return {'value':'CLARIFY','reason':'unknown, conflicting or out-of-scope clause','restrictions':restrictions}
    if not affirmative:
        return {'value':'CLARIFY','reason':'no explicit approval of pending item','restrictions':restrictions}
    return {'value':'APPROVE','reason':'explicit current-scope assent; downstream execution remains unauthorized','restrictions':restrictions}


METHOD_ALIASES = {'k-means':'kmeans', 'kmeans':'kmeans', 'hierarchical':'hierarchical',
    '階層分群':'hierarchical', '階層式分群':'hierarchical', 'dbscan':'dbscan',
    'pam':'pam', 'pam/gower':'pam', 'pam／gower':'pam', 'k-medoids':'pam'}

def classify(response, item, payload=None):
    payload = payload or {}
    if item == 'method' and isinstance(response, str):
        text = response.strip().casefold()
        m = re.fullmatch(r'(?:我)?(?:選擇|選|確認選擇)?\s*([\w/／-]+)[。！!]*', text)
        value = m[1] if m else None
        options = payload.get('options')
        selected = (options.get(value) if options else None) or METHOD_ALIASES.get(value)
        allowed = set(options.values()) if options else {payload.get('method')}
        if selected in METHODS and selected in allowed:
            return {'value':'APPROVE','reason':'Exact current method option; planning only', 'selected_method':selected}
        if options and text in {'a','同意','批准','yes','approve','確認'}:
            return {'value':'CLARIFY','reason':'Choose one current method option'}
    return _scoped_classify(response, item, payload)
