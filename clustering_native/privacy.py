"""Public output masking; backend state remains unchanged."""
import re
PRIVATE = re.compile(r"token|nonce|expires|ttl|deadline|authorization|approval.*hash", re.I)
def public_output(value, request=None):
    if isinstance(value, dict):
        return {k: public_output(v) for k,v in value.items() if not PRIVATE.search(k)}
    if isinstance(value, list): return [public_output(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\b[a-f0-9]{64}\b", "[internal digest]", value)
    return value
