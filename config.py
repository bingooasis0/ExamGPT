# config.py
from __future__ import annotations
import json, os, logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.json"

@dataclass
class Config:
    # Core
    region: Optional[Tuple[int, int, int, int]] = None  # (left, top, width, height)
    show_region_overlay: bool = False

    # OCR
    ocr_engine: str = "auto"        # auto | tess | easy
    ocr_lang: str = "eng"
    ocr_math_mode: bool = False
    ocr_adaptive: bool = False
    ocr_block: int = 25
    ocr_c: int = 10

    # OpenAI
    openai_api_env: str = "OPENAI_API_KEY"
    model: str = "gpt-5"
    max_completion_tokens: int = 256
    system_prompt: str = (
        "You are a helpful assistant. Be concise and accurate. "
        "When solving, show working only if needed."
    )

    # Logging
    log_path: str = "app.log"

    # Legacy/ignored (prevent warning spam in load)
    tesseract_cmd: Optional[str] = None
    auto_copy_answer_to_clipboard: Optional[bool] = None
    auto_copy_ocr_text_to_clipboard: Optional[bool] = None
    region_mode: Optional[str] = None
    window_title_contains: Optional[str] = None
    use_client_area: Optional[bool] = None
    relative_region: Optional[Tuple[int, int, int, int]] = None
    hotkey_select_region: Optional[str] = None
    hotkey_ocr_only: Optional[str] = None
    hotkey_send_to_chatgpt: Optional[str] = None
    hotkey_quit: Optional[str] = None

def _existing_config_path() -> str:
    for p in ("config.json", "config.yaml", "config.yml"):
        if os.path.exists(p):
            return p
    return DEFAULT_CONFIG_PATH

def load_config(path: Optional[str] = None) -> Config:
    path = path or _existing_config_path()
    if not os.path.exists(path):
        return Config()
    try:
        if path.endswith((".yaml", ".yml")):
            try:
                import yaml  # type: ignore
            except Exception:
                log.warning("YAML not available; ignoring yaml file. Using defaults.")
                return Config()
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        known = set(k for k in Config().__dict__.keys())
        unknown = [k for k in data.keys() if k not in known]
        if unknown:
            log.warning("Ignoring unknown config keys: %s", unknown)

        cfg = Config(**{k: v for k, v in data.items() if k in known})
        return cfg
    except Exception as e:
        log.exception("Failed to read config; using defaults: %s", e)
        return Config()

def save_config(cfg: Config, path: Optional[str] = None) -> None:
    path = path or _existing_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, indent=2)
