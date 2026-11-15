"""Bounded Stage 2 EDA only: no estimator, epsilon or model search."""
import numpy as np
from .core import clean


def density_eda(model, plan, max_rows=500, memory_mb=32):
    n,p=model.shape
    metadata={'n':n,'p':p,'stage':2,'metric':'euclidean','weights':plan['weights'],
              'max_rows':max_rows,'memory_mb':memory_mb,'estimated_work_bytes':12*8*n*n+32*n*p,'model_fits':0,
              'k_convention':'neighbors exclude self; DBSCAN min_samples would include self',
              'natural_groups_proven':False,'eps_selected':None}
    types=[plan['schema'][c]['type'] for c in model]
    reason=None
    if not all(t in {'numeric','count'} for t in types):reason='Meaningful Euclidean numeric geometry not available'
    elif n<10 or p<2:reason='Insufficient rows/features for this multiscale diagnostic'
    elif n>max_rows or 12*8*n*n+32*n*p>memory_mb*1024**2:reason='Bounded Stage 2 diagnostic budget exceeded; ask before extra work'
    elif not np.isfinite(model.to_numpy(dtype=float)).all():reason='Remaining nonfinite/missing values'
    if reason:return {**metadata,'status':'資訊不足','computed':False,'reason':reason}
    X=model.to_numpy(dtype=float)*np.sqrt([plan['weights'][c] for c in model])
    D=np.empty((n,n))
    for i in range(n):D[i]=np.sqrt(np.sum((X-X[i])**2,axis=1))
    upper=D[np.triu_indices(n,1)]
    if not len(upper) or not np.any(upper>0):return {**metadata,'status':'不適合','computed':False,'reason':'No positive pairwise distances; identical observations cannot support density separation','all_pairwise_zero':True}
    np.fill_diagonal(D,np.inf);neighbors=np.sort(D,axis=1)[:,:n-1]
    ks=sorted({k for k in (1,4,9,14,25) if k<n});rows=[]
    for k in ks:
        a=neighbors[:,k-1];q=np.quantile(a,[.1,.25,.5,.75,.9,.95])
        rows.append({'k_excluding_self':k,'min_samples_including_self':k+1,
                     **dict(zip(['p10','p25','median','p75','p90','p95'],q)),
                     'min':a.min(),'max':a.max(),'constant_radius':bool(np.allclose(a,a[0],rtol=1e-12,atol=1e-12)),'sorted_distances':np.sort(a)})
    q=np.quantile(upper,[.05,.5,.95]);far=neighbors[:,-1]
    return clean({**metadata,'computed':True,'status':'COMPUTED','n':n,'p':p,'pairs':len(upper),'neighbors':rows,
       'duplicate_feature_rows':int(model.duplicated().sum()),
       'equidistant_pairs':bool(np.allclose(upper,upper[0],rtol=1e-12,atol=1e-12)),
       'radius_variation_observed':any(not r['constant_radius'] for r in rows),
       'concentration':{'mean':upper.mean(),'cv':upper.std()/upper.mean(),'p05':q[0],'median':q[1],'p95':q[2],
          'p95_p05':q[2]/q[0] if q[0]>0 else None,'median_nearest_farthest':np.median(neighbors[:,0]/far)},
       'interpretation':'Descriptive distance evidence; no universal thresholds, knee, epsilon or natural-cluster claim'})
