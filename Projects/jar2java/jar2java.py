#!/usr/bin/env python3
"""jar2java - decompile .jar files to .java sources for IDE global search.
Default decompiler: Vineflower (fallback: CFR). Requires Java 11+ (17+ recommended)."""
import argparse, struct, concurrent.futures as cf, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"
MAVEN = "https://repo1.maven.org/maven2"
DECOMPILERS = {
    "vineflower": ("org/vineflower/vineflower", "1.11.1"),
    "cfr": ("org/benf/cfr", "0.152"),
}
RES_SKIP = (".class",)

LOG_HOOK = None  # GUI can set a callable(str)

def log(*a):
    msg = " ".join(str(x) for x in a)
    if LOG_HOOK: LOG_HOOK(msg)
    else: print("[jar2java]", msg, flush=True)

def find_java(java="java"):
    """Return path to java executable or None."""
    return shutil.which(java) or (java if Path(java).exists() else None)

def latest_version(path, default):
    try:
        x = urllib.request.urlopen(f"{MAVEN}/{path}/maven-metadata.xml", timeout=15).read().decode()
        m = re.search(r"<release>([^<]+)</release>", x)
        return m.group(1) if m else default
    except Exception:
        return default

def ensure_decompiler(name):
    TOOLS.mkdir(exist_ok=True)
    found = sorted(TOOLS.glob(f"{name}-*.jar"))
    if found: return found[-1]
    path, default = DECOMPILERS[name]
    ver = latest_version(path, default)
    art = path.split("/")[-1]
    url = f"{MAVEN}/{path}/{ver}/{art}-{ver}.jar"
    dst = TOOLS / f"{name}-{ver}.jar"
    log("downloading", url)
    urllib.request.urlretrieve(url, dst)
    return dst

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def collect(inputs, list_file):
    items = list(inputs)
    if list_file:
        items += [l.strip() for l in Path(list_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    jars = []
    for i in items:
        p = Path(i)
        if p.is_dir(): jars += sorted(x for x in p.rglob("*") if x.suffix.lower() in (".jar", ".war"))
        elif p.is_file(): jars.append(p)
        else: log("WARN not found:", i)
    seen, out = set(), []
    for j in jars:
        r = j.resolve()
        if r not in seen: seen.add(r); out.append(r)
    return out

def run_decompiler(name, djar, src_jar, outdir, java, xmx):
    outdir.mkdir(parents=True, exist_ok=True)
    if name == "vineflower":
        cmd = [java, f"-Xmx{xmx}", "-jar", str(djar), "-dgs=1", "-rsy=1", "-rbr=1", "-ind=    ", "-log=WARN", str(src_jar), str(outdir)]
    else:
        cmd = [java, f"-Xmx{xmx}", "-jar", str(djar), str(src_jar), "--outputdir", str(outdir), "--silent", "true"]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0: raise RuntimeError(f"{name} exit {r.returncode}: {r.stderr[-2000:]}")
    # Vineflower writes a jar/zip or a dir depending on version: normalize to sources dir
    for z in list(outdir.glob("*.jar")) + list(outdir.glob("*.zip")):
        with zipfile.ZipFile(z) as zf: zf.extractall(outdir)
        z.unlink()
    # CFR writes summary.txt
    (outdir / "summary.txt").unlink(missing_ok=True)

def copy_resources(jar, outdir, prefix_strip=""):
    n = 0
    with zipfile.ZipFile(jar) as zf:
        for info in zf.infolist():
            name = info.filename
            if info.is_dir() or name.endswith(RES_SKIP) or name.lower().endswith((".jar", ".war")): continue
            if prefix_strip and name.startswith(prefix_strip): name = name[len(prefix_strip):]
            dst = outdir / name
            if not dst.resolve().is_relative_to(outdir.resolve()): continue  # zip-slip guard
            if dst.exists(): continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as s, open(dst, "wb") as d: shutil.copyfileobj(s, d)
            n += 1
    return n

def classes_jar_for_boot(jar, tmp):
    """Spring Boot / WAR: classes live in BOOT-INF/classes or WEB-INF/classes -> repack to plain jar."""
    with zipfile.ZipFile(jar) as zf:
        names = zf.namelist()
        for pre in ("BOOT-INF/classes/", "WEB-INF/classes/"):
            if any(n.startswith(pre) and n.endswith(".class") for n in names):
                out = Path(tmp) / (jar.stem + "-classes.jar")
                with zipfile.ZipFile(out, "w") as z2:
                    for n in names:
                        if n.startswith(pre) and not n.endswith("/"):
                            z2.writestr(n[len(pre):], zf.read(n))
                return out, pre
    return None, ""

def count_classes(jar):
    with zipfile.ZipFile(jar) as zf:
        return sum(1 for n in zf.namelist() if n.endswith(".class") and "$" not in n.rsplit("/",1)[-1])

def process(jar, args, djars, out_root, depth=0, outname=None):
    """Returns list of result dicts (this jar + nested)."""
    results = []
    name = outname or jar.stem
    outdir = out_root / name
    t0 = time.time()
    res = {"jar": str(jar), "out": str(outdir), "ok": False, "decompiler": None, "classes": 0, "java": 0, "error": None}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            boot, pre = classes_jar_for_boot(jar, tmp)
            target = boot or jar
            res["classes"] = count_classes(target)
            if outdir.exists(): shutil.rmtree(outdir)
            outdir.mkdir(parents=True)
            errors = []
            if res["classes"]:
                for dname in args.order:
                    try:
                        if dname == "cfr" and errors: shutil.rmtree(outdir); outdir.mkdir()
                        run_decompiler(dname, djars[dname], target, outdir, args.java, args.xmx)
                        res["decompiler"] = dname; break
                    except Exception as e:
                        errors.append(str(e))
                else:
                    raise RuntimeError(" | ".join(errors))
            if not args.no_resources:
                copy_resources(jar, outdir, pre)
            res["java"] = sum(1 for _ in outdir.rglob("*.java"))
            if getattr(args, "metainfo", True) and res["classes"]:
                rows = metainfo_scan(target, args.metainfo_annotation, (args.metainfo_attr, "value"))
                res["metainfo"] = len(rows)
                if rows:
                    write_metainfo(outdir / "metainfo-index", rows, args.metainfo_annotation)
                    log(f"MetaInfo {Path(res['jar']).name}: {len(rows)} class(es)")
            res["ok"] = True
            if args.nested:
                with zipfile.ZipFile(jar) as zf:
                    nested = [n for n in zf.namelist() if n.lower().endswith(".jar")]
                    if nested:
                        nd = Path(tmp) / "nested"; nd.mkdir()
                        libs_out = out_root / f"{name}__libs"
                        for n in nested:
                            p = nd / Path(n).name
                            p.write_bytes(zf.read(n))
                            if args.nested_filter and not re.search(args.nested_filter, p.name): continue
                            results += process(p, args, djars, libs_out, depth + 1)
    except Exception as e:
        res["error"] = str(e)[-3000:]
    res["seconds"] = round(time.time() - t0, 1)
    log(("OK  " if res["ok"] else "FAIL"), f"{Path(res['jar']).name}: {res['java']} .java / {res['classes']} classes ({res['seconds']}s)" + (f" via {res['decompiler']}" if res['decompiler'] else ""))
    return [res] + results

# ---------------- MetaInfo index (bytecode, stdlib only) ----------------
def _read_annotations(data, ann_simple, attrs):
    """Parse a .class file; return (fqcn, value) if it has annotation whose simple name == ann_simple.
    attrs: preferred element names in order; fallback to first string element."""
    if data[:4] != b"\xca\xfe\xba\xbe": return None
    pos = 10; n = struct.unpack(">H", data[8:10])[0]
    cp = [None] * n; i = 1
    while i < n:
        t = data[pos]
        if t == 1:
            ln = struct.unpack(">H", data[pos+1:pos+3])[0]
            cp[i] = data[pos+3:pos+3+ln].decode("utf-8", "replace"); pos += 3 + ln
        elif t == 7: cp[i] = ("C", struct.unpack(">H", data[pos+1:pos+3])[0]); pos += 3
        elif t in (8, 16, 19, 20): pos += 3
        elif t == 15: pos += 4
        elif t in (3, 4, 9, 10, 11, 12, 17, 18): pos += 5
        elif t in (5, 6): pos += 9; i += 1
        else: return None
        i += 1
    pos += 2  # access
    this_cls = struct.unpack(">H", data[pos:pos+2])[0]; pos += 4
    fqcn = cp[cp[this_cls][1]].replace("/", ".")
    ic = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2 + 2 * ic
    for _ in range(2):  # fields, methods
        cnt = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2
        for _ in range(cnt):
            pos += 6; ac = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2
            for _ in range(ac):
                pos += 2 + 4 + struct.unpack(">I", data[pos+2:pos+6])[0]
    ac = struct.unpack(">H", data[pos:pos+2])[0]; pos += 2
    def ev(q):  # returns (value_or_None, newpos)
        tag = chr(data[q]); q += 1
        if tag in "BCDFIJSZsc":
            idx = struct.unpack(">H", data[q:q+2])[0]
            return (cp[idx] if tag == "s" else None), q + 2
        if tag == "e": return None, q + 4
        if tag == "@": return None, ann(q)[1]
        if tag == "[":
            k = struct.unpack(">H", data[q:q+2])[0]; q += 2; vals = []
            for _ in range(k):
                v, q = ev(q)
                if v is not None: vals.append(v)
            return (", ".join(vals) if vals else None), q
        raise ValueError(tag)
    def ann(q):
        typ = cp[struct.unpack(">H", data[q:q+2])[0]]; k = struct.unpack(">H", data[q+2:q+4])[0]; q += 4
        pairs = {}
        for _ in range(k):
            nm = cp[struct.unpack(">H", data[q:q+2])[0]]; v, q = ev(q + 2)
            if v is not None: pairs[nm] = v
        return (typ, pairs), q
    for _ in range(ac):
        nm = cp[struct.unpack(">H", data[pos:pos+2])[0]]; ln = struct.unpack(">I", data[pos+2:pos+6])[0]
        body = pos + 6; pos = body + ln
        if nm not in ("RuntimeVisibleAnnotations", "RuntimeInvisibleAnnotations"): continue
        q = body + 2
        for _ in range(struct.unpack(">H", data[body:body+2])[0]):
            (typ, pairs), q = ann(q)
            simple = typ[1:-1].replace("$", "/").rsplit("/", 1)[-1]
            if simple == ann_simple:
                for a in attrs:
                    if a in pairs: return fqcn, pairs[a]
                if pairs: return fqcn, next(iter(pairs.values()))
    return None

def metainfo_scan(jar, ann_simple="MetaInfo", attrs=("name", "value")):
    """Return sorted list of (obfuscated FQCN, annotation value) for every class in jar (incl. inner classes)."""
    out = []
    with zipfile.ZipFile(jar) as zf:
        for n in zf.namelist():
            if not n.endswith(".class") or n.startswith("META-INF/versions/"): continue
            try:
                r = _read_annotations(zf.read(n), ann_simple, attrs)
                if r: out.append(r)
            except Exception as e:
                log("WARN metainfo parse", n, e)
    return sorted(set(out))

def metainfo_regex_scan(src_dir, ann_simple="MetaInfo", attr="name"):
    """Fallback/verification: regex over decompiled .java (top-level classes only)."""
    pat = re.compile(r"@(?:[\w.]+\.)?" + re.escape(ann_simple) + r"\s*\((?:[^)]*?\b" + re.escape(attr) + r"\s*=\s*|\s*)\"([^\"]*)\"")
    out = []
    for f in Path(src_dir).rglob("*.java"):
        m = pat.search(f.read_text(encoding="utf-8", errors="replace"))
        if m: out.append((".".join(f.relative_to(src_dir).with_suffix("").parts), m.group(1)))
    return sorted(out)

def _md_cell(s): return str(s).replace("|", "\\|")

def write_metainfo(path_base, rows, ann_simple, with_jar=False):
    """rows: (cls, value[, jar]). Writes <base>.txt (tab-separated) and <base>.md."""
    txt = Path(str(path_base) + ".txt"); md = Path(str(path_base) + ".md")
    with open(txt, "w", encoding="utf-8", newline="\n") as f:
        for r in rows: f.write("\t".join(r) + "\n")
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# @{ann_simple} index ({len(rows)})\n\n")
        f.write("| Class (obfuscated) | Name |" + (" Jar |" if with_jar else "") + "\n")
        f.write("|---|---|" + ("---|" if with_jar else "") + "\n")
        for r in rows: f.write("| " + " | ".join(_md_cell(x) for x in r) + " |\n")

# ---------------- output folder naming ----------------
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_NAME = 120

def _san(s):
    s = _BAD.sub("_", s).strip(" .")
    return s or "_"

def _parts(p):
    """Path components without root; drive 'D:' -> 'D'."""
    pp = Path(p)
    parts = list(pp.parts)
    if parts and parts[0] in (pp.anchor, "/"):
        parts = parts[1:]
        if pp.drive: parts = [pp.drive.rstrip(":\\/").replace(":", "")] + parts
    return parts

def output_names(jars):
    """Map each jar -> output folder name. Unique stems keep the plain stem (e.g. 'server');
    same-stem jars get the shortest parent-folder suffix that distinguishes them
    (e.g. 'work-space__server', 'work-space-2__server'). Case-insensitive (Windows)."""
    by = {}
    for j in jars: by.setdefault(Path(j).stem.lower(), []).append(Path(j))
    res = {}
    for group in by.values():
        if len(group) == 1:
            res[group[0]] = _san(group[0].stem); continue
        dirs = {j: [x.lower() for x in _parts(j.parent)] for j in group}
        for j in group:  # per jar: fewest trailing parent folders that no other jar shares
            d = dirs[j]; k = 1
            while k < len(d) and any(o is not j and dirs[o][-k:] == d[-k:] for o in group): k += 1
            res[j] = "__".join([_san(x) for x in _parts(j.parent)[-k:]] + [_san(j.stem)])
    used = set()
    for j, nm in res.items():
        if len(nm) > MAX_NAME:
            nm = nm[-(MAX_NAME - 7):].lstrip("_") + "_" + hashlib.md5(str(j).encode()).hexdigest()[:6]
        base, i = nm, 2
        while nm.lower() in used: nm = f"{base}_{i}"; i += 1
        used.add(nm.lower()); res[j] = nm
    return res

def write_ide_files(out_root):
    vs = out_root / ".vscode"; vs.mkdir(parents=True, exist_ok=True)
    (vs / "settings.json").write_text(json.dumps({
        "search.exclude": {"**/.jar2java-cache.json": True},
        "files.watcherExclude": {"**": True},
        "java.import.exclusions": ["**"],
        "search.useIgnoreFiles": False,
    }, indent=2))
    (out_root / ".ignore").unlink(missing_ok=True)
    iml = out_root / f"{out_root.name}.iml"
    if not iml.exists():
        iml.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<module type="JAVA_MODULE" version="4">\n  <component name="NewModuleRootManager">\n    <content url="file://$MODULE_DIR$" />\n  </component>\n</module>\n')

def build_parser():
    ap = argparse.ArgumentParser(description="Decompile JARs to .java for IDE search")
    ap.add_argument("inputs", nargs="*", help="jar files and/or folders (recursive)")
    ap.add_argument("-l", "--list", help="text file with one jar/folder per line")
    ap.add_argument("-o", "--output", default="output")
    ap.add_argument("-j", "--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("-d", "--decompiler", choices=["vineflower", "cfr"], default="vineflower")
    ap.add_argument("--no-fallback", action="store_true", help="don't retry with CFR on failure")
    ap.add_argument("--nested", action="store_true", help="also decompile nested jars (BOOT-INF/lib, WEB-INF/lib)")
    ap.add_argument("--nested-filter", help="regex: only nested jars whose name matches")
    ap.add_argument("--no-resources", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore hash cache")
    ap.add_argument("--no-ide", action="store_true", help="don't write .vscode / .iml")
    ap.add_argument("--java", default=os.environ.get("JAVA", "java"))
    ap.add_argument("--xmx", default="2g")
    ap.add_argument("--no-metainfo", dest="metainfo", action="store_false", help="don't build @MetaInfo index")
    ap.add_argument("--metainfo-annotation", default="MetaInfo", help="annotation simple name (any package)")
    ap.add_argument("--metainfo-attr", default="name", help="annotation element to read (fallback: value / first string)")
    return ap

def make_options(**kw):
    """Options namespace with CLI defaults (for programmatic / GUI use)."""
    a = build_parser().parse_args([])
    for k, v in kw.items(): setattr(a, k, v)
    return a

def run(a, on_result=None, cancel=None):
    """Core pipeline. on_result(res, done, total) per top-level jar; cancel: threading.Event.
    Returns list of result dicts."""
    a.order = [a.decompiler] + ([] if a.no_fallback else [d for d in DECOMPILERS if d != a.decompiler])
    djars = {d: ensure_decompiler(d) for d in a.order}
    out_root = Path(a.output).resolve(); out_root.mkdir(parents=True, exist_ok=True)
    cache_f = out_root / ".jar2java-cache.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() and not a.force else {}
    jars = collect(a.inputs, a.list)
    names = output_names(jars)
    todo = []
    mapping = {}
    for j in jars:
        key = names[j]; mapping[str(j)] = key
        if key != j.stem: log(f"MAP {j} -> {key}/")
        h = sha256(j)
        opt = f"{a.decompiler}|{a.nested}|{a.nested_filter}|{a.no_resources}|{a.metainfo}|{a.metainfo_annotation}|{a.metainfo_attr}"
        c = cache.get(str(j), {})
        if c.get("hash") == h and c.get("opt") == opt and c.get("out") == key and (out_root / key).exists():
            log("SKIP (unchanged)", j.name)
            if on_result: on_result({"jar": str(j), "ok": True, "skipped": True, "java": 0}, None, None)
            continue
        todo.append((j, h, opt, key))
    log(f"{len(jars)} jar(s) found, {len(todo)} to process, jobs={a.jobs}")
    allres = []
    done = 0
    def job(j, k):
        if cancel is not None and cancel.is_set():
            return [{"jar": str(j), "ok": False, "cancelled": True, "java": 0, "error": "cancelled"}]
        return process(j, a, djars, out_root, 0, k)
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        futs = {ex.submit(job, j, k): (j, h, opt) for j, h, opt, k in todo}
        for f in cf.as_completed(futs):
            j, h, opt = futs[f]
            rs = f.result(); allres += rs; done += 1
            if rs[0]["ok"]: cache[str(j)] = {"hash": h, "opt": opt, "out": mapping[str(j)]}
            if on_result: on_result(rs[0], done, len(todo))
    cache_f.write_text(json.dumps(cache, indent=1))
    fails = [r for r in allres if not r["ok"]]
    with open(out_root / "jar2java-failures.log", "w", encoding="utf-8") as f:
        for r in fails: f.write(f"{r['jar']}\n  {r['error']}\n\n")
    (out_root / "jar2java-report.json").write_text(json.dumps(allres, indent=1))
    (out_root / "jar2java-mapping.json").write_text(json.dumps(mapping, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.metainfo:
        rows = []
        for f in sorted(list(out_root.glob("*/metainfo-index.txt")) + list(out_root.glob("*__libs/*/metainfo-index.txt"))):
            jarname = str(f.parent.relative_to(out_root)).replace("\\", "/")
            for line in f.read_text(encoding="utf-8").splitlines():
                if "\t" in line: rows.append(tuple(line.split("\t", 1)) + (jarname,))
        write_metainfo(out_root / "metainfo-index", [r[:2] for r in rows], a.metainfo_annotation)
        write_metainfo(out_root / "metainfo-index-by-jar", rows, a.metainfo_annotation, with_jar=True)
        log(f"MetaInfo index: {len(rows)} entries -> {out_root / 'metainfo-index.txt'}")
    if not a.no_ide: write_ide_files(out_root)
    log(f"done: {len(allres)-len(fails)} ok, {len(fails)} failed, "
        f"{sum(r['java'] for r in allres)} .java files -> {out_root}")
    if fails: log("see", out_root / "jar2java-failures.log")
    return allres

def main():
    ap = build_parser()
    a = ap.parse_args()
    if not a.inputs and not a.list: ap.error("give jar/folder or --list")
    if not find_java(a.java): sys.exit("Java not found. Install JDK 17+ (e.g. Temurin) or set JAVA=/path/to/java")
    allres = run(a)
    sys.exit(1 if any(not r["ok"] for r in allres) else 0)

if __name__ == "__main__":
    main()
