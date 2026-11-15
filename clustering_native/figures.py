"""Small exact-data SVG figures without an optional plotting dependency.

Labels use English aliases F1..Fp. Report maps aliases to source columns.
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
    aliases = {c: f"F{i+1}" for i, c in enumerate(df.columns)}
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
        body += f'<text x="{x-16}" y="445">{aliases[c]}</text><text x="{x-30}" y="475">{lo:.3g}..{hi:.3g}</text>'
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
        body += f'<text x="35" y="{yy+15}">{aliases[c]}</text><rect x="100" y="{yy}" width="{top*590}" height="15" fill="#387c94"/>'
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
        body += f'<text x="15" y="{y+4:.3f}">C{i+1}</text>'
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
    body += '<text x="35" y="480">C = candidate number; undefined values are not plotted as zero; proposal order retained</text>'
    body += '<metadata id="plotted-values">'+escape(json.dumps(marks, allow_nan=False))+'</metadata>'
    svg(path, "Candidate quality and coverage", body)
    return str(path)


def preview_assets(paths, attempt_png=True):
    """Return true file/preview availability, never claim a UI displayed them.

    The operator must emit Markdown images using preview_path, and offer the
    attachment if the client does not render it. SVGs always remain deliverables.
    Optional conversion is a presentation-only action; no data are recomputed.
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
                'operator_action':'Emit an inline Markdown image; if the client cannot render it, offer the real image attachment and disclose that limitation.'}
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
        record['operator_action'] = 'Use presentation.image_content/image_batch and forward each image block with functions.image; JSON paths alone are not image output. Fall back to real PNG attachments.'
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
