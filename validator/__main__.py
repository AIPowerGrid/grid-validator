# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Module entrypoint for `python -m validator` and PyInstaller builds."""

import multiprocessing

from validator.cli import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
