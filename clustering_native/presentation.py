"""Presentation-only image content bridge. Never imports or fits estimators."""
import base64
from html import escape
from pathlib import Path
import re
from PIL import Image
from .core import file_hash


def image_content(path):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != '.png':
        raise ValueError('PNG required for conversation output')
    with Image.open(path) as im:
        if im.format != 'PNG':
            raise ValueError('Invalid PNG')
        im.verify()
    with Image.open(path) as im:
        im.load()
        size = list(im.size)
    return {'type': 'image', 'mimeType': 'image/png',
            'data': base64.b64encode(path.read_bytes()).decode('ascii')}, {
            'path': str(path), 'sha256': file_hash(path), 'size': size,
            'file_output': 'PASS', 'content_constructed': 'PASS',
            'interface_submission': 'NOT RUN', 'human_visible': 'UNVERIFIED'}


def image_batch(paths, start=0, limit=3):
    if type(start) is not int or type(limit) is not int or start < 0 or not 1 <= limit <= 4:
        raise ValueError('Use nonnegative start and batch size 1..4')
    content, receipts = [], []
    for path in paths[start:start+limit]:
        block, receipt = image_content(path)
        content.append(block); receipts.append(receipt)
    return {'content': content, 'receipts': receipts,
            'next_start': start+len(content) if start+len(content) < len(paths) else None,
            'human_visible': 'UNVERIFIED'}


def offline_html(markdown, root):
    """Safe offline Markdown fallback: escaped prose/tables plus actual PNGs.

    Avoid a new Markdown renderer dependency; retain readable prewrapped prose.
    No scripts, remote fonts, styles or relative image references.
    """
    root = Path(root).resolve()
    parts = []; last = 0
    for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', markdown):
        parts.append('<pre>'+escape(markdown[last:match.start()])+'</pre>')
        path = (root/match[2]).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Image outside report')
        block, _ = image_content(path)
        parts.append('<figure><img alt="'+escape(match[1], quote=True)+'" src="data:image/png;base64,'+
                     block['data']+'"><figcaption>'+escape(match[1])+'</figcaption></figure>')
        last = match.end()
    parts.append('<pre>'+escape(markdown[last:])+'</pre>')
    return '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Clustering research</title><style>body{max-width:1100px;margin:2em auto;padding:0 1em;font:16px/1.6 sans-serif;color:#182a3a}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}img{max-width:100%;height:auto}figure{margin:1em 0}</style>'+''.join(parts)+'</html>'


def synchronize_status(report, status):
    report = Path(report)
    for name in ('analysis.md', 'analysis.qmd'):
        p = report/name
        text = p.read_text(encoding='utf-8')
        text = re.sub(r'<!-- RC6_CURRENT_STATUS -->.*?<!-- /RC6_CURRENT_STATUS -->',
            '<!-- RC6_CURRENT_STATUS -->目前交付狀態：'+status+'。<!-- /RC6_CURRENT_STATUS -->', text, flags=re.S)
        p.write_text(text, encoding='utf-8')
    quarto = report/'analysis.html'
    if quarto.is_file():
        html=quarto.read_text(encoding='utf-8')
        html=re.sub(r'<!-- RC6_CURRENT_STATUS -->.*?<!-- /RC6_CURRENT_STATUS -->',
            '<!-- RC6_CURRENT_STATUS -->目前交付狀態：'+status+'。<!-- /RC6_CURRENT_STATUS -->',html,flags=re.S)
        html=html.replace('目前階段：Stage 5，等待使用者最終交付確認。','目前交付狀態：'+status+'。')
        quarto.write_text(html,encoding='utf-8')
    (report/'analysis_offline.html').write_text(offline_html((report/'analysis.md').read_text(encoding='utf-8'), report), encoding='utf-8')


def validate_report_images(report):
    """Validate every MD/QMD PNG and every embedded HTML img byte-for-byte."""
    from html.parser import HTMLParser
    import io
    from .core import write_json
    report=Path(report).resolve(); records=[]; expected=[]
    markdown=(report/'analysis.md').read_text(encoding='utf-8')
    for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', markdown):
        path=(report/match[2]).resolve()
        if not path.is_relative_to(report): raise ValueError('Image reference escapes report')
        block,receipt=image_content(path)
        if not path.with_suffix('.svg').is_file(): raise ValueError('Vector attachment missing: '+str(path))
        expected.append(base64.b64decode(block['data'],validate=True))
        records.append({'reference':match[2],**receipt,'vector_retained':True})
    qmd=(report/'analysis.qmd').read_text(encoding='utf-8')
    if re.findall(r'!\[[^\]]*\]\(([^)]+)\)',qmd)!=[r['reference'] for r in records]:
        raise ValueError('Markdown/QMD image reference mismatch')
    class Images(HTMLParser):
        def __init__(self):super().__init__();self.sources=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag in {'script','link','base','iframe','object','embed','source'}:raise ValueError('External/active HTML dependency')
            if tag=='img':self.sources.append(attrs.get('src',''))
            if any('url(' in str(v).lower() or '@import' in str(v).lower() for v in attrs.values()):raise ValueError('CSS external dependency')
        def handle_data(self,data):
            # Generated stylesheet contains no URLs or imports.
            pass
    html=(report/'analysis_offline.html').read_text(encoding='utf-8');parser=Images();parser.feed(html)
    if len(parser.sources)!=len(expected):raise ValueError('Offline image count mismatch')
    for source,data in zip(parser.sources,expected):
        if not source.startswith('data:image/png;base64,'):raise ValueError('Offline image must be embedded PNG')
        embedded=base64.b64decode(source.split(',',1)[1],validate=True)
        if embedded!=data:raise ValueError('Embedded PNG differs from report image')
        with Image.open(io.BytesIO(embedded)) as im:im.load()
    for css in re.findall(r'<style[^>]*>(.*?)</style>',html,flags=re.S|re.I):
        if re.search(r'url\s*\(|@import',css,re.I):raise ValueError('Offline CSS must not load dependencies')
    result={'status':'PASS','images':records,'image_count':len(records),'markdown_qmd_refs':'PASS',
            'offline_all_images_embedded_exact_bytes':'PASS','offline_no_external_dependencies':'PASS',
            'interface_submission':'NOT RUN','human_visible':'UNVERIFIED'}
    write_json(report/'presentation_validation.json',result)
    return result


def attachment_batch(paths, stage):
    """Build clickable PNG attachment links, without fitting or inline output.

    A constructed link is not host submission or proof of successful user opening.
    Validate the complete batch before returning any links; never silently omit PNGs.
    """
    if type(stage) is not int or stage not in range(1, 6):
        raise ValueError('Stage 1..5 required')
    content, receipts = [], []
    for candidate in paths:
        path = Path(candidate).resolve(strict=True)
        _, receipt = image_content(path)
        if any(c in str(path) for c in ('\n', '\r', '<', '>')):
            raise ValueError('Unsafe attachment path')
        label = path.name.replace('[', r'\[').replace(']', r'\]')
        link = '['+label+'](<sandbox:'+str(path)+'>)'
        content.append(link)
        receipts.append({**receipt, 'stage': stage, 'attachment_link': link,
                         'attachment_constructed': 'PASS',
                         'attachment_submission': 'NOT RUN',
                         'attachment_user_opened': 'UNVERIFIED',
                         'inline_display': 'UNVERIFIED'})
    return {'stage': stage, 'attachment_count': len(content),
            'attachment_markdown': '\n\n'.join(content), 'receipts': receipts,
            'required_action': 'Emit every attachment_markdown link in the CURRENT stage user-facing response; JSON alone is not delivery. Do not retry inline display.',
            'attachment_delivery': 'NOT RUN', 'inline_display': 'UNVERIFIED'}
