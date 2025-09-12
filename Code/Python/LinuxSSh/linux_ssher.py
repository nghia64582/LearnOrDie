# ssh_task_runner_v5.py
import json, os, threading, queue, tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
from pathlib import Path
import getpass, paramiko, base64, hashlib
from paramiko.config import SSHConfig

TASKS_FILE = "ssh_tasks.json"
SETTINGS_FILE = "ssh_settings.json"

def parse_host(userhost: str):
    port = 22
    user = None
    raw = (userhost or "").strip()
    if not raw:
        return None, None, None
    if ":" in raw and raw.count(":") == 1 and "@" not in raw.split(":", 1)[1]:
        hostpart, port_str = raw.split(":", 1)
        try:
            port = int(port_str); raw = hostpart
        except ValueError:
            pass
    if "@" in raw:
        user, host = raw.split("@", 1)
        user = user or None
    else:
        host = raw
    return user, host, port

def load_ssh_config():
    path = Path.home() / ".ssh" / "config"
    if not path.exists(): return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = SSHConfig(); cfg.parse(f)
            return cfg
    except Exception:
        return None

def resolve_from_config(user, host, port):
    cfg = load_ssh_config()
    resolved = {"user": user, "host": host, "port": port or 22, "identities": []}
    if not cfg or not host:
        if not resolved["user"]:
            resolved["user"] = getpass.getuser()
        return resolved
    o = cfg.lookup(host)
    if o.get("hostname"): resolved["host"] = o["hostname"]
    if not resolved["user"] and o.get("user"): resolved["user"] = o["user"]
    if (not port or port == 22) and o.get("port"):
        try: resolved["port"] = int(o["port"])
        except Exception: pass
    ids = o.get("identityfile")
    if ids:
        resolved["identities"].extend([str(Path(p).expanduser()) for p in ids])
    if not resolved["user"]: resolved["user"] = getpass.getuser()
    return resolved

def pkey_sha256(pkey: paramiko.PKey) -> str:
    try:
        digest = hashlib.sha256(pkey.asbytes()).digest()
        return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")
    except Exception:
        return "SHA256:unknown"

def load_private_key_anytype(key_path: str, passphrase: str):
    key_path = str(Path(key_path).expanduser())
    pw = passphrase or None
    last_err = None
    # Thứ tự giống OpenSSH phổ biến: Ed25519, RSA, ECDSA, DSS
    for Loader in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey):
        try:
            if Loader is None: continue
            return Loader.from_private_key_file(key_path, password=pw)
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("Unsupported key format")

class Task:
    def __init__(self, name="", commands=None):
        self.name = name
        self.commands = commands or ["echo 'hello from remote'"]
    def to_dict(self): return {"name": self.name, "commands": self.commands}
    @staticmethod
    def from_dict(d): return Task(d.get("name",""), d.get("commands",[]) or [])

class SSHRunner(threading.Thread):
    def __init__(self, host_string, ui_key_path, passphrase, commands, output_queue):
        super().__init__(daemon=True)
        self.host_string = host_string
        self.ui_key_path = (ui_key_path or "").strip()
        self.passphrase = passphrase or ""
        self.commands = commands or []
        self.output_queue = output_queue
        self.client = None
        self.stopped = False
    
    def _emit(self, text): self.output_queue.put(text)

    def run(self):
        user, host, port = parse_host(self.host_string)
        r = resolve_from_config(user, host, port)

        # Build candidate key list (UI key first, then config, then defaults)
        candidates = []
        if self.ui_key_path:
            candidates.append(self.ui_key_path)
        for p in r["identities"]:
            if p not in candidates:
                candidates.append(p)
        ssh_dir = Path.home() / ".ssh"
        for fname in ("id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"):
            p = str((ssh_dir / fname).expanduser())
            if p not in candidates and Path(p).exists():
                candidates.append(p)
        if not candidates:
            self._emit("[error] No private key candidates found. Pick a key file or set IdentityFile in ~/.ssh/config.\n")
            return

        last_error = None
        for path in candidates:
            if not Path(path).expanduser().exists():
                continue
            try:
                pkey = load_private_key_anytype(path, self.passphrase)
                alg = getattr(pkey, "get_name", lambda: type(pkey).__name__)()
                sha = pkey_sha256(pkey)
                self._emit(f"[info] Trying key {path} (alg={alg}, {sha})...\n")

                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(
                    hostname=r["host"], port=r["port"], username=r["user"],
                    pkey=pkey, allow_agent=False, look_for_keys=False,
                    timeout=15, auth_timeout=15, banner_timeout=15,
                )
                # Connected → run WHOLE task in a single shell so cd/source… persist
                try:
                    transport = self.client.get_transport()
                    if not transport or not transport.is_active():
                        raise RuntimeError("SSH transport is not active.")
                    script_lines = ["set -Eeuo pipefail", "set -x"]
                    script_lines += [c for c in (cmd.strip() for cmd in self.commands) if c]
                    script = "\n".join(script_lines) + "\n"

                    chan = transport.open_session()
                    chan.get_pty()
                    cmd = 'bash -lc "bash -s"'
                    try:
                        chan.exec_command(cmd)
                    except Exception:
                        cmd = 'sh -lc "sh -s"'
                        chan.exec_command(cmd)

                    self._emit(f"[info] Connected as {r['user']}@{r['host']}:{r['port']} using {path} (alg={alg}, {sha})\n")
                    self._emit("$ (task script begins)\n")
                    chan.send(script)
                    chan.shutdown_write()

                    while True:
                        if chan.recv_ready():
                            data = chan.recv(4096).decode(errors="replace")
                            if data: self._emit(data)
                        if chan.recv_stderr_ready():
                            data = chan.recv_stderr(4096).decode(errors="replace")
                            if data: self._emit(data)
                        if chan.exit_status_ready():
                            while chan.recv_ready():
                                data = chan.recv(4096).decode(errors="replace")
                                if data: self._emit(data)
                            while chan.recv_stderr_ready():
                                data = chan.recv_stderr(4096).decode(errors="replace")
                                if data: self._emit(data)
                            rc = chan.recv_exit_status()
                            self._emit(f"[exit code] {rc}\n")
                            break
                finally:
                    try: 
                        self.client.close()
                    except Exception: pass
                self._emit("[info] Done.\n")
                return  # success
            except paramiko.AuthenticationException as e:
                last_error = e
                self._emit("[warn] Auth failed with this key. Trying next...\n")
                continue
            except Exception as e:
                last_error = e
                self._emit(f"[warn] Could not use key {path}: {e}\n")
                continue

        self._emit("[error] Authentication failed with all candidate keys.\n")
        if last_error:
            self._emit(f"        Last error: {last_error}\n")
        self._emit("        Tips:\n"
                   "        - Specify user explicitly in Host, e.g. user@host\n"
                   "        - Check ~/.ssh/config IdentityFile for this host\n"
                   "        - Run: ssh -v <host> to see which key CLI uses\n")
        self._emit("[info] Done.\n")

    def stop(self):
        """Signals the thread to stop and attempts to close the connection."""
        self.stopped = True
        if self.client:
            self._emit("[warn] Stopping in progress...\n")
            try:
                self.client.close()
            except Exception:
                pass

class CommandEditorDialog(tk.Toplevel):
    def __init__(self, parent, task: Task, font=None):
        super().__init__(parent)
        self.title(f"Edit Commands - {task.name or 'Unnamed Task'}")
        self.resizable(True, True)
        self.transient(parent)  # stay on top of parent
        self.grab_set()         # modal
        self.changed_commands = None
        self._build_ui(task, font)
        self._center_on_parent(parent)

    def _build_ui(self, task: Task, font):
        frame = ttk.Frame(self); frame.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(frame, text="Commands (one per line):").pack(anchor="w", pady=(0,6))
        # Text + scrollbar
        text_frame = ttk.Frame(frame); text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(text_frame, height=18, wrap="none", undo=True)
        if font: self.text.configure(font=font)
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        text_frame.rowconfigure(0, weight=1); text_frame.columnconfigure(0, weight=1)

        if task.commands:
            self.text.insert("1.0", "\n".join(task.commands))

        btns = ttk.Frame(frame); btns.pack(fill="x", pady=(8,0))
        save_btn = ttk.Button(btns, text="Save", command=self._on_save)
        cancel_btn = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        save_btn.pack(side="right"); cancel_btn.pack(side="right", padx=(0,8))

        # shortcuts
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _center_on_parent(self, parent):
        self.update_idletasks()
        try:
            px = parent.winfo_rootx(); py = parent.winfo_rooty()
            pw = parent.winfo_width(); ph = parent.winfo_height()
            w = self.winfo_width(); h = self.winfo_height()
            x = px + (pw - w)//2; y = py + (ph - h)//2
            self.geometry(f"+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    def _on_save(self):
        lines = self.text.get("1.0", "end").splitlines()
        self.changed_commands = [c for c in (ln.strip() for ln in lines) if c]
        self.destroy()

    def _on_cancel(self):
        self.changed_commands = None
        self.destroy()

class TaskFrame(ttk.Frame):
    def __init__(self, master, task: Task, run_callback, delete_callback, edit_callback, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.task = task
        self.run_callback = run_callback
        self.delete_callback = delete_callback
        self.edit_callback = edit_callback
        self._build_ui()

    def _build_ui(self):
        # Row 1: Name + buttons
        top = ttk.Frame(self); top.pack(fill="x", pady=(6, 0))
        ttk.Label(top, text="Task name:").pack(side="left")
        self.name_var = tk.StringVar(value=self.task.name)
        ttk.Entry(top, textvariable=self.name_var, width=32).pack(side="left", padx=6)
        ttk.Button(top, text="Run", command=self._on_run).pack(side="right")
        ttk.Button(top, text="Delete", command=self._on_delete).pack(side="right", padx=(0,6))
        ttk.Button(top, text="Edit", command=self._on_edit).pack(side="right", padx=(0,6))

    def _apply_from_ui(self):
        self.task.name = self.name_var.get().strip()

    def _on_run(self):
        self._apply_from_ui()
        self.run_callback(self.task)

    def _on_delete(self):
        if messagebox.askyesno("Confirm", f"Delete task '{self.name_var.get().strip() or '(unnamed)'}'?"):
            self.delete_callback(self)

    def _on_edit(self):
        self._apply_from_ui()
        self.edit_callback(self.task)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SSH Task Runner (compact tasks + popup editor)")
        self.geometry("1050x720")
        self.tasks = []; self.task_frames = []; self.output_queue = queue.Queue()

        # Font: monospace & to hơn
        self.app_mono = tkfont.Font(family="JetBrains Mono", size=11)
        self.app_mono.configure(size=11)
        self.current_ssh_runner = None
        # áp font mặc định cho Text tạo sau đó (nếu muốn)
        self.option_add("*Text.Font", self.app_mono)

        self._build_ui()
        self._load_settings()
        self._load_tasks()
        self._pump_output()

    def _build_ui(self):
        hp = ttk.Frame(self); hp.pack(fill="x", padx=10, pady=10)

        ttk.Label(hp, text="Host (alias or user@host[:port]):").grid(row=0, column=0, sticky="w")
        self.host_var = tk.StringVar(); ttk.Entry(hp, textvariable=self.host_var, width=40).grid(row=0, column=1, padx=6, sticky="w")

        ttk.Label(hp, text="Passphrase (for key):").grid(row=0, column=2, sticky="w", padx=(12,0))
        self.pass_var = tk.StringVar(); ttk.Entry(hp, textvariable=self.pass_var, width=28, show="*").grid(row=0, column=3, padx=6, sticky="w")

        ttk.Label(hp, text="Private key path (optional):").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.key_var = tk.StringVar(); ttk.Entry(hp, textvariable=self.key_var, width=40).grid(row=1, column=1, padx=6, sticky="w", pady=(6,0))
        ttk.Button(hp, text="Browse...", command=self._browse_key).grid(row=1, column=2, sticky="w", padx=(12,0), pady=(6,0))

        btn_frame = ttk.Frame(hp); btn_frame.grid(row=0, column=4, rowspan=2, sticky="e", padx=(20,0))
        # New "Close Connection" button
        self.close_btn = ttk.Button(btn_frame, text="Close Connection", command=self._close_connection, state="disabled")
        self.close_btn.pack(side="top", fill="x", pady=(0, 6))
        ttk.Button(btn_frame, text="Add Task", command=self._add_task).pack(side="top", fill="x")
        ttk.Button(btn_frame, text="Save All Tasks", command=self._save_tasks).pack(side="top", fill="x", pady=6)
        ttk.Button(btn_frame, text="Load Tasks", command=self._load_tasks).pack(side="top", fill="x")

        container = ttk.Frame(self); container.pack(fill="both", expand=True, padx=10)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.tasks_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y"); self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.tasks_frame, anchor="nw")
        self.tasks_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        out_frame = ttk.LabelFrame(self, text="Remote Output")
        out_frame.pack(fill="both", expand=False, padx=10, pady=(6,10))
        self.output_text = tk.Text(out_frame, height=12, wrap="word", state="disabled")
        self.output_text.configure(font=self.app_mono)
        self.output_text.pack(fill="both", expand=True)

    def _browse_key(self):
        path = filedialog.askopenfilename(
            title="Select private key",
            initialdir=str(Path.home() / ".ssh"),
            filetypes=[("Private key files", "*"), ("All files", "*.*")]
        )
        if path: self.key_var.set(path)

    def _add_task(self, task=None):
        if task is None:
            task = Task(name="New task", commands=["uname -a", "whoami", "uptime"])
        # luôn lưu vào self.tasks (sửa bug save)
        self.tasks.append(task)
        frame = TaskFrame(
            self.tasks_frame, task,
            run_callback=self._run_task,
            delete_callback=self._delete_task_frame,
            edit_callback=self._edit_task_commands
        )
        frame.pack(fill="x", expand=True, padx=4, pady=4)
        self.task_frames.append(frame)

    def _delete_task_frame(self, frame: TaskFrame):
        try: self.tasks.remove(frame.task)
        except ValueError: pass
        frame.destroy(); self.task_frames.remove(frame)

    def _gather_tasks_from_ui(self):
        for tf in self.task_frames: tf._apply_from_ui()

    def _save_tasks(self):
        # lấy thẳng từ UI frames để chắc chắn
        to_save = []
        for tf in self.task_frames:
            tf._apply_from_ui()
            to_save.append(tf.task)
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in to_save], f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Saved", f"Tasks saved to {TASKS_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tasks: {e}")

    def _load_tasks(self):
        for tf in list(self.task_frames): tf.destroy()
        self.task_frames.clear(); self.tasks.clear()
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data: self._add_task(Task.from_dict(item))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load tasks: {e}")
        else:
            self._add_task()

    def _append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _pump_output(self):
        try:
            while True:
                self._append_output(self.output_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(80, self._pump_output)

    def _save_settings(self):
        data = {
            "host": self.host_var.get().strip(),
            "passphrase": self.pass_var.get(),
            "private_key_path": self.key_var.get().strip(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _close_connection(self):
        if self.current_ssh_runner:
            self.current_ssh_runner.stop()
            self.current_ssh_runner = None
            self._append_output("[info] Connection closed by user.\n")
            self.close_btn.config(state="disabled")

    def _run_task(self, task: Task):
        host = self.host_var.get().strip()
        if not host:
            messagebox.showwarning("Missing host", "Please enter Host (alias or user@host[:port]).")
            return
        if self.current_ssh_runner and self.current_ssh_runner.is_alive():
            messagebox.showwarning("Busy", "A task is already running. Please wait or close the connection.")
            return
        
        # Clear output and disable the close button while running
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.close_btn.config(state="enabled")
        
        self._save_settings()
        
        # Create and start the new runner, then store it
        self.current_ssh_runner = SSHRunner(host, self.key_var.get().strip(), self.pass_var.get(), task.commands, self.output_queue)
        self.current_ssh_runner.start()

    def _load_settings(self):
        default_key = Path.home() / ".ssh" / "id_rsa"
        if default_key.exists(): self.key_var.set(str(default_key))
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.host_var.set(data.get("host", self.host_var.get()))
                self.pass_var.set(data.get("passphrase", ""))
                self.key_var.set(data.get("private_key_path", self.key_var.get()))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load settings: {e}")

    def _edit_task_commands(self, task: Task):
        dlg = CommandEditorDialog(self, task, font=self.app_mono)
        self.wait_window(dlg)
        if dlg.changed_commands is not None:
            task.commands = dlg.changed_commands
            # Có thể hiển thị count hoặc preview ngắn nếu muốn
            messagebox.showinfo("Updated", f"Saved {len(task.commands)} command(s) for '{task.name or 'Unnamed Task'}'.")

if __name__ == "__main__":
    try:
        app = App(); app.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", str(e))
