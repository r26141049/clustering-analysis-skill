"""Presentation-only image content bridge. Never imports or fits estimators."""
import base64
from html import escape
from pathlib import Path
import re
from PIL import Image
from .core import file_hash

# This is an operator/display contract, not an instruction to create artwork.
REAL_RESEARCH_FIGURES_ONLY = (
    '僅顯示本次真實研究產生的圖表（實際資料、已保存模型標籤或統計結果）；'
    '禁止網路圖片、模擬／示意圖、生成圖或與本次研究無關的補位圖片。'
    '無法內嵌時只交付本次實際存在的 PNG 附件，不重新擬合模型。'
)


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
            'human_visible': 'UNVERIFIED',
            'image_source_policy': REAL_RESEARCH_FIGURES_ONLY}


def offline_html(markdown, root):
    """Readable, self-contained offline report; code fully retained but folded.

    Only known Markdown constructs and PNG data URIs are generated. No scripts,
    remote resources or arbitrary raw HTML may enter the result.
    """
    root=Path(root).resolve()
    parts=[]; code=None; table=False; headers=False; in_list=False
    def inline(text):
        safe=escape(text)
        safe=re.sub(r'`([^`]+)`',r'<code>\1</code>',safe)
        safe=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',safe)
        return safe
    def close_table():
        nonlocal table,headers
        if table:parts.append('</tbody></table>');table=False;headers=False
    def close_list():
        nonlocal in_list
        if in_list:parts.append('</ul>');in_list=False
    for line in markdown.splitlines():
        if line.startswith('```'):
            close_table();close_list()
            if code is None:
                code=[]
            else:
                parts.append('<details class="code-block"><summary>展開 Python 程式碼</summary>'
                             '<pre><code class="language-python">'+escape('\n'.join(code))+
                             '</code></pre></details>')
                code=None
            continue
        if code is not None:
            code.append(line);continue
        if line.startswith('|'):
            close_list()
            if not table:
                parts.append('<table><tbody>');table=True;headers=True
            cells=line.strip().strip('|').split('|')
            if not all(re.fullmatch(r'[: -]+',cell) for cell in cells):
                tag='th' if headers else 'td'
                parts.append('<tr>'+''.join('<'+tag+'>'+inline(cell.strip())+'</'+tag+'>' for cell in cells)+'</tr>')
                headers=False
            continue
        close_table()
        match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line.strip())
        if match:
            close_list()
            image_path=(root/match[2]).resolve()
            if not image_path.is_relative_to(root):raise ValueError('Image outside report')
            block,_=image_content(image_path)
            parts.append('<figure><img loading="lazy" alt="'+escape(match[1],quote=True)+
                         '" src="data:image/png;base64,'+block['data']+'"><figcaption>'+escape(match[1])+'</figcaption></figure>')
        elif line.startswith('#'):
            close_list()
            level=min(len(line)-len(line.lstrip('#')),6)
            parts.append(f'<h{level}>'+inline(line[level:].strip())+f'</h{level}>')
        elif line.startswith('- '):
            if not in_list:parts.append('<ul>');in_list=True
            parts.append('<li>'+inline(line[2:])+'</li>')
        elif line.strip():
            close_list()
            if line.lstrip().startswith('<!--'):
                # status marker retained as text, not arbitrary HTML
                continue
            parts.append('<p>'+inline(line)+'</p>')
    if code is not None:raise ValueError('Unclosed code fence')
    close_table();close_list()
    style="""
    *{box-sizing:border-box}body{max-width:1020px;margin:2rem auto;padding:0 1.5rem;
    font:16px/1.75 -apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif;color:#273140;background:#fff}
    h1,h2,h3,h4{line-height:1.3;color:#172438}h1{border-bottom:2px solid #ccd4df;padding-bottom:.7rem}
    h2{margin-top:2.4rem;padding-bottom:.35rem;border-bottom:1px solid #e0e5ec}
    h3{margin-top:1.6rem}p{margin:.8rem 0;overflow-wrap:anywhere}
    table{border-collapse:collapse;width:100%;display:block;overflow-x:auto;margin:1rem 0 1.8rem;font-size:.91rem}
    td,th{border:1px solid #d9e0e8;padding:.5rem .7rem;vertical-align:top;text-align:left}
    th{background:#f3f6fa;font-weight:650}tr:nth-child(even) td{background:#fbfcfe}
    img{max-width:100%;height:auto}figure{margin:1.5rem 0}figcaption{font-size:.83rem;color:#536274;text-align:center}
    code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#f0f3f7;padding:.1rem .25rem;border-radius:3px}
    details.code-block{margin:1rem 0 1.9rem;border:1px solid #d6dfe8;border-radius:7px;background:#fafcfe}
    details summary{padding:.65rem .9rem;cursor:pointer;font-weight:600}
    pre{max-height:32rem;overflow:auto;margin:0;padding:1rem;background:#f4f6f9;border-top:1px solid #d6dfe8;font:13px/1.5 monospace}
    pre code{background:transparent;padding:0;white-space:pre}ul{padding-left:1.4rem}
    """
    return ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>分群研究報告</title><style>'+style+'</style></head><body>'+''.join(parts)+'</body></html>')

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
            'image_source_policy': REAL_RESEARCH_FIGURES_ONLY,
            'interface_submission':'NOT RUN','human_visible':'UNVERIFIED'}
    write_json(report/'presentation_validation.json',result)
    return result


def attachment_batch(paths, stage):
    """Build single-column, text-only PNG links without fitting or inline UI.

    The chat host may render a mixed image-and-caption response as a cramped
    column. Return ordinary independent Markdown *links* only, never image
    markup, HTML, base64, columns or layout components. A constructed link is
    not host submission or proof of successful user opening. Validate the
    complete batch first and fail closed when no images exist.
    """
    if type(stage) is not int or stage not in range(1, 6):
        raise ValueError('Stage 1..5 required')
    paths = list(paths)
    if not paths:
        raise ValueError('No validated stage PNGs available; cannot claim attachment delivery')
    content, receipts = [], []
    for candidate in paths:
        path = Path(candidate).resolve(strict=True)
        _, receipt = image_content(path)
        if any(c in str(path) for c in ('\n', '\r', '<', '>')):
            raise ValueError('Unsafe attachment path')
        label = path.name.replace('\\', r'\\').replace('[', r'\[').replace(']', r'\]')
        link = '['+label+'](<sandbox:'+str(path)+'>)'
        content.append(link)
        receipts.append({**receipt, 'stage': stage, 'attachment_link': link,
                         'attachment_constructed': 'PASS',
                         'attachment_submission': 'NOT RUN',
                         'attachment_user_opened': 'UNVERIFIED',
                         'inline_display': 'UNVERIFIED'})
    return {'stage': stage, 'attachment_count': len(content),
            'attachment_markdown': '\n\n'.join(content), 'receipts': receipts,
            'chat_layout_contract': {
                'presentation': 'single_column_plain_markdown_links',
                'image_embedding': 'PROHIBITED_IN_CHAT',
                'captions': 'separate_normal_width_paragraphs',
                'tables_or_side_by_side_cards': 'PROHIBITED_FOR_FIGURES',
                'delivery_confirmation': 'USER_OPEN_REQUIRED',
            },
            'required_action': (
                'First explain the current-stage statistical results in ordinary paragraphs. '
                'On their OWN separate lines, emit ALL real PNG attachment_markdown links, '
                'with blank lines separating links. Never use ![](), HTML img, rich image '
                'content, side-by-side layouts, markdown tables containing figures, or '
                'a narrow caption column. Ask the current Hard Gate question only AFTER '
                'these links; do not search for, fabricate, illustrate, or generate '
                'substitute images; do not refit. Link construction does not verify UI '
                'visibility or that the user can open/download the links.'
            ),
            'image_source_policy': REAL_RESEARCH_FIGURES_ONLY,
            'attachment_delivery': 'NOT RUN', 'inline_display': 'UNVERIFIED'}
