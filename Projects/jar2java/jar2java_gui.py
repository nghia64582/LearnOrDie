#!/usr/bin/env python3
"""jar2java GUI (Tkinter) - chọn file jar, chọn thư mục output, bấm Chạy."""
import os, queue, subprocess, sys, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jar2java as core


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("jar2java - Dịch file JAR sang mã nguồn Java")
        self.geometry("900x680")
        self.minsize(760, 560)
        self.q = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.jars = []  # list[str]
        self._build()
        self.after(100, self._poll)
        self.after(300, self._check_java)

    # ---------- UI ----------
    def _build(self):
        pad = dict(padx=6, pady=4)
        f1 = ttk.LabelFrame(self, text="1. File JAR/WAR cần dịch")
        f1.pack(fill="both", expand=True, **pad)
        bar = ttk.Frame(f1); bar.pack(fill="x")
        ttk.Button(bar, text="Thêm file JAR...", command=self.add_files).pack(side="left", **pad)
        ttk.Button(bar, text="Thêm thư mục...", command=self.add_folder).pack(side="left", **pad)
        ttk.Button(bar, text="Xoá mục đã chọn", command=self.remove_sel).pack(side="left", **pad)
        ttk.Button(bar, text="Xoá hết", command=self.clear).pack(side="left", **pad)
        self.count_lbl = ttk.Label(bar, text="0 file"); self.count_lbl.pack(side="right", **pad)
        cols = ("status", "java")
        self.tree = ttk.Treeview(f1, columns=cols, height=8, selectmode="extended")
        self.tree.heading("#0", text="File"); self.tree.heading("status", text="Trạng thái"); self.tree.heading("java", text="Số file .java")
        self.tree.column("#0", width=560); self.tree.column("status", width=150); self.tree.column("java", width=100, anchor="e")
        sb = ttk.Scrollbar(f1, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4); sb.pack(side="left", fill="y", pady=4)

        f2 = ttk.LabelFrame(self, text="2. Thư mục output"); f2.pack(fill="x", **pad)
        self.out_var = tk.StringVar(value=str(Path.cwd() / "output"))
        ttk.Entry(f2, textvariable=self.out_var).pack(side="left", fill="x", expand=True, **pad)
        ttk.Button(f2, text="Chọn...", command=self.pick_out).pack(side="left", **pad)

        f3 = ttk.LabelFrame(self, text="3. Tuỳ chọn"); f3.pack(fill="x", **pad)
        self.dec_var = tk.StringVar(value="vineflower")
        ttk.Label(f3, text="Decompiler:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Combobox(f3, textvariable=self.dec_var, values=["vineflower", "cfr"], state="readonly", width=12).grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(f3, text="Số luồng song song:").grid(row=0, column=2, sticky="w", **pad)
        self.jobs_var = tk.IntVar(value=max(1, (os.cpu_count() or 2) // 2))
        ttk.Spinbox(f3, from_=1, to=max(32, os.cpu_count() or 1), textvariable=self.jobs_var, width=5).grid(row=0, column=3, sticky="w", **pad)
        self.force_var = tk.BooleanVar()
        ttk.Checkbutton(f3, text="Chạy lại tất cả (bỏ qua cache)", variable=self.force_var).grid(row=0, column=4, sticky="w", **pad)
        self.nested_var = tk.BooleanVar()
        ttk.Checkbutton(f3, text="Dịch cả thư viện lồng bên trong (Spring Boot / WAR)", variable=self.nested_var).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(f3, text="Lọc tên thư viện (regex):").grid(row=1, column=3, sticky="e", **pad)
        self.filter_var = tk.StringVar()
        ttk.Entry(f3, textvariable=self.filter_var, width=20).grid(row=1, column=4, sticky="w", **pad)
        ttk.Label(f3, text="Tên thư mục output:").grid(row=3, column=0, sticky="w", **pad)
        self.mode_labels = {"Đường dẫn đầy đủ (D__work-space__server)": "path",
                            "Rút gọn (chỉ thêm path khi trùng tên)": "short", "Chỉ tên jar": "name"}
        self.mode_var = tk.StringVar(value=next(iter(self.mode_labels)))
        ttk.Combobox(f3, textvariable=self.mode_var, values=list(self.mode_labels), state="readonly", width=40).grid(row=3, column=1, columnspan=3, sticky="w", **pad)
        self.meta_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f3, text="Tạo file index @MetaInfo (tên class mã hoá ↔ name)", variable=self.meta_var).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(f3, text="Tên annotation:").grid(row=2, column=3, sticky="e", **pad)
        self.ann_var = tk.StringVar(value="MetaInfo")
        ttk.Entry(f3, textvariable=self.ann_var, width=20).grid(row=2, column=4, sticky="w", **pad)

        f4 = ttk.Frame(self); f4.pack(fill="x", **pad)
        self.run_btn = ttk.Button(f4, text="▶ Chạy", command=self.start); self.run_btn.pack(side="left", **pad)
        self.cancel_btn = ttk.Button(f4, text="Huỷ", command=self.do_cancel, state="disabled"); self.cancel_btn.pack(side="left", **pad)
        self.open_btn = ttk.Button(f4, text="Mở thư mục output", command=self.open_out, state="disabled"); self.open_btn.pack(side="left", **pad)
        self.prog = ttk.Progressbar(f4, mode="determinate"); self.prog.pack(side="left", fill="x", expand=True, **pad)
        self.status = ttk.Label(f4, text="Sẵn sàng", width=24); self.status.pack(side="left", **pad)

        f5 = ttk.LabelFrame(self, text="Nhật ký"); f5.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(f5, height=10, wrap="none", state="disabled", font=("Courier", 9))
        lsb = ttk.Scrollbar(f5, orient="vertical", command=self.log.yview); self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4); lsb.pack(side="left", fill="y", pady=4)

    # ---------- list ----------
    def _add(self, paths):
        for p in paths:
            p = str(Path(p).resolve())
            if p not in self.jars:
                self.jars.append(p); self.tree.insert("", "end", iid=p, text=p, values=("Chờ", ""))
        self.count_lbl.config(text=f"{len(self.jars)} file")

    def add_files(self):
        self._add(filedialog.askopenfilenames(title="Chọn file JAR/WAR", filetypes=[("Java archive", "*.jar *.war"), ("Tất cả", "*.*")]))

    def add_folder(self):
        d = filedialog.askdirectory(title="Chọn thư mục chứa file JAR (quét cả thư mục con)")
        if d:
            found = core.collect([d], None)
            if not found: messagebox.showinfo("jar2java", "Không tìm thấy file .jar/.war nào trong thư mục này.")
            self._add(found)

    def remove_sel(self):
        for i in self.tree.selection():
            self.tree.delete(i); self.jars.remove(i)
        self.count_lbl.config(text=f"{len(self.jars)} file")

    def clear(self):
        self.tree.delete(*self.tree.get_children()); self.jars.clear(); self.count_lbl.config(text="0 file")

    def pick_out(self):
        d = filedialog.askdirectory(title="Chọn thư mục output")
        if d: self.out_var.set(d)

    # ---------- run ----------
    def _check_java(self):
        ver = core.java_version(os.environ.get("JAVA", "java"))
        if ver: self._log("Java: " + ver)
        if not ver:
            messagebox.showerror("Thiếu Java", "Không tìm thấy Java trên máy.\n\nHãy cài JDK 11+ (ví dụ Eclipse Temurin: https://adoptium.net) "
                                 "rồi mở lại chương trình, hoặc đặt biến môi trường JAVA=đường_dẫn_tới_java.")
            return False
        return True

    def _log(self, msg):
        self.log.config(state="normal"); self.log.insert("end", msg + "\n"); self.log.see("end"); self.log.config(state="disabled")

    def start(self):
        if not self.jars: return messagebox.showwarning("jar2java", "Hãy thêm ít nhất một file JAR.")
        out = self.out_var.get().strip()
        if not out: return messagebox.showwarning("jar2java", "Hãy chọn thư mục output.")
        if not self._check_java(): return
        try: jobs = max(1, int(self.jobs_var.get()))
        except Exception: jobs = 1
        opts = core.make_options(inputs=list(self.jars), output=out, decompiler=self.dec_var.get(), jobs=jobs,
                                 nested=self.nested_var.get(), nested_filter=self.filter_var.get().strip() or None,
                                 force=self.force_var.get(), metainfo=self.meta_var.get(), name_mode=self.mode_labels[self.mode_var.get()],
                                 metainfo_annotation=(self.ann_var.get().strip().lstrip("@") or "MetaInfo"), java=os.environ.get("JAVA", "java"))
        for i in self.jars: self.tree.item(i, values=("Đang chờ...", ""))
        self.prog.config(maximum=len(self.jars), value=0)
        self.cancel.clear(); self.run_btn.config(state="disabled"); self.cancel_btn.config(state="normal"); self.open_btn.config(state="disabled")
        self.status.config(text="Đang chạy..."); self._log(f"=== Bắt đầu: {len(self.jars)} file -> {out}")
        core.LOG_HOOK = lambda m: self.q.put(("log", m))
        self.worker = threading.Thread(target=self._work, args=(opts,), daemon=True); self.worker.start()

    def _work(self, opts):
        try:
            res = core.run(opts, on_result=lambda r, d, t: self.q.put(("res", r)), cancel=self.cancel)
            self.q.put(("done", res))
        except Exception as e:
            self.q.put(("error", str(e)))

    def do_cancel(self):
        self.cancel.set(); self.cancel_btn.config(state="disabled")
        self.status.config(text="Đang huỷ..."); self._log("Đang huỷ: các file đang chạy sẽ hoàn tất, các file còn lại bị bỏ qua.")

    def _poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "log": self._log(data)
                elif kind == "res":
                    iid = data["jar"]
                    st = "Bỏ qua (không đổi)" if data.get("skipped") else "Đã huỷ" if data.get("cancelled") else \
                         ("✔ Xong" + (f" ({data.get('decompiler')})" if data.get("decompiler") else "")) if data["ok"] else "✘ Lỗi"
                    if self.tree.exists(iid): self.tree.item(iid, values=(st, data.get("java") or ""))
                    self.prog.step(1)
                elif kind in ("done", "error"): self._finish(kind, data)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, kind, data):
        core.LOG_HOOK = None
        self.run_btn.config(state="normal"); self.cancel_btn.config(state="disabled"); self.open_btn.config(state="normal")
        self.prog.config(value=self.prog["maximum"])
        if kind == "error":
            self.status.config(text="Lỗi"); self._log("LỖI: " + data); messagebox.showerror("jar2java", data); return
        ok = sum(1 for r in data if r["ok"]); fail = len(data) - ok; n = sum(r.get("java", 0) for r in data)
        msg = f"Hoàn tất: {ok} thành công, {fail} lỗi, {n} file .java"
        self.status.config(text="Hoàn tất" if not self.cancel.is_set() else "Đã huỷ"); self._log("=== " + msg)
        idx = Path(self.out_var.get()) / "metainfo-index.txt"
        if self.meta_var.get() and idx.exists(): self._log("Index @MetaInfo: " + str(idx))
        if fail: self._log("Xem chi tiết lỗi: " + str(Path(self.out_var.get()) / "jar2java-failures.log"))

    def open_out(self):
        p = str(Path(self.out_var.get()).resolve())
        try:
            if sys.platform.startswith("win"): os.startfile(p)
            elif sys.platform == "darwin": subprocess.Popen(["open", p])
            else: subprocess.Popen(["xdg-open", p])
        except Exception as e:
            messagebox.showerror("jar2java", f"Không mở được thư mục: {e}")


if __name__ == "__main__":
    App().mainloop()
