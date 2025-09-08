# core.py
from __future__ import annotations

import logging
import json, os
from dataclasses import asdict
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from PIL import ImageGrab, Image
from ocr import run_ocr
from overlay import RegionSelector, RegionOverlay
from mini_math import solve_if_simple

log = logging.getLogger(__name__)
CONFIG_FILE = os.path.join(os.getcwd(), "config.json")


def load_config_from_disk() -> Config:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d.get("region"), list) and len(d["region"]) == 4:
            d["region"] = tuple(d["region"])
        return Config(**d)
    except Exception:
        return Config()

def save_config_to_disk(cfg: Config):
    d = asdict(cfg)
    if isinstance(d.get("region"), tuple):
        d["region"] = list(d["region"])
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

@dataclass
class Config:
    # Region / overlay
    region: Optional[Tuple[int, int, int, int]] = None
    show_region_overlay: bool = False

    # OCR
    ocr_engine: str = "easyocr"
    ocr_lang: str = "eng"
    ocr_math_mode: bool = False
    ocr_adaptive: bool = True
    ocr_block: int = 25
    ocr_c: int = 10

    # OpenAI
    openai_api_env: str = "OPENAI_API_KEY"
    model: str = "gpt-5"
    max_tokens: int = 256
    system_prompt: str = "You are a helpful assistant."


class ChatGPTClient:
    """
    Implemented in openai_client.py. Only here for type hints.
    """
    def ask(self, system_prompt: str, user_text: str, max_tokens: int) -> str: ...
    def test_poem(self) -> str: ...
    def reconfigure(self, api_env: str, model: str, max_tokens: int) -> None: ...
    # no-op placeholders to keep type checkers happy


class App:
    def __init__(self, cfg: Config, client: Optional[ChatGPTClient] = None):
        self.cfg = cfg
        self.client = client
        self.ui_root = None
        self.write_home: Callable[[str], None] = lambda s: None
        self.overlay: Optional[RegionOverlay] = None

    def save_cfg(self):
        try:
            save_config_to_disk(self.cfg)
        except Exception:
            pass

    def ensure_client(self):
        if not self.client:
            from openai_client import ChatGPTClient
            self.client = ChatGPTClient(self.cfg.openai_api_env, self.cfg.model, self.cfg.max_tokens)

    def set_ui(self, root, write_func):
        self.ui_root = root
        self.write_home = write_func
        # Build overlay once; outline shows only if checkbox is on
        self.overlay = RegionOverlay(root)
        if self.cfg.show_region_overlay and self.cfg.region:
            self.overlay.show(self.cfg.region)

    # ---------- Region selection ----------
    def action_select_region(self) -> None:
        if not self.ui_root:
            raise RuntimeError("UI root not set")

        self.write_home("[info] Starting region selection overlay...\n")

        # Temporarily hide outline while selecting to avoid confusion
        outline_shown = bool(self.overlay and self.cfg.show_region_overlay)
        if outline_shown:
            try:
                self.overlay.hide()
            except Exception:
                pass

        try:
            selector = RegionSelector(self.ui_root)
            sel = selector.show()
        finally:
            # Restore existing outline if enabled
            if outline_shown and self.cfg.region and self.overlay:
                try:
                    self.overlay.show(self.cfg.region)
                except Exception:
                    pass

        if sel:
            self.cfg.region = sel
            l, t, w, h = sel
            self.write_home(f"[info] Region saved: left={l} top={t} width={w} height={h}\n")
            if self.cfg.show_region_overlay and self.overlay:
                try:
                    self.overlay.update_region(sel)
                    self.overlay.show(sel)
                    self.save_cfg()
                except Exception:
                    pass
        else:
            self.write_home("[warn] Region selection cancelled.\n")

    def toggle_overlay(self):
        if not self.overlay:
            return
        if self.cfg.show_region_overlay and self.cfg.region:
            self.overlay.show(self.cfg.region)
        else:
            self.overlay.hide()
            self.save_cfg()

    # ---------- OCR actions ----------
    def _grab_region_image(self) -> Optional[Image.Image]:
        if not self.cfg.region:
            self.write_home("[warn] No region set.\n")
            return None
        l, t, w, h = self.cfg.region
        box = (l, t, l + w, t + h)
        try:
            img = ImageGrab.grab(bbox=box, all_screens=True)
            return img
        except Exception as e:
            log.error("Screen grab failed: %s", e)
            self.write_home(f"[error] Screen grab failed: {e}\n")
            return None

    def action_ocr_only(self, writer: Optional[Callable[[str], None]] = None):
        out = writer or self.write_home
        out("[ocr]\n")
        img = self._grab_region_image()
        if not img:
            return
        text = run_ocr(
            img,
            engine=self.cfg.ocr_engine,
            lang=self.cfg.ocr_lang,
            math_mode=self.cfg.ocr_math_mode,
            adaptive=self.cfg.ocr_adaptive,
            block=self.cfg.ocr_block,
            c=self.cfg.ocr_c,
        )
        out(text.strip() + "\n")

        def action_send_to_chatgpt(self):
            self.write_home("[info] Performing OCR and sending to ChatGPT...\n")
            img = self._grab_region_image()
            if not img:
                return
            text = run_ocr(
                img,
                engine=self.cfg.ocr_engine,
                lang=self.cfg.ocr_lang,
                math_mode=self.cfg.ocr_math_mode,
                adaptive=self.cfg.ocr_adaptive,
                block=self.cfg.ocr_block,
                c=self.cfg.ocr_c,
            )

            text = text.strip()
            if not text:
                self.write_home("[error] OCR produced no text.\n")
                return
            try:
                # Make sure a client exists (in case the GUI hasn’t hit “Apply Settings” yet)
                if self.client is None:
                    from openai_client import ChatGPTClient  # respect your existing design
                    self.client = ChatGPTClient(self.cfg.openai_api_env, self.cfg.model, self.cfg.max_tokens)
                answer = self.client.ask(self.cfg.system_prompt, text, self.cfg.max_tokens)
                if not answer.strip():
                    self.write_home("[error] Model returned empty text.\n")
                else:
                    self.write_home("[answer]\n" + answer.strip() + "\n")
            except Exception as e:
                log.exception("OpenAI error")
                self.write_home(f"[error] {e}\n")
