#!/usr/bin/env python3
"""jar2java - decompile .jar files to .java sources for IDE global search.
Default decompiler: Vineflower (fallback: CFR). Requires Java 11+ (17+ recommended)."""
import argparse, concurrent.futures as cf, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"
MAVEN = "https://repo1.maven.org/maven2"
DECOMPILERS = {
    "vineflower": ("org/vineflower/vineflower", "1.11.1"),
    "cfr": ("org/benf/cfr", "0.152"),
}
RES_SKIP = (".class",)

def log(*a): print("[jar2java]", *a, flush=True)

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

def main():
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
    a = ap.parse_args()
    if not a.inputs and not a.list: ap.error("give jar/folder or --list")
    if not shutil.which(a.java) and not Path(a.java).exists(): sys.exit("Java not found. Install JDK 17+ (e.g. Temurin) or set JAVA=/path/to/java")
    a.order = [a.decompiler] + ([] if a.no_fallback else [d for d in DECOMPILERS if d != a.decompiler])
    djars = {d: ensure_decompiler(d) for d in a.order}
    out_root = Path(a.output).resolve(); out_root.mkdir(parents=True, exist_ok=True)
    cache_f = out_root / ".jar2java-cache.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() and not a.force else {}
    jars = collect(a.inputs, a.list)
    names = {}
    todo = []
    for j in jars:
        key = j.stem
        if key in names and names[key] != j:  # name collision -> suffix
            key = f"{j.stem}_{hashlib.md5(str(j).encode()).hexdigest()[:6]}"
        names[key] = j
        h = sha256(j)
        opt = f"{a.decompiler}|{a.nested}|{a.nested_filter}|{a.no_resources}"
        if cache.get(str(j), {}).get("hash") == h and cache[str(j)].get("opt") == opt and (out_root / key).exists():
            log("SKIP (unchanged)", j.name); continue
        todo.append((j, h, opt, key))
    log(f"{len(jars)} jar(s) found, {len(todo)} to process, jobs={a.jobs}")
    allres = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(process, j, a, djars, out_root, 0, k): (j, h, opt) for j, h, opt, k in todo}
        for f in cf.as_completed(futs):
            j, h, opt = futs[f]
            rs = f.result(); allres += rs
            if rs[0]["ok"]: cache[str(j)] = {"hash": h, "opt": opt}
    cache_f.write_text(json.dumps(cache, indent=1))
    fails = [r for r in allres if not r["ok"]]
    with open(out_root / "jar2java-failures.log", "w", encoding="utf-8") as f:
        for r in fails: f.write(f"{r['jar']}\n  {r['error']}\n\n")
    (out_root / "jar2java-report.json").write_text(json.dumps(allres, indent=1))
    if not a.no_ide: write_ide_files(out_root)
    log(f"done: {len(allres)-len(fails)} ok, {len(fails)} failed, "
        f"{sum(r['java'] for r in allres)} .java files -> {out_root}")
    if fails: log("see", out_root / "jar2java-failures.log")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
