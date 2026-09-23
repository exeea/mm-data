#!/usr/bin/env python3
# Copyright (C) 2026 The MegaMek Team. SPDX-License-Identifier: GPL-3.0-or-later
"""The 64 by 64 cactus detail map (CC0-1.0, procedural): pale, sage-tinted ribs with dark grooves and small spine
tufts along the rib crests. Like the other foliage maps it is tinted by the model's vertex colours; U runs across the
ribs and V up the stem. Usage, from the mm-data root: python tools/build_cactus_texture.py"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / 'data/models/board/textures/foliage/cactus.png'
SIZE, RIBS = 64, 8

u = (np.arange(SIZE) + .5) / SIZE
v = u[:, None]
phase = (u[None, :] * RIBS) % 1.0
# A rounded rib: bright crest, dark groove between ribs.
rib = np.clip(np.sin(phase * np.pi), 0, 1) ** .6
rng = np.random.default_rng(7)
mottle = 1 + .04 * rng.standard_normal((SIZE, SIZE))
tone = (.70 + .30 * rib) * mottle
# Spine tufts: small pale dots on the crests, staggered up the stem.
row = (v * 16 + (np.floor(u[None, :] * RIBS) % 2) * .5) % 1.0
tuft = (np.abs(phase - .5) < .12) & (np.abs(row - .5) < .09)
rgb = np.stack([tone * .95, tone * .96, tone * .82], -1)
rgb = np.where(tuft[..., None], np.array([1.0, .98, .9]), rgb)
Image.fromarray(np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8), 'RGB').save(OUT, optimize=True)
print(OUT)
