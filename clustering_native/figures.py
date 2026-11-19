"""Small exact-data SVG figures without an optional plotting dependency.

All chart axes and legend labels display source feature names.
"""
from html import escape
from pathlib import Path
import numpy as np
import pandas as pd


def svg(path, title, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" viewBox="0 0 900 500">'
        '<rect width="900" height="500" fill="white"/>'
        '<style>text{font-family:Arial,sans-serif;font-size:13px;fill:#182a3a}</style>'
        f'<text x="35" y="30" font-size="20">{escape(title)}</text>{body}</svg>', encoding="utf-8")


def eda_figures(df, eda, directory):
    directory = Path(directory)
    aliases = {c: str(c) for c in df.columns}
    numeric = [c for c in eda["numeric"] if eda["numeric"][c]["valid_n"] > 0]
    body = '<text x="35" y="55">Raw values; panel-wise vertical scales; flagged extremes retained</text>'
    shown = numeric[:8]
    for i, c in enumerate(shown):
        a = pd.to_numeric(df[c], errors="coerce").dropna().to_numpy(dtype=float)
        lo, q1, med, q3, hi = np.quantile(a, [0, .25, .5, .75, 1])
        span = hi-lo or 1.
        y = lambda v: 415-(v-lo)/span*310
        x = 95+i*95
        body += f'<line x1="{x}" y1="{y(lo)}" x2="{x}" y2="{y(hi)}" stroke="#344e65"/>'
        body += f'<rect x="{x-22}" y="{y(q3)}" width="44" height="{max(1,y(q1)-y(q3))}" fill="#b9dce8" stroke="#344e65"/>'
        body += f'<line x1="{x-22}" y1="{y(med)}" x2="{x+22}" y2="{y(med)}" stroke="#102b42" stroke-width="2"/>'
        for v in a[(a < q1-1.5*(q3-q1)) | (a > q3+1.5*(q3-q1))]:
            body += f'<circle cx="{x}" cy="{y(v)}" r="2.5" fill="#b35b42"/>'
        body += f'<text x="{x-20}" y="445" transform="rotate(-30 {x-20} 445)">{escape(aliases[c])}</text><text x="{x-30}" y="490">{lo:.3g}..{hi:.3g}</text>'
    if not shown:
        body += '<text x="40" y="110">No confirmed numeric features; confirm schema first.</text>'
    svg(directory/"eda_numeric.svg", "Numeric quality: vertical boxplots", body)
    cats = [c for c in df if c not in numeric and next(x for x in eda["columns"] if x["column"] == c)["role"] == "feature"]
    body = '<text x="35" y="55">Missingness and top category shares; denominators = all observations</text>'
    for i, c in enumerate((cats or list(df))[:8]):
        counts = df[c].value_counts(dropna=False)
        top = counts.iloc[0]/len(df) if len(counts) else 0
        missing = df[c].isna().mean()
        yy = 90+i*44
        body += f'<text x="35" y="{yy+15}">{escape(aliases[c])}</text><rect x="220" y="{yy}" width="{top*480}" height="15" fill="#387c94"/>'
        body += f'<text x="710" y="{yy+13}">top {top:.1%}; missing {missing:.1%}</text>'
    svg(directory/"eda_categories.svg", "Category and missingness quality", body)
    return aliases


def result_figure(results, path):
    """Actual metric marks, not text masquerading as a statistical figure.

    Candidates are shown in proposal order. Undefined silhouettes are explicit
    and do not become zero; noise is a separate fraction, not a cluster.
    """
    import json
    body = '<text x="35" y="57">Exploratory candidates; no automatic winner; silhouette excludes noise for DBSCAN</text>'
    panels = [(65, 315, "Silhouette", -1., 1.),
              (365, 610, "Non-noise clusters", 0., max(1., max((r['metrics'].get('clusters', 0) for r in results), default=1))),
              (660, 865, "Noise fraction", 0., 1.)]
    marks=[]
    for left,right,title,lo,hi in panels:
        body += f'<text x="{left}" y="85">{title}</text>'
        for value in (lo, (lo+hi)/2, hi):
            x=left+(value-lo)/(hi-lo)*(right-left)
            body += f'<line x1="{x:.3f}" y1="100" x2="{x:.3f}" y2="425" stroke="#dbe2e7"/><text x="{x-8:.3f}" y="448">{value:.3g}</text>'
    step=min(42., 300./max(1,len(results)))
    for i,r in enumerate(results):
        y=120+i*step
        body += f'<text x="15" y="{y+4:.3f}">{"D" if r.get("method")=="dbscan" else "C"}{i+1}</text>'
        silhouette=r['metrics'].get('silhouette');clusters=r['metrics'].get('clusters',0)
        noise=r.get('info',{}).get('noise_fraction')
        marks.append({'candidate':i+1,'silhouette':silhouette,'clusters':clusters,'noise_fraction':noise})
        for j,v in enumerate((silhouette,clusters,noise)):
            left,right,_,lo,hi=panels[j]
            if v is None or not np.isfinite(v):
                body += f'<text x="{left+8}" y="{y+4:.3f}">Undefined / not applicable</text>'
                continue
            x=left+(float(v)-lo)/(hi-lo)*(right-left)
            if j==0:
                body += f'<circle cx="{x:.6f}" cy="{y:.3f}" r="5" fill="#236b8e"/>'
            else:
                body += f'<rect x="{left}" y="{y-7:.3f}" width="{max(0,x-left):.6f}" height="14" fill="{["", "#53965a", "#c4792b"][j]}"/>'
            body += f'<text x="{min(right-38,x+7):.3f}" y="{y-10:.3f}">{float(v):.4g}</text>'
    body += '<text x="35" y="480">Candidate IDs follow report labels; undefined is not zero; proposal order retained</text>'
    body += '<metadata id="plotted-values">'+escape(json.dumps(marks, allow_nan=False))+'</metadata>'
    svg(path, "Candidate quality and coverage", body)
    return str(path)


def preview_assets(paths, attempt_png=True):
    """Return true file/preview availability, never claim a UI displayed them.

    The operator must deliver actual PNG files as separate Markdown *links*, not
    inline Markdown images or multimodal blocks in the user-facing chat.
    SVGs remain deliverables. Conversion is presentation-only; no fitting occurs.
    """
    import shutil
    import subprocess
    previews=[]
    for value in paths:
        source=Path(value).resolve()
        if not source.is_file():
            previews.append({'svg_path':str(source),'status':'MISSING','displayed':False,'reason':'Source image does not exist'})
            continue
        png=source.with_suffix('.png')
        record={'svg_path':str(source),'attachment_path':str(source),'displayed':False,
                'status':'SVG_ATTACHMENT_READY','preview_path':str(source),
                'operator_action':'Use stage_attachments and put each verified PNG link in a separate full-width paragraph. Do not inline images or pair images and captions in a horizontal layout.'}
        if png.is_file() and png.stat().st_mtime_ns >= source.stat().st_mtime_ns and png.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n':
            record.update(status='PNG_PREVIEW_READY',preview_path=str(png),attachment_path=str(png))
        elif attempt_png:
            command=None
            if shutil.which('inkscape'):
                command=[shutil.which('inkscape'),str(source),'--export-type=png','--export-filename='+str(png),'--export-width=1800']
            elif shutil.which('rsvg-convert'):
                command=[shutil.which('rsvg-convert'),'-w','1800','-o',str(png),str(source)]
            if command is None:
                try:
                    import cairosvg
                    cairosvg.svg2png(url=str(source), write_to=str(png), output_width=1800)
                    from .presentation import image_content
                    image_content(png)
                    record.update(status='PNG_PREVIEW_READY',preview_path=str(png),attachment_path=str(png))
                except Exception as exc:
                    record['reason']='PNG converter unavailable or failed: '+str(exc)+ '; SVG attachment available' 
            else:
                try:
                    run=subprocess.run(command,capture_output=True,text=True,timeout=30)
                    record['conversion']={'command':command,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
                    if run.returncode==0 and png.is_file() and png.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n':
                        record.update(status='PNG_PREVIEW_READY',preview_path=str(png),attachment_path=str(png))
                    else:
                        record['reason']='PNG conversion failed; retain SVG attachment; no display claimed'
                except (OSError,subprocess.TimeoutExpired) as exc:
                    record['reason']='PNG conversion failed: '+str(exc)
        if record['status'] == 'PNG_PREVIEW_READY':
            try:
                from .presentation import image_content
                _, receipt = image_content(record['preview_path'])
                record['validation'] = receipt
            except Exception as exc:
                record.update(status='INVALID_PNG', reason=str(exc))
        record['interface_submission'] = 'NOT RUN'
        record['human_visible'] = 'UNVERIFIED'
        record['operator_action'] = 'Use stage_attachments for ALL real PNGs; send plain single-column links before the user gate. Do not call present_figures or forward image blocks to the chat; UI rendering remains UNVERIFIED.'
        previews.append(record)
    return previews


def density_figure(diagnostic, path):
    """One compact actual-data k-distance plot, no knee/epsilon annotation."""
    if not diagnostic.get('computed'):
        return None
    rows=diagnostic['neighbors'];maximum=max(r['max'] for r in rows) or 1
    body='<text x="40" y="60">Euclidean, approved features; k excludes self; no epsilon selected</text>'
    body+='<line x1="70" y1="420" x2="820" y2="420" stroke="#333"/><line x1="70" y1="100" x2="70" y2="420" stroke="#333"/>'
    colors=['#236b8e','#c4792b','#53965a','#b54b56','#7959a5']
    for i,r in enumerate(rows):
        a=r['sorted_distances'];pts=' '.join(f'{70+j/(len(a)-1)*750:.2f},{420-v/maximum*300:.2f}' for j,v in enumerate(a))
        body+=f'<polyline points="{pts}" fill="none" stroke="{colors[i%5]}" stroke-width="2"/>'
        body+=f'<text x="{85+i*140}" y="465">k={r["k_excluding_self"]}</text>'
    body+=f'<text x="35" y="105">{maximum:.3g}</text><text x="30" y="420">0</text><text x="350" y="445">Sorted observation rank</text>'
    svg(path,'Stage 2: multiscale neighbor distances',body)
    return str(path)


# R4E: figures deliberately separated by analytical stage. All plots use
# saved full-data labels; no fitting, no authorization token, no synthetic IDs.
def candidate_partition_preview(model, results, path):
    """Stage 3: show only which exploratory fits completed and their group counts."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from pathlib import Path
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        return None
    method = results[0]['method']
    prefix='D' if method=='dbscan' else 'C'
    names=[f'{prefix}{i+1}' for i in range(len(results))]
    groups=[int(r['metrics']['clusters']) for r in results]
    fig,ax=plt.subplots(figsize=(max(6,min(13,len(results)*.53+3)),3.5))
    ax.bar(names,groups)
    ax.set(title='Stage 3: approved candidate execution (descriptive only)',
           xlabel='Approved candidate',ylabel='Observed non-noise group count')
    ax.tick_params(axis='x',labelrotation=45)
    fig.tight_layout()
    for ext in ('svg','png'):
        fig.savefig(path.with_suffix('.'+ext),dpi=160,bbox_inches='tight')
    plt.close(fig)
    return path


def _planar_axes(model):
    """Return actual numeric columns, not fabricated embeddings/PCA."""
    import numpy as np
    numeric=[]
    for c in model.columns:
        try:
            v=np.asarray(model[c],dtype=float)
        except (ValueError,TypeError):
            continue
        if np.isfinite(v).all():
            numeric.append(c)
    return numeric[:2] if len(numeric)>=2 else None


def _scatter_partition(ax,model,labels,cols):
    import numpy as np
    labels=np.asarray(labels)
    x=np.asarray(model[cols[0]],dtype=float)
    y=np.asarray(model[cols[1]],dtype=float)
    groups=sorted(int(g) for g in set(labels) if g!=-1)
    colors=__import__('matplotlib.pyplot',fromlist=['get_cmap']).get_cmap('tab20')
    for i,g in enumerate(groups):
        mask=labels==g
        ax.scatter(x[mask],y[mask],s=13,alpha=.75,color=colors(i%20),
                   linewidths=0,label=f'Group {g+1} (n={mask.sum()})')
    noise=labels==-1
    if noise.any():
        ax.scatter(x[noise],y[noise],s=20,c='#777777',marker='x',
                   linewidths=.9,label=f'Noise (n={noise.sum()})')
    ax.set(xlabel=str(cols[0]),ylabel=str(cols[1]))
    ax.grid(True,alpha=.15)


def candidate_partition_grid(model, results, path):
    """Stage 4: true labels for approved candidates; no preferred label before approval."""
    import math
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from pathlib import Path
    path=Path(path)
    cols=_planar_axes(model)
    if cols is None or not results:
        return None
    path.parent.mkdir(parents=True,exist_ok=True)
    count=min(len(results),24)
    ncols=min(3,count)
    nrows=math.ceil(count/ncols)
    fig,axes=plt.subplots(nrows,ncols,figsize=(5.2*ncols,4.0*nrows),squeeze=False)
    prefix='D' if results[0]['method']=='dbscan' else 'C'
    for i in range(count):
        r=results[i];ax=axes[i//ncols][i%ncols]
        _scatter_partition(ax,model,r['labels'],cols)
        eps = f' eps={r["config"]["eps"]:.5g}' if 'eps' in r['config'] else ''
        k = f' K={r["config"]["k"]}' if 'k' in r['config'] else ''
        ax.set_title(f'{prefix}{i+1}{eps}{k} | groups={r["metrics"]["clusters"]}',fontsize=10)
    for i in range(count,nrows*ncols):
        axes[i//ncols][i%ncols].set_axis_off()
    suffix=(' (first 24 of '+str(len(results))+')' if len(results)>24 else '')
    projection_note=('; numeric projection only, excludes other features'
                     if len(model.columns)>2 else '')
    fig.suptitle('Stage 4: actual approved full-data candidate labels'+suffix+projection_note,
                 fontsize=11)
    fig.tight_layout(rect=[0,0,1,.97])
    for ext in ('svg','png'):
        fig.savefig(path.with_suffix('.'+ext),dpi=150,bbox_inches='tight')
    plt.close(fig)
    return path


def selected_partition_figure(model, result, path):
    """Stage 4 final approval: plot immutable labels, never refit; Stage 5 cites it."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from pathlib import Path
    path=Path(path)
    cols=_planar_axes(model)
    if cols is None or result is None:
        return None
    path.parent.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,5))
    _scatter_partition(ax,model,result['labels'],cols)
    ax.set_title('Stage 4: selected, approved model (saved full-data labels)')
    if len(set(result['labels']))<=11:
        ax.legend(fontsize=7,loc='best')
    fig.tight_layout()
    for ext in ('svg','png'):
        fig.savefig(path.with_suffix('.'+ext),dpi=160,bbox_inches='tight')
    plt.close(fig)
    return path
