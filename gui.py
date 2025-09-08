# gui.py
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from core import Config, App
from openai_client import ChatGPTClient


# =======================
# Theme: Embers (dark)
# =======================
THEME = {
    # Base surfaces
    "bg":        "#121a25",  # app background (deep navy)
    "panel":     "#172131",  # cards / panels
    "surface":   "#1f2a3b",  # text areas

    # Text
    "fg":        "#E8EDF5",
    "muted":     "#A7B0C0",

    # Palette accents
    "indigo":    "#41436A",
    "plum":      "#984063",
    "coral":     "#F64668",
    "peach":     "#FE9677",

    # Controls
    "btn":           "#2a3448",
    "btn_hover":     "#364057",
    "btn_active":    "#41436A",
    "btn_text":      "#E8EDF5",

    "entry_bg":      "#1a2434",
    "entry_fg":      "#E8EDF5",
}

# ----- colored console writer -----
_TAG_RE = re.compile(r"\[(ready|info|answer|ocr|error|warn)\]")

def console_write(widget: tk.Text, text: str):
    widget.config(state="normal")
    pos = 0
    while True:
        m = _TAG_RE.search(text, pos)
        if not m:
            widget.insert("end", text[pos:])
            break
        widget.insert("end", text[pos:m.start()])
        tag = m.group(1)
        widget.insert("end", m.group(0), f"tag_{tag}")
        pos = m.end()
    widget.see("end")
    widget.config(state="disabled")


def _format_region(r):
    if not r:
        return "(none)"
    l, t, w, h = r
    return f"{l},{t},{w},{h}"


def gui_main(app: App, cfg: Config, log_path: str):
    root = tk.Tk()
    root.title("Screen OCR Box → ChatGPT")
    root.geometry("1060x640+200+120")

    # ------------------
    # ttk style (clam)
    # ------------------
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Global defaults
    style.configure(".",
        background=THEME["bg"],
        foreground=THEME["fg"]
    )
    root.configure(bg=THEME["bg"])

    # Frames / cards / labels
    style.configure("Dark.TFrame", background=THEME["bg"])
    style.configure("Card.TFrame", background=THEME["panel"])
    style.configure("Dark.TLabel", background=THEME["bg"], foreground=THEME["fg"])
    style.configure("Card.TLabel", background=THEME["panel"], foreground=THEME["fg"])

    # Buttons
    style.configure("Dark.TButton",
        background=THEME["btn"],
        foreground=THEME["btn_text"],
        padding=(12, 6),
        borderwidth=0
    )
    style.map("Dark.TButton",
        background=[("active", THEME["btn_hover"]), ("pressed", THEME["btn_active"])],
        foreground=[("disabled", "#7f8aa3")]
    )

    style.configure("Accent.TButton",
        background=THEME["coral"],
        foreground="#111318",
        padding=(12, 6),
        borderwidth=0
    )
    style.map("Accent.TButton",
        background=[("active", THEME["peach"]), ("pressed", THEME["peach"])],
        foreground=[("disabled", "#303846")]
    )

    # Entries
    style.configure("Dark.TEntry",
        fieldbackground=THEME["entry_bg"],
        foreground=THEME["entry_fg"],
        bordercolor=THEME["indigo"],
        lightcolor=THEME["indigo"],
        darkcolor=THEME["indigo"],
        insertcolor=THEME["entry_fg"],
    )
    style.map("Dark.TEntry",
        fieldbackground=[("readonly", THEME["entry_bg"]), ("!disabled", THEME["entry_bg"])],
        foreground=[("readonly", THEME["entry_fg"]), ("!disabled", THEME["entry_fg"])],
        bordercolor=[("focus", THEME["indigo"])],
        lightcolor=[("focus", THEME["indigo"])],
        darkcolor=[("focus", THEME["indigo"])]
    )

    # ComboBox
    style.configure("Dark.TCombobox",
        fieldbackground=THEME["entry_bg"],
        background=THEME["entry_bg"],
        foreground=THEME["entry_fg"],
        arrowcolor=THEME["entry_fg"]
    )
    style.map("Dark.TCombobox",
        fieldbackground=[("readonly", THEME["entry_bg"]), ("!disabled", THEME["entry_bg"])],
        background=[("active", THEME["entry_bg"])],
        foreground=[("readonly", THEME["entry_fg"]), ("!disabled", THEME["entry_fg"])],
        arrowcolor=[("disabled", "#6b7386"), ("!disabled", THEME["entry_fg"])]
    )

    # Checkbuttons — keep dark (prevents white hover/flash)
    style.configure("Dark.TCheckbutton",
        background=THEME["bg"],
        foreground=THEME["fg"]
    )
    style.map("Dark.TCheckbutton",
        background=[("active", THEME["bg"]), ("selected", THEME["bg"]), ("!selected", THEME["bg"])],
        foreground=[("active", THEME["fg"]), ("!active", THEME["fg"])]
    )

    # ------------- Layout -------------
    stack = ttk.Frame(root, style="Dark.TFrame")
    stack.pack(fill="both", expand=True, padx=8, pady=8)

    # nav (slightly raised panel)
    nav = ttk.Frame(stack, width=160, style="Card.TFrame")
    nav.pack(side="left", fill="y", padx=(0, 10))
    main = ttk.Frame(stack, style="Dark.TFrame")
    main.pack(side="right", fill="both", expand=True)

    pages = {}

    def show(name: str):
        for n, f in pages.items():
            f.pack_forget()
        pages[name].pack(fill="both", expand=True)

    # ------------- Home -------------
    home = ttk.Frame(main, style="Dark.TFrame")
    ttk.Label(home, text="Control Panel", style="Dark.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))

    topbar = ttk.Frame(home, style="Card.TFrame")
    topbar.pack(fill="x")

    # coords + overlay toggle
    coords_var = tk.StringVar(value=_format_region(cfg.region))
    ttk.Label(topbar, text="Region:", style="Card.TLabel").pack(side="left", padx=(10, 6), pady=10)

    coords_box = ttk.Entry(topbar, textvariable=coords_var, width=28, style="Dark.TEntry", state="readonly")
    coords_box.pack(side="left", padx=(0, 12), pady=10)

    overlay_var = tk.BooleanVar(value=bool(cfg.show_region_overlay))
    ttk.Checkbutton(
        topbar,
        text="Show selected region overlay",
        variable=overlay_var,
        style="Dark.TCheckbutton"
    ).pack(side="right", padx=10, pady=10)

    # Action row
    row = ttk.Frame(home, style="Card.TFrame")
    row.pack(fill="x", pady=(10, 8))
    ttk.Button(row, text="Select New Region", style="Dark.TButton",
               command=lambda: _select_region_update()).pack(side="left")
    ttk.Button(row, text="Preview OCR", style="Dark.TButton",
               command=lambda: app.action_ocr_only(lambda s: console_write(home_out, s))).pack(side="left", padx=(8, 0))
    ttk.Button(row, text="Ask ChatGPT", style="Accent.TButton",
               command=lambda: app.action_send_to_chatgpt(lambda s: console_write(home_out, s))).pack(side="left", padx=(8, 0))
    ttk.Button(row, text="Clear", style="Dark.TButton",
               command=lambda: _clear_text(home_out)).pack(side="left", padx=(8, 0))

    # Console (with colored tags)
    home_out = tk.Text(home, height=16, bg=THEME["surface"], fg=THEME["fg"],
                       insertbackground=THEME["fg"], bd=0, highlightthickness=0)
    home_out.pack(fill="both", expand=True, pady=(8, 0))
    home_out.config(state="disabled")

    # tag colors (kept as you specified)
    home_out.tag_config("tag_ready", foreground="#ffd860")    # yellow
    home_out.tag_config("tag_info",  foreground="#ffa955")    # orange
    home_out.tag_config("tag_ocr",   foreground="#58a6ff")    # blue
    home_out.tag_config("tag_answer",foreground="#2dd36f")    # green
    home_out.tag_config("tag_error", foreground="#ff6b6b")    # red
    home_out.tag_config("tag_warn",  foreground="#ffcc66")    # amber

    console_write(home_out, "[ready]\n")

    pages["home"] = home

    # ------------- OCR -------------
    ocrp = ttk.Frame(main, style="Dark.TFrame")
    ttk.Label(ocrp, text="OCR", style="Dark.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))

    r1 = ttk.Frame(ocrp, style="Card.TFrame"); r1.pack(anchor="w", pady=6, fill="x")
    ttk.Label(r1, text="Engine:", style="Card.TLabel").pack(side="left", padx=(10, 6), pady=8)
    eng = tk.StringVar(value=cfg.ocr_engine)
    ttk.Combobox(r1, textvariable=eng, values=["auto", "easyocr", "tesseract"], state="readonly",
                 style="Dark.TCombobox", width=12).pack(side="left")

    ttk.Label(r1, text="Language:", style="Card.TLabel").pack(side="left", padx=(12, 6))
    lng = tk.StringVar(value=cfg.ocr_lang)
    ttk.Entry(r1, textvariable=lng, width=10, style="Dark.TEntry").pack(side="left")

    # Options row
    r2 = ttk.Frame(ocrp, style="Card.TFrame"); r2.pack(anchor="w", pady=6, fill="x")
    adaptive = tk.BooleanVar(value=True)  # default ON per your request
    ttk.Checkbutton(r2, text="Adaptive Threshold", variable=adaptive, style="Dark.TCheckbutton").pack(side="left", padx=(10, 10), pady=8)
    math_mode = tk.BooleanVar(value=cfg.ocr_math_mode)
    ttk.Checkbutton(r2, text="Math mode (gridline removal)", variable=math_mode, style="Dark.TCheckbutton").pack(side="left", padx=(0, 10), pady=8)

    # Params
    r3 = ttk.Frame(ocrp, style="Card.TFrame"); r3.pack(anchor="w", pady=6, fill="x")
    blk = tk.IntVar(value=cfg.ocr_block)
    cc = tk.IntVar(value=cfg.ocr_c)
    ttk.Label(r3, text="Block:", style="Card.TLabel").pack(side="left", padx=(10, 6))
    ttk.Entry(r3, textvariable=blk, width=6, style="Dark.TEntry").pack(side="left")
    ttk.Label(r3, text="C:", style="Card.TLabel").pack(side="left", padx=(12, 6))
    ttk.Entry(r3, textvariable=cc, width=6, style="Dark.TEntry").pack(side="left")

    # OCR output + buttons
    ocr_out = tk.Text(ocrp, height=12, bg=THEME["surface"], fg=THEME["fg"], insertbackground=THEME["fg"], bd=0, highlightthickness=0)
    ocr_out.pack(fill="both", expand=True, pady=(8, 0))

    def _save_ocr_cfg():
        cfg.ocr_engine = eng.get().strip() or "auto"
        cfg.ocr_lang = lng.get().strip() or "eng"
        cfg.ocr_adaptive = bool(adaptive.get())
        cfg.ocr_math_mode = bool(math_mode.get())
        try:
            cfg.ocr_block = int(blk.get())
            cfg.ocr_c = int(cc.get())
        except Exception:
            pass

    def _ocr_preview():
        _save_ocr_cfg()
        app.action_ocr_only(lambda s: console_write(ocr_out, s))

    rbtn = ttk.Frame(ocrp, style="Card.TFrame"); rbtn.pack(anchor="w", pady=8)
    ttk.Button(rbtn, text="Save OCR Settings", style="Dark.TButton", command=_save_ocr_cfg).pack(side="left", padx=(0, 8))
    ttk.Button(rbtn, text="Preview OCR (from region)", style="Dark.TButton", command=_ocr_preview).pack(side="left")

    pages["ocr"] = ocrp

    # ------------- OpenAI -------------
    ai = ttk.Frame(main, style="Dark.TFrame")
    ttk.Label(ai, text="OpenAI", style="Dark.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))

    a1 = ttk.Frame(ai, style="Card.TFrame"); a1.pack(anchor="w", pady=6, fill="x")
    ttk.Label(a1, text="API Key Env Var:", style="Card.TLabel").pack(side="left", padx=(10, 6), pady=8)
    api_env = tk.StringVar(value=cfg.openai_api_env)
    ttk.Entry(a1, textvariable=api_env, width=22, style="Dark.TEntry").pack(side="left")

    ttk.Label(a1, text="Model:", style="Card.TLabel").pack(side="left", padx=(12, 6))
    model = tk.StringVar(value=cfg.model)
    ttk.Entry(a1, textvariable=model, width=18, style="Dark.TEntry").pack(side="left")

    ttk.Label(a1, text="Response Tokens:", style="Card.TLabel").pack(side="left", padx=(12, 6))
    max_tok = tk.IntVar(value=cfg.max_tokens)
    ttk.Entry(a1, textvariable=max_tok, width=8, style="Dark.TEntry").pack(side="left")

    # System prompt
    sp = tk.Text(ai, height=6, bg=THEME["surface"], fg=THEME["fg"], insertbackground=THEME["fg"], bd=0, highlightthickness=0)
    sp.pack(fill="x", pady=(8, 8))
    sp.insert("end", cfg.system_prompt)

    ai_out = tk.Text(ai, height=12, bg=THEME["surface"], fg=THEME["fg"], insertbackground=THEME["fg"], bd=0, highlightthickness=0)
    ai_out.pack(fill="both", expand=True)

    def _apply_ai():
        cfg.openai_api_env = api_env.get().strip() or "OPENAI_API_KEY"
        cfg.model = model.get().strip() or "gpt-5"
        cfg.max_tokens = int(max_tok.get())
        cfg.system_prompt = sp.get("1.0", "end").strip()
        if app.client:
            app.client.reconfigure(cfg.openai_api_env, cfg.model, cfg.max_tokens)
        else:
            app.client = ChatGPTClient(cfg.openai_api_env, cfg.model, cfg.max_tokens)

    def _test_poem():
        try:
            _apply_ai()
            poem = app.client.test_poem()
            ai_out.delete("1.0", "end")
            ai_out.insert("end", poem or "(empty)")
        except Exception as e:
            ai_out.delete("1.0", "end")
            ai_out.insert("end", f"[error] {e}")

    arow = ttk.Frame(ai, style="Card.TFrame"); arow.pack(anchor="w", pady=8)
    ttk.Button(arow, text="Test API (poem)", style="Dark.TButton", command=_test_poem).pack(side="left", padx=(0, 8))
    ttk.Button(arow, text="Apply Settings", style="Dark.TButton", command=_apply_ai).pack(side="left")

    pages["openai"] = ai

    # ------------- Logs -------------
    logs = ttk.Frame(main, style="Dark.TFrame")
    ttk.Label(logs, text="Logs", style="Dark.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))
    tbox = tk.Text(logs, height=22, bg=THEME["surface"], fg=THEME["fg"], insertbackground=THEME["fg"], bd=0, highlightthickness=0)
    tbox.pack(fill="both", expand=True)

    def refresh_logs():
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                tbox.delete("1.0", "end")
                tbox.insert("end", f.read())
                tbox.see("end")
        except Exception as e:
            tbox.insert("end", f"[error] {e}\n")

    btnrow = ttk.Frame(logs, style="Card.TFrame"); btnrow.pack(anchor="w", pady=8)
    ttk.Button(btnrow, text="Refresh", style="Dark.TButton", command=refresh_logs).pack(side="left", padx=(0, 8))
    ttk.Button(btnrow, text="Clear", style="Dark.TButton", command=lambda: tbox.delete("1.0", "end")).pack(side="left")

    pages["logs"] = logs

    # ------------- About -------------
    about = ttk.Frame(main, style="Dark.TFrame")
    ttk.Label(about, text="About", style="Dark.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))
    ttk.Label(about, text="ExamGPT — Screen OCR Box to ChatGPT", style="Dark.TLabel").pack(anchor="w")
    pages["about"] = about

    # ------------- nav buttons -------------
    def nav_btn(txt, key):
        return ttk.Button(nav, text=txt, style="Dark.TButton", command=lambda: show(key))

    nav_btn("Home", "home").pack(fill="x", pady=4, padx=8)
    nav_btn("OCR", "ocr").pack(fill="x", pady=4, padx=8)
    nav_btn("OpenAI", "openai").pack(fill="x", pady=4, padx=8)
    nav_btn("Logs", "logs").pack(fill="x", pady=4, padx=8)
    nav_btn("About", "about").pack(fill="x", pady=4, padx=8)

    # ---------- helpers ----------
    def _clear_text(widget: tk.Text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.config(state="disabled")

    def _select_region_update():
        app.action_select_region()
        coords_var.set(_format_region(cfg.region))
        coords_box.configure(state="readonly")
        if overlay_var.get():
            cfg.show_region_overlay = True
            app.toggle_overlay()

    def _toggle_overlay():
        cfg.show_region_overlay = bool(overlay_var.get())
        app.toggle_overlay()

    overlay_var.trace_add("write", lambda *_: _toggle_overlay())

    # Hotkeys
    root.bind_all("<Control-Shift-S>", lambda e: _select_region_update())
    root.bind_all("<Control-Shift-O>", lambda e: app.action_ocr_only(lambda s: console_write(home_out, s)))
    root.bind_all("<Control-Shift-G>", lambda e: app.action_send_to_chatgpt(lambda s: console_write(home_out, s)))

    # Provide handles
    app.set_ui(root, lambda s: console_write(home_out, s))

    

    if app.client is None:
        app.ensure_client()

    show("home")
    root.mainloop()
