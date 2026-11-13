"""Page title scene: a brick figure of Alec throws bricks that stack into a word.
On COOKING a chef's hat lands on him at the end; on GARDENING he plants a tree.

TITLE_WORD picks the word ("PROJECTS" by default). Run it like intro.py; `pnpm intro:render`
renders one clip per word. The last frame is the still the page shows under the video.
"""

import math
import os
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from figure import build_figure
from intro import BRICK_H, COLORS, FPS, brick_material, brick_mesh, brick_object, build_stage, clear_scene, configure_render, key, material

WORD = os.environ.get("TITLE_WORD", "PROJECTS").upper()
CUT = os.environ.get("TITLE_CUT", "wide")

# Brick-pixel letters, top row first.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["111", "010", "010", "010", "010", "010", "111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
}
LETTER_COLORS = ["blue", "yellow", "red", "green"]
OUTFIT = {"COOKING": "chef", "GARDENING": "gardener"}.get(WORD, "suit")
PLANT = 22 if OUTFIT == "gardener" else 0  # frames the gardener spends planting a tree
TREE_GAP = 4.8  # the tree goes in to the right of where the figure stops
TREE_Y = -1.0

START = 8  # first throw
BUILD = 76  # frames to throw the whole word
FLIGHT = 9  # frames a brick is in the air
WAVE = 5  # frames per swing of the wave
TAIL = 50  # the figure runs clear, turns round, hops and waves hello
FIGURE_Y = -4.5  # the figure works in front of the word
WORKING = math.radians(125)  # the figure runs to the right, turned towards the word
TWIST = 0.6  # and its upper body turns further, to face the word as it throws
FIGURE_SCALE = 1.4
REST_GAP = 4.5  # where the figure ends up, right of the last letter
SIZE = (960, 720) if CUT == "tall" else (1920, 480)

LIGHTS = [
    ("Key", (6, -40, 46), (40, 0, 8), 80000, 70, (1.0, 0.96, 0.9)),
    ("Fill", (-40, -45, 30), (55, 0, -40), 16000, 60, (0.75, 0.85, 1.0)),
    ("Rim", (10, 30, 26), (-50, 0, 175), 45000, 60, (0.7, 0.8, 1.0)),
]


def plan_word():
    """Returns (bricks, letter centres, right edge). A brick is (x, row, length, letter index)."""
    widths = [len(FONT[ch][0]) for ch in WORD]
    left = -(sum(widths) + len(WORD) - 1) / 2 + 0.5
    bricks, centres = [], []
    for index, ch in enumerate(WORD):
        rows = FONT[ch][::-1]  # bottom row first: bricks stack upwards
        for row, cells in enumerate(rows):
            col = 0
            while col < len(cells):
                if cells[col] == "0":
                    col += 1
                    continue
                run = 0
                while col + run < len(cells) and cells[col + run] == "1" and run < 4:
                    run += 1
                bricks.append((left + col + (run - 1) / 2, row, run, index))
                col += run
        centres.append(left + (widths[index] - 1) / 2)
        left += widths[index] + 1
    return bricks, centres, left - 1.5


def throw_bricks(bricks, centres, path, arrive, beats):
    """Each brick leaves the figure's hand on a throw, tumbles through an arc and clicks into
    place.
    `arrive` is the frame each letter starts. Returns the frame the last brick lands."""
    rng = random.Random(7)
    mats = {name: brick_material(f"Brick {name}", COLORS[name]) for name in LETTER_COLORS}
    meshes = {length: brick_mesh(length, 1) for length in range(1, 5)}
    window = BUILD / len(WORD)
    finale = 0
    for index in range(len(WORD)):
        letter = [b for b in bricks if b[3] == index]
        for n, (x, row, length, _) in enumerate(letter):
            # Bricks leave in handfuls, on the beat of whichever arm is throwing.
            due = arrive[index] + n * window / len(letter)
            launch, arm = min(beats, key=lambda beat: abs(beat[0] - due))
            land = launch + FLIGHT
            finale = max(finale, land)
            mat = mats[LETTER_COLORS[index % len(LETTER_COLORS)]]
            obj = brick_object(f"{WORD[index]}{index} {n}", meshes[length].copy(), mat)

            hand = tuple(c + rng.uniform(-0.25, 0.25) for c in hand_at(path_x(path, launch), arm))
            target = (x, 0.0, row * BRICK_H)
            apex = max(hand[2], target[2]) + rng.uniform(2.0, 3.2)
            for axis in (0, 1):
                key(
                    obj,
                    "location",
                    [(launch, hand[axis], "LINEAR", "AUTO"), (land, target[axis], "LINEAR", "AUTO")],
                    index=axis,
                )
            key(
                obj,
                "location",
                [
                    (launch, hand[2], "QUAD", "EASE_OUT"),
                    (launch + FLIGHT // 2, apex, "QUAD", "EASE_IN"),
                    (land, target[2], "LINEAR", "AUTO"),
                ],
                index=2,
            )
            for axis in range(3):
                spin = rng.choice((-1, 1)) * rng.uniform(2.0, 5.0)
                key(obj, "rotation_euler", [(launch, spin, "LINEAR", "AUTO"), (land, 0.0, "LINEAR", "AUTO")], index=axis)
            # Invisible until thrown; a quick squash as the studs click.
            small, full, click = (0.0,) * 3, (1.0,) * 3, (1.1, 1.1, 0.8)
            key(
                obj,
                "scale",
                [
                    (1, small, "CONSTANT", "AUTO"),
                    (launch, (0.5,) * 3, "LINEAR", "AUTO"),
                    (launch + 3, full, "CONSTANT", "AUTO"),
                    (land, click, "BACK", "EASE_OUT"),
                    (land + 4, full, "LINEAR", "AUTO"),
                ],
            )
    return finale


def throw_beats():
    """The throwing rhythm. Returns (swing keys for each arm, [(frame, arm)] for each release):
    an arm winds back, then flings forward and up, and lets go at the top."""
    back, flung, period = 0.45, -1.9, 3  # negative x raises an arm forward
    swings, beats = [], []
    for n in range(2):
        keys, frame, forward = [(1, 0.0)], START - period + n * period, False
        while frame < START + BUILD + period:
            keys.append((frame, flung if forward else back))
            if forward:
                beats.append((frame, n))
            forward = not forward
            frame += period
        swings.append(keys)
    return swings, sorted(beats)


def hand_at(x, arm):
    """Roughly where a hand is as it lets go, with the figure at `x`: up and out towards the
    word, on that arm's side of the body."""
    facing = WORKING + TWIST
    side, reach = (-1.47, 1.47)[arm], 2.1
    if CUT == "tall":
        width = plan_word()[2] * 2 + 1
        scale = ((width + 4) * 0.75 - 7 * BRICK_H - 2) / (7.5 if OUTFIT == "chef" else 6.6) / FIGURE_SCALE
        return (
            0.45 * x + scale * (side * math.cos(facing) + reach * math.sin(facing)),
            3 + scale * (FIGURE_Y + side * math.sin(facing) - reach * math.cos(facing)),
            7 * BRICK_H + 5.5 * scale,
        )
    return (
        x + side * math.cos(facing) + reach * math.sin(facing),
        FIGURE_Y + side * math.sin(facing) - reach * math.cos(facing),
        5.5,
    )


def run_path(centres, arrive):
    """Where the figure is while building, as (frame, x): it waits at the first letter, then
    runs steadily along the word, passing each letter as that letter goes up."""
    lead = 2.5  # reach a letter at its left edge
    path = [(1, centres[0] - lead), (START, centres[0] - lead)]
    path += [(frame, x - lead) for frame, x in zip(arrive[1:], centres[1:])]
    return path + [(START + BUILD, centres[-1] + lead)]


def path_x(path, frame):
    for (f0, x0), (f1, x1) in zip(path, path[1:]):
        if frame <= f1:
            return x0 + (x1 - x0) * max(frame - f0, 0) / (f1 - f0)
    return path[-1][1]


def animate_figure(fig, path, finale, rest_x, swings):
    """Run along the word while throwing, then run clear, turn to the camera, hop and wave.
    The gardener first stops side on and bends down to plant; the chef's hat lands in the hop."""
    root, pose, body, head, arms, legs = (fig[k] for k in ("root", "pose", "body", "head", "arms", "legs"))
    smooth = ("SINE", "EASE_IN_OUT")
    arrived = finale + 9  # at the resting spot
    turn = arrived + PLANT  # when it turns to the camera
    jump, apex, down = turn + 3, turn + 7, turn + 11
    bend = [(arrived + 6, 1.0), (turn - 5, 1.0)] if PLANT else []  # bent over the planting spot
    wave = down + 2

    # The run: a steady pace along the word, legs scissoring from the hips, a bob on every step.
    xs = [(frame, x, "LINEAR", "AUTO") for frame, x in path[:-1]]
    xs += [(path[-1][0], path[-1][1], "SINE", "EASE_OUT"), (arrived, rest_x, "LINEAR", "AUTO")]
    step = 4  # frames per footfall
    stride, zs, forward = [(1, 0.0)], [(1, 0.0, *smooth)], True
    for frame in range(START, arrived - 1, step):
        stride.append((frame + step // 2, 0.75 if forward else -0.75))
        zs += [(frame, 0.0, *smooth), (frame + step // 2, 0.32, *smooth)]
        forward = not forward
    # Then a hop on the spot with a kick, and a little bounce as it lands.
    stride += [(arrived, 0.0), (jump, 0.0), (apex, 0.6), (down, 0.0)]
    zs += [(arrived, 0.0, *smooth), (jump, 0.0, "QUAD", "EASE_OUT"), (apex, 1.0, "QUAD", "EASE_IN"), (down, 0.0, "LINEAR", "AUTO")]
    squash = [(1, 1.0), (arrived, 1.0), (jump, 0.86), (apex, 1.07), (down, 0.9), (down + 2, 1.03), (down + 4, 1.0)]
    key(root, "location", xs, index=0)
    key(root, "location", zs, index=2)
    key(root, "location", [(1, FIGURE_Y, *smooth), (finale + 3, FIGURE_Y, *smooth), (arrived, -1.0, "LINEAR", "AUTO")], index=1)
    key(
        root,
        "rotation_euler",
        [(1, WORKING, *smooth), (finale + 3, WORKING, *smooth)]
        + ([(arrived, math.pi / 2, *smooth), (turn - 2, math.pi / 2, *smooth)] if PLANT else [])
        + [(turn + 2, math.radians(-14), "LINEAR", "AUTO")],
        index=2,
    )
    # Squash keeps the volume: shorter means wider.
    key(pose, "scale", [(f, (s**-0.5, s**-0.5, s), *smooth) for f, s in squash])
    for leg, way in zip(legs, (1, -1)):
        key(leg, "rotation_euler", [(f, way * angle, *smooth) for f, angle in stride], index=0)

    reach = [(f, -0.9 * amount, *smooth) for f, amount in bend] + [(jump, 0.0, "LINEAR", "AUTO")]
    # Arms take turns throwing. The upper body is turned to the word while the legs run on,
    # it rocks into each throw, and the head stays on the word, looking up at the bricks.
    key(arms[0], "rotation_euler", [(f, a, *smooth) for f, a in swings[0]] + [(finale, 0.0, *smooth)] + reach, index=0)
    # The waving arm also comes a little forward, so the wave isn't flat to the camera.
    waving = [(finale, 0.0, *smooth)] + reach[:-1] + [(jump, 0.0, *smooth), (wave, -0.3, "LINEAR", "AUTO")]
    key(arms[1], "rotation_euler", [(f, a, *smooth) for f, a in swings[1]] + waving, index=0)
    rock = [(1, 0.0), (START - 2, TWIST)]
    rock += [(f, TWIST + (0.14 if n else -0.14)) for f, a in sorted(swings[0][1:] + swings[1][1:]) for n in [a < 0]]
    rock += [(finale, TWIST), (finale + 3, 0.0)]
    key(body, "rotation_euler", [(f, a, *smooth) for f, a in rock], index=2)
    key(head, "rotation_euler", [(1, 0.0, *smooth), (START - 2, 0.2, *smooth), (finale, 0.2, *smooth), (finale + 3, 0.0, "LINEAR", "AUTO")], index=2)

    # Both arms go up and out in the hop. One comes back down; the other stays up and waves.
    # The wave is loose: each swing is smaller than the last, the hand trails the arm and
    # flicks further, and the body and head sway against it.
    swing_sizes = [0.36, -0.32, 0.28, -0.22, 0.13, 0.0]
    beats = [(wave + i * WAVE, size) for i, size in enumerate(swing_sizes)]
    for n, arm in enumerate(arms):
        hang = arm.rotation_euler.y
        up = hang * 14
        raise_keys = [(1, hang, "CONSTANT", "AUTO"), (jump, hang, "BACK", "EASE_OUT"), (apex + 1, up, *smooth)]
        if n == 1:
            high = hang * 17  # nearly straight up
            raise_keys += [(f, high + size, *smooth) for f, size in beats]
        else:
            raise_keys += [(down, up, *smooth), (down + 7, hang, "BACK", "EASE_OUT"), (down + 12, hang, "LINEAR", "AUTO")]
        key(arm, "rotation_euler", raise_keys, index=1)
    flick = [(1, 0.0, *smooth), (wave - 2, 0.0, *smooth)] + [(f + 2, 1.5 * size, *smooth) for f, size in beats]
    key(fig["hands"][1], "rotation_euler", flick, index=1)
    sway = [(1, 0.0, *smooth), (down, 0.0, *smooth)] + [(f + 1, -0.22 * size, *smooth) for f, size in beats]
    key(body, "rotation_euler", sway, index=1)
    # The head tips towards the waving hand and nods along a beat behind.
    tip = [(1, 0.0, *smooth), (down, 0.0, *smooth)] + [(f + 2, 0.13 + 0.25 * size, *smooth) for f, size in beats]
    key(head, "rotation_euler", tip, index=1)

    # Positive x leans forward: into the run, upright for the turn, back a touch in the hop.
    lean = [(1, 0.0), (START, 0.0), (START + 3, 0.2), (arrived - 2, 0.2)] + [(f, 0.85 * a) for f, a in bend] + [(jump, 0.0), (apex, -0.1), (down, 0.06), (down + 4, 0.0)]
    key(body, "rotation_euler", [(f, a, *smooth) for f, a in lean], index=0)
    look = [(1, -0.24), (finale, -0.24), (arrived, 0.0)] + [(f, 0.3 * a) for f, a in bend] + [(jump, 0.0), (apex, -0.2), (down, 0.08), (down + 4, 0.0)]
    key(head, "rotation_euler", [(f, a, *smooth) for f, a in look], index=0)

    if OUTFIT == "chef":
        # The hat drops in from above the frame during the hop and settles with a bounce.
        hat, rest = fig["hat"], fig["hat"].location.z
        # Full hair until the hat lands on it.
        for name, hidden in (("full", False), ("under hat", True)):
            key(fig["hair"][name], "hide_render", [(1, hidden, "CONSTANT", "AUTO"), (down, not hidden, "CONSTANT", "AUTO")])
        fall = [(1, rest + 9, "CONSTANT", "AUTO"), (jump, rest + 9, "QUAD", "EASE_IN"), (down, rest, "BACK", "EASE_OUT"), (down + 5, rest, "LINEAR", "AUTO")]
        key(hat, "location", fall, index=2)
        key(hat, "scale", [(1, (1.0,) * 3, *smooth), (down, (1.12, 1.12, 0.7), *smooth), (down + 5, (1.0,) * 3, "LINEAR", "AUTO")])
    return arrived


def plant_tree(x, sprout):
    """A brick sapling that springs out of the ground at frame `sprout`."""
    tree = bpy.data.objects.new("Tree", None)
    tree.location = (x, TREE_Y, 0)
    bpy.context.scene.collection.objects.link(tree)
    trunk = material("Trunk", (0.12, 0.05, 0.02), 0.4, coat=0.2)
    leaf = brick_material("Leaf", COLORS["green"])
    for n, (size, mat) in enumerate([(1, trunk), (1, trunk), (3, leaf), (2, leaf), (1, leaf)]):
        obj = brick_object(f"Tree {n}", brick_mesh(size, size), mat)
        obj.parent, obj.location = tree, (0, 0, n * BRICK_H)
    grown = [(1, (0.0,) * 3, "CONSTANT", "AUTO"), (sprout, (0.3, 0.3, 0.0), "BACK", "EASE_OUT"), (sprout + 12, (1.0,) * 3, "LINEAR", "AUTO")]
    key(tree, "scale", grown)


def frame_shot(cam, target, left, right):
    """Fit the word and the resting figure to the width of the frame."""
    centre, width = (left + right) / 2, right - left + 5
    if CUT == "tall":
        bricks = plan_word()[0]
        width = max(b[0] + b[2] / 2 for b in bricks) - min(b[0] - b[2] / 2 for b in bricks) + 4
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = width
        cam.data.dof.use_dof = False
        target.location = (0, 0, width * 0.375 - 1)
        cam.location = (0, -100, target.location.z + 8)
        return
    cam.data.lens = 50
    cam.data.dof.use_dof = False
    distance = width / (cam.data.sensor_width / cam.data.lens)
    if SIZE[1] > SIZE[0]:
        # AUTO sensor fit uses the vertical sensor in a portrait frame. Preserve horizontal room.
        distance *= SIZE[1] / SIZE[0]
    elevation = math.radians(7)
    height = 4.4
    target.location = (centre, 0, height)
    cam.location = (centre, -distance * math.cos(elevation), height + distance * math.sin(elevation))


def main():
    clear_scene()
    cam, target = build_stage(LIGHTS)
    bricks, centres, right = plan_word()
    arrive = [round(START + i * BUILD / len(WORD)) for i in range(len(WORD))]
    path = run_path(centres, arrive)
    swings, beats = throw_beats()
    finale = throw_bricks(bricks, centres, path, arrive, beats)
    fig = build_figure(OUTFIT)
    fig["root"].scale = (FIGURE_SCALE,) * 3
    rest_x = right + REST_GAP
    arrived = animate_figure(fig, path, finale, rest_x, swings)
    if CUT == "tall":
        # A second stage above the letters: the complete word stays in the foreground.
        # Parent the animated rig so its original throwing/waving motion is preserved.
        stage = bpy.data.objects.new("Tall figure stage", None)
        bpy.context.scene.collection.objects.link(stage)
        fig["root"].parent = stage
        width = right * 2 + 1
        scale = ((width + 4) * 0.75 - 7 * BRICK_H - 2) / (7.5 if OUTFIT == "chef" else 6.6) / FIGURE_SCALE
        stage.scale = (scale,) * 3
        stage.location = (-rest_x * scale, 3, 7 * BRICK_H)
        # Keep the running figure in frame before it arrives at its central resting spot.
        key(stage, "location", [(f, ((0.45 - scale) * x, 3, 7 * BRICK_H), "LINEAR", "AUTO") for f, x in path] + [
            (arrived, (-rest_x * scale, 3, 7 * BRICK_H), "LINEAR", "AUTO")])
        bpy.context.scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.6
        for light in bpy.data.lights:
            light.energy *= 1.65
    if PLANT:
        plant_tree(rest_x + TREE_GAP, arrived + 8)
        if CUT == "tall":
            tree = bpy.data.objects["Tree"]
            tree.location = (width * 0.3, 2, 7 * BRICK_H)
    frame_shot(cam, target, -right, rest_x + (TREE_GAP + 2.5 if PLANT else 2.5))
    end = finale + TAIL + PLANT
    configure_render(end, SIZE)
    bpy.context.scene.frame_set(end)
    print(f"word={WORD} bricks={len(bricks)} finale={finale} end={end} seconds={end / FPS:.2f}")


if __name__ == "__main__":
    main()
