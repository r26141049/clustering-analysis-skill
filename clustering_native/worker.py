"""Private subprocess worker, JSON only."""
import json
import sys
import pandas as pd
from .core import write_json
from .engine import fit_one


def main():
    request, output = sys.argv[1:]
    try:
        args = json.loads(open(request, encoding="utf-8").read())
        data = pd.DataFrame(args.pop("data"))
        result = fit_one(data, **args)
        write_json(output, result)
    except Exception as exc:
        write_json(output, {"error": f"{type(exc).__name__}: {exc}"})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
