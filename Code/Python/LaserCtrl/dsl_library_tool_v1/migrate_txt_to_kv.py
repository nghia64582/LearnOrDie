"""
Upload 1 lan cac file DSL .txt cu (dsl_library/*.txt) len Cloudflare
Worker KV theo dinh dang moi (xem dsl_library.py), roi doc lai va so
sanh tung byte.

Chay:
    python migrate_txt_to_kv.py [thu_muc_txt] [--overwrite]
"""

import sys
from pathlib import Path

from dsl_library import DSLLibrary, file_key


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    overwrite = "--overwrite" in sys.argv
    folder = Path(args[0]) if args else Path(__file__).parent / "dsl_library"

    lib = DSLLibrary(folder)
    results = lib.migrate_txt_files(folder, overwrite=overwrite)

    # Doc lai tu server (khong dung cache) va so sanh byte
    fresh = DSLLibrary(folder)
    fresh._cache["files"] = {}
    fresh.refresh()
    ok_all = True
    for filename, dsl_id, status in results:
        original = (folder / filename).read_bytes()
        remote = fresh.client.get(file_key(dsl_id))["content"].encode("utf-8")
        same = remote == original and dsl_id in fresh.index["drawings"]
        ok_all &= same
        print(f"{filename:32s} -> {file_key(dsl_id):45s} {status:28s} "
              f"verify={'OK' if same else 'MISMATCH'}")

    print("ALL OK" if ok_all else "SOME FILES DID NOT MATCH")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
