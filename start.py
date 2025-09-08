# start.py
from __future__ import annotations

import os
import logging

from core import App, load_config_from_disk, save_config_to_disk
from gui import gui_main


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logging.info("Bootstrapping Screen OCR Box → ChatGPT…")
    workdir = os.getcwd()
    logging.info("Working dir: %s", workdir)
    logging.info("Starting GUI…")

    # Load portable config (creates defaults if missing)
    cfg = load_config_from_disk()

    # Build the app (client will be created on-demand by GUI via app.ensure_client())
    app = App(cfg, client=None)

    try:
        gui_main(app, cfg, log_path=os.path.join(workdir, "app.log"))
    finally:
        # Persist any last config changes on close
        try:
            save_config_to_disk(app.cfg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
