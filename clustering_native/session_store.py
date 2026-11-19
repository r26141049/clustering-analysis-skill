"""Durable local study discovery and fail-closed snapshots for the CLI.

The host must mount the configured root persistently for continuity across
isolated runtimes. Local snapshots never create or infer consent; the original
Gate remains authoritative. No implicit selection of a different study.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import uuid
from .core import file_hash, write_json
from .locking import session_lock


class SessionUnavailable(FileNotFoundError):
    """No verified saved study can be resumed; never synthesize approvals."""


def state_root():
    configured = os.environ.get('CLUSTERING_STATE_ROOT', '').strip()
    if configured:
        base = Path(configured).expanduser()
    elif os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'ClusteringAnalysis' / 'ResearchSessions'
    else:
        base = Path.home() / '.local' / 'share' / 'clustering-analysis' / 'research-sessions'
    return base.resolve()


def _prepare():
    base = state_root()
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    return base


def allocate_study():
    base = _prepare()
    target = base / 'studies' / uuid.uuid4().hex
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return target


def _index(base):
    f = base / 'index.json'
    if not f.exists():
        return {'version':1,'current':None,'studies':{}}
    data = json.loads(f.read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('studies'), dict):
        raise SessionUnavailable('Stored research index has an unsupported format; no authorization was reconstructed')
    return data


def _is_under(path, ancestor):
    return path == ancestor or path.is_relative_to(ancestor)


def _check_tree_no_symlinks(root):
    for walkroot, dirs, files in os.walk(root, followlinks=False):
        for item in dirs + files:
            if (Path(walkroot) / item).is_symlink():
                raise PermissionError('Refusing to archive symlinked research evidence')


def preserve(directory):
    """Atomically publish a copy after a successful/local-state-changing call.

    Snapshots are generation directories, so a crash while copying cannot
    replace the last complete snapshot. Index is atomically updated last.
    """
    source = Path(directory).resolve()
    state_file = source / 'session.json'
    input_file = source / 'input.original.csv'
    if not state_file.is_file() or not input_file.is_file():
        return None
    state = json.loads(state_file.read_text(encoding='utf-8'))
    sid = state.get('gate', {}).get('session_id')
    if not isinstance(sid,str) or len(sid) != 32 or any(c not in '0123456789abcdef' for c in sid):
        raise PermissionError('Cannot retain an invalid research Session identity')
    if file_hash(input_file) != state.get('input_sha256'):
        raise PermissionError('Cannot retain research with altered original input')
    base = _prepare()
    with session_lock(base/'.store.lock'):
        index = _index(base)
        prior = index['studies'].get(sid)
        # For recovered mirror locations, retain the original study identity.
        origin = prior['origin'] if prior else str(source)
        if prior and source not in (Path(prior['origin']).resolve(), Path(prior['snapshot']).resolve()):
            raise PermissionError('A research identity is already bound to a different origin')
        # Already in a durable study directory: use it directly to avoid copies.
        studies_root = (base/'studies').resolve()
        if _is_under(source,studies_root):
            snapshot = source
        elif prior and source == Path(prior['snapshot']).resolve():
            snapshot = source
        else:
            _check_tree_no_symlinks(source)
            dest_parent = base / 'snapshots'
            dest_parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            snapshot = dest_parent / (sid + '-' + uuid.uuid4().hex)
            shutil.copytree(source, snapshot)
            write_json(snapshot/'.session_origin.json', {'original_directory':origin})
            if file_hash(snapshot/'session.json') != file_hash(state_file) or file_hash(snapshot/'input.original.csv') != state['input_sha256']:
                shutil.rmtree(snapshot)
                raise IOError('Session snapshot verification failed')
        index['studies'][sid] = {'origin':origin,'snapshot':str(snapshot),'input_sha256':state['input_sha256']}
        index['current'] = sid
        write_json(base/'index.json',index)
        if prior:
            old = Path(prior['snapshot']).resolve()
            if old != snapshot and _is_under(old,(base/'snapshots').resolve()) and old.is_dir():
                shutil.rmtree(old)
    return {'session_id':sid, 'directory':str(snapshot),'status':'DURABLE_LOCAL_CHECKPOINT'}


def resolve_session(user_path=None):
    """Resume an exact study (or explicit current selection), never guess one."""
    explicit = user_path not in (None, '', 'auto')
    if explicit:
        path = Path(user_path).expanduser().resolve()
    base = state_root()
    if explicit and (path/'session.json').is_file():
        # An explicit existing study may be a legacy direct Session with no
        # index. If it is indexed, refuse a stale branch of the same study.
        if (base/'index.json').is_file():
            index = _index(base)
            matched = [(sid,r) for sid,r in index['studies'].items()
                       if Path(r['origin']).resolve() == path]
            if len(matched) == 1:
                sid, row = matched[0]
                snap = Path(row['snapshot']).resolve()
                if (snap/'session.json').is_file() and snap != path:
                    if file_hash(snap/'session.json') != file_hash(path/'session.json'):
                        source_state = json.loads((path/'session.json').read_text(encoding='utf-8'))
                        saved_state = json.loads((snap/'session.json').read_text(encoding='utf-8'))
                        a, b = source_state.get('gate',{}), saved_state.get('gate',{})
                        if (a.get('session_id') != sid or b.get('session_id') != sid or
                            source_state.get('input_sha256') != row['input_sha256'] or
                            saved_state.get('input_sha256') != row['input_sha256']):
                            raise SessionUnavailable('Original and checkpoint belong to different research identities')
                        ev_a, ev_b = a.get('events',[]), b.get('events',[])
                        if ev_a == ev_b:
                            if (a.get('approvals') != b.get('approvals') or
                                a.get('proposals') != b.get('proposals')):
                                raise SessionUnavailable('Original and checkpoint approvals diverged')
                            return path  # legitimate non-gate local recalculation
                        if len(ev_a) >= len(ev_b) and ev_a[:len(ev_b)] == ev_b:
                            return path  # original has newer, valid Gate events
                        if len(ev_b) > len(ev_a) and ev_b[:len(ev_a)] == ev_a:
                            return snap  # prevent stale original from rolling back Gate
                        raise SessionUnavailable('Original and checkpoint have conflicting histories; manual verification required')
        return path
    if not (base/'index.json').is_file():
        raise SessionUnavailable('No durable research Session exists. The Skill ZIP is program code, not a saved study; cannot reconstruct earlier approvals. Start a new study or restore the original Session workspace.')
    with session_lock(base/'.store.lock'):
        index = _index(base)
        if explicit:
            matches = [(k,r) for k,r in index['studies'].items() if Path(r['origin']).resolve() == path]
            if len(matches) != 1:
                raise SessionUnavailable('The requested Session path is unavailable and has no matching verified local checkpoint; no other study was selected')
            sid, row = matches[0]
        else:
            sid = index.get('current')
            row = index['studies'].get(sid)
            if not row:
                raise SessionUnavailable('No single current research Session is recorded; specify a verified Session path')
        snapshot = Path(row['snapshot']).resolve()
        # Do not follow paths from a modified index outside the private store.
        if not (_is_under(snapshot,(base/'studies').resolve()) or
                _is_under(snapshot,(base/'snapshots').resolve())):
            raise SessionUnavailable('The saved Session index points outside the private study store')
        if not (snapshot/'session.json').is_file() or not (snapshot/'input.original.csv').is_file():
            raise SessionUnavailable('The saved Session checkpoint is missing or incomplete; no authorization was reconstructed')
        if file_hash(snapshot/'input.original.csv') != row['input_sha256']:
            raise SessionUnavailable('The saved Session input does not match its original digest; not resumed')
        state = json.loads((snapshot/'session.json').read_text(encoding='utf-8'))
        if state.get('input_sha256') != row['input_sha256'] or state.get('gate',{}).get('session_id') != sid:
            raise SessionUnavailable('The saved Session identity or input binding changed; not resumed')
        if explicit and Path(row['origin']).resolve() != path:
            raise SessionUnavailable('Session alias mismatch')
    return snapshot


def saved_status(directory):
    from .session import Session
    session = Session(directory)
    proposals = {key: {'stage':proposal['stage'],'status':proposal['status']}
                 for key, proposal in session.gate.state['proposals'].items() if proposal['status']=='PENDING'}
    return {'session_id': session.gate.state['session_id'], 'phase': session.gate.state['phase'],
            'pending_decisions':proposals,'approvals': sorted(session.gate.state['approvals']),
            'input_sha256':session.state['input_sha256'], 'model_fits':len(session.state.get('results',[])),
            'resumed_without_new_consent':True}
