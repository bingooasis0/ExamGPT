# overlay.py
from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple
from mini_math import solve_if_simple


# ----------------------------
# Region outline (non-blocking)
# ----------------------------
class RegionOverlay:
    """
    Draws a non-blocking outline around the region using four 2px Toplevels.
    No fullscreen, no tint, no input stealing.
    """
    def __init__(self, root: tk.Tk, color: str = "#00ffc2", thickness: int = 2):
        self.root = root
        self.color = color
        self.thickness = max(1, int(thickness))

        self._top = self._mk_bar()
        self._bottom = self._mk_bar()
        self._left = self._mk_bar()
        self._right = self._mk_bar()

        self._shown = False
        self._region: Optional[Tuple[int, int, int, int]] = None

        # Hide outline when main window minimizes; re-apply when restored.
        self.root.bind("<Unmap>", lambda e: self.hide(), add="+")
        self.root.bind("<Map>", lambda e: (self._shown and self._region and self._apply(self._region)), add="+")

    def _mk_bar(self) -> tk.Toplevel:
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=self.color, highlightthickness=0, bd=0)
        w.withdraw()
        return w

    def _apply(self, region: Tuple[int, int, int, int]) -> None:
        l, t, w, h = region
        th = self.thickness

        # Top bar
        self._top.geometry(f"{w}x{th}+{l}+{t}")
        # Bottom bar
        self._bottom.geometry(f"{w}x{th}+{l}+{t + h - th}")
        # Left bar
        self._left.geometry(f"{th}x{h}+{l}+{t}")
        # Right bar
        self._right.geometry(f"{th}x{h}+{l + w - th}+{t}")

        for bar in (self._top, self._bottom, self._left, self._right):
            bar.deiconify()
            bar.lift()

    def show(self, region: Tuple[int, int, int, int]) -> None:
        self._region = region
        self._shown = True
        self._apply(region)

    def update_region(self, region: Tuple[int, int, int, int]) -> None:
        self._region = region
        if self._shown:
            self._apply(region)

    def hide(self) -> None:
        self._shown = False
        for bar in (self._top, self._bottom, self._left, self._right):
            bar.withdraw()

    def destroy(self) -> None:
        for bar in (self._top, self._bottom, self._left, self._right):
            try:
                bar.destroy()
            except Exception:
                pass


# ----------------------------
# Region selection (modal)
# ----------------------------
class RegionSelector:
    """
    Drag-to-select region overlay. Uses a single border-only Canvas rectangle
    on a nearly transparent full-screen Toplevel. No 'fullscreen' flag (so no Tk errors).
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.sel_win = tk.Toplevel(self.root)
        self.sel_win.overrideredirect(True)
        self.sel_win.attributes("-topmost", True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.sel_win.geometry(f"{sw}x{sh}+0+0")

        # Almost fully transparent (no visual wash), but still receives events.
        try:
            self.sel_win.attributes("-alpha", 0.02)
        except Exception:
            pass

        self.sel_win.configure(bg="#000000", highlightthickness=0, bd=0)
        self.sel_win.config(cursor="crosshair")

        # IMPORTANT: don't pass empty string as a color; use the window's bg
        self.canvas = tk.Canvas(self.sel_win, highlightthickness=0, bd=0, bg=self.sel_win["bg"])
        self.canvas.pack(fill="both", expand=True)

        self._start: Optional[Tuple[int, int]] = None
        self._rect = None
        self._result: Optional[Tuple[int, int, int, int]] = None

        # Events
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.sel_win.bind("<Escape>", self._on_escape)

        # Modal
        self.sel_win.lift()
        try:
            self.sel_win.grab_set()
        except Exception:
            pass

    def _on_press(self, e):
        self._start = (e.x_root, e.y_root)
        if self._rect is not None:
            self.canvas.delete(self._rect)
            self._rect = None

    def _on_drag(self, e):
        if not self._start:
            return
        x0, y0 = self._start
        x1, y1 = e.x_root, e.y_root
        l, t = min(x0, x1), min(y0, y1)
        r, b = max(x0, x1), max(y0, y1)

        if self._rect is None:
            self._rect = self.canvas.create_rectangle(l, t, r, b, outline="#00ffc2", width=2)
        else:
            self.canvas.coords(self._rect, l, t, r, b)

    def _on_release(self, e):
        if not self._start:
            return self._cancel()
        x0, y0 = self._start
        x1, y1 = e.x_root, e.y_root
        l, t = min(x0, x1), min(y0, y1)
        r, b = max(x0, x1), max(y0, y1)
        w, h = r - l, b - t

        if w < 5 or h < 5:
            return self._cancel()

        self._result = (l, t, w, h)
        self._close()

    def _on_escape(self, _e):
        self._cancel()

    def _cancel(self):
        self._result = None
        self._close()

    def _close(self):
        try:
            self.sel_win.grab_release()
        except Exception:
            pass
        self.sel_win.destroy()

    def show(self) -> Optional[Tuple[int, int, int, int]]:
        self.sel_win.wait_window()  # modal
        return self._result
