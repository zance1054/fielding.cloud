"""Reads the head out of the profile picture: which pixels are face print, which are hair.

Plain numpy, no Blender, so it can be checked on its own. Arrays are rows from the top of the
picture, values 0 to 1.
"""

from collections import deque

import numpy as np


def dilate(mask, radius):
    """Grow a mask by `radius` pixels (square)."""
    out = mask.copy()
    for axis in (0, 1):
        grown = out.copy()
        for shift in range(1, radius + 1):
            for sign in (-1, 1):
                moved = np.roll(out, sign * shift, axis=axis)
                # Don't let np.roll wrap the far edge round.
                edge = [slice(None), slice(None)]
                edge[axis] = slice(0, shift) if sign > 0 else slice(-shift, None)
                moved[tuple(edge)] = False
                grown |= moved
        out = grown
    return out


def close(mask, radius):
    """Fill gaps and notches narrower than about twice `radius`."""
    return ~dilate(~dilate(mask, radius), radius)


def flood(passable, seed):
    """The connected region of `passable` that contains `seed` (row, column)."""
    region = np.zeros_like(passable)
    queue = deque([seed])
    region[seed] = True
    rows, cols = passable.shape
    while queue:
        r, c = queue.popleft()
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and passable[nr, nc] and not region[nr, nc]:
                region[nr, nc] = True
                queue.append((nr, nc))
    return region


def fill_holes(mask):
    """Add every area the mask fully encloses."""
    return ~flood(~mask, (0, 0))


def read_head(rgb):
    """Returns a dict:
    face   - the skin area inside the head outline, print included
    ink    - 0..1, the dark print inside the face (eyes, brows, mouth, stubble)
    white  - 0..1, the white print inside the face (eye glints, teeth)
    hair   - the hair with its outline
    skin   - the face's skin colour
    box    - (left, right, top, bottom) of the head outline, in pixels
    """
    height, width, _ = rgb.shape
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dark = r < 0.3  # the navy outline and print
    backdrop = (b > r + 0.05) & ~dark
    rows = np.arange(height)[:, None]

    # The face is the skin reachable from the bridge of the nose without crossing an outline.
    seed = (round(height * 0.53), round(width * 0.5))
    skin_area = flood(~dark & ~backdrop, seed)
    face = fill_holes(close(skin_area, 16))  # print in the skin is part of the face
    inside = ~dilate(~face, 3)  # stay off the head's own outline
    ink = np.clip((0.55 - r) / 0.3, 0, 1) * inside
    white = np.clip((b - 0.72) / 0.15, 0, 1) * inside
    skin = np.median(rgb[skin_area & (b < 0.6)], axis=0)

    # Hair: the warm colours above the jaw that aren't face, plus the outline drawn round them.
    warm = ~dark & ~backdrop & ~face & (rows < height * 0.6)
    hair = fill_holes(close(warm | (dark & dilate(warm, 12) & ~inside), 3))

    outline = dilate(face, 12)
    cols_used, rows_used = np.where(outline.any(axis=0))[0], np.where(outline.any(axis=1))[0]
    box = (cols_used[0], cols_used[-1], rows_used[0], rows_used[-1])
    return {"face": face, "ink": ink, "white": white, "hair": hair, "skin": skin, "box": box}
