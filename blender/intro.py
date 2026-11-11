"""Pipeline intro scene: bricks assemble three stages (build, test, ship) and each goes green.

Builds the whole scene from nothing so the intro can be regenerated: run it in Blender
(through the Blender MCP, or `blender --background --python blender/intro.py`), then
`pnpm intro:render` renders the frames and encodes the web assets.

INTRO_CUT picks the framing: "wide" (16:9, pipeline right of the headline) or "tall" (9:16,
pipeline above the headline). The last frame of each cut is the matching hero background.
"""

import math
import os
from pathlib import Path

import bmesh
import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot

CUT = os.environ.get("INTRO_CUT", "wide")
FONT = Path(__file__).parent / "fonts" / "ArchivoBlack-Regular.ttf"

# One stud pitch is 1 unit; real bricks are 8 mm pitch, 9.6 mm tall.
BRICK_H = 1.2
STUD_R = 0.3
STUD_H = 0.22
GAP = 0.012  # hairline between neighbours so edges read

FPS = 30
FALL = 9  # frames a brick takes to fall
FINAL_FALL = 6  # the last cap comes down harder
DROP_HEIGHT = 24.0  # starts every brick above the top of the frame
FIRST_LANDING = 6
STEP = 2  # frames between landings inside a stage
BEAT = 5  # pause before a stage's green cap
FINAL_BEAT = 10  # longer pause before the last cap
TAIL = 12  # frames after the last cap lands, while its glow settles

COLORS = {
    "blue": (0.0, 0.1, 0.5),
    "yellow": (1.0, 0.5, 0.0),
    "red": (0.6, 0.03, 0.02),
    "green": (0.0, 0.32, 0.06),
    "grey": (0.1, 0.11, 0.12),
}
BACKGROUND = (0.012, 0.014, 0.018)

# Stages left to right: label, colour, courses of two 2x4 bricks. Each is 4 studs square with
# a 4-stud link between neighbours, and climbs one course so the line rises towards "ship".
STAGES = [("BUILD", "blue", 2), ("TEST", "yellow", 3), ("SHIP", "red", 4)]
STAGE_PITCH = 8


def brick_mesh(length, width=2):
    """A length x width brick with smooth-shaded studs, origin at the bottom centre."""
    bm = bmesh.new()
    body = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(length - GAP, width - GAP, BRICK_H), verts=body)
    bmesh.ops.translate(bm, vec=(0, 0, BRICK_H / 2), verts=body)
    for ix in range(length):
        for iy in range(width):
            stud = bmesh.ops.create_cone(
                bm, cap_ends=True, segments=32, radius1=STUD_R, radius2=STUD_R, depth=STUD_H
            )["verts"]
            x = ix - (length - 1) / 2
            y = iy - (width - 1) / 2
            bmesh.ops.translate(bm, vec=(x, y, BRICK_H + STUD_H / 2), verts=stud)
    for face in bm.faces:
        n = face.normal
        # Stud walls: horizontal normals that aren't one of the body's four sides.
        face.smooth = abs(n.z) < 0.5 and max(abs(n.x), abs(n.y)) < 0.999
    mesh = bpy.data.meshes.new(f"Brick {width}x{length}")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def material(name, rgb, roughness, coat=0.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.12
    bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def brick_material(name, rgb):
    """The glossy plastic every brick is made of."""
    return material(name, rgb, 0.28, coat=0.35)


def brick_object(name, mesh, mat):
    """Link a brick, with the fine bevel that lets its edges catch the light."""
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width, bevel.segments, bevel.limit_method = 0.03, 2, "ANGLE"
    return obj


def key(target, path, keys, index=-1):
    """Insert (frame, value, interpolation, easing) keyframes on one property."""
    for frame, value, _, _ in keys:
        if index >= 0:
            getattr(target, path)[index] = value
        else:
            setattr(target, path, value)
        target.keyframe_insert(path, index=index, frame=frame)
    anim = target.animation_data
    by_frame = {frame: (interp, easing) for frame, _, interp, easing in keys}
    for fcurve in action_get_channelbag_for_slot(anim.action, anim.action_slot).fcurves:
        if fcurve.data_path == path and index in (-1, fcurve.array_index):
            for kp in fcurve.keyframe_points:
                kp.interpolation, kp.easing = by_frame[round(kp.co.x)]


def add_brick(name, mesh, mat, location, land, turned=False, fall=FALL):
    """Link a brick and drop it so it lands on `land`. Studded bricks click and stop: no bounce."""
    obj = brick_object(name, mesh.copy(), mat)  # own mesh, so each brick keeps its own colour
    obj.location = location
    obj.rotation_euler.z = math.pi / 2 if turned else 0.0
    high = location[2] + DROP_HEIGHT
    start = max(land - fall, 1)
    key(
        obj,
        "location",
        [(1, high, "CONSTANT", "AUTO"), (start, high, "QUAD", "EASE_IN"), (land, location[2], "LINEAR", "AUTO")],
        index=2,
    )
    return obj


def add_label(text, x, shown):
    """An upright sign in front of a stage that flips up off the floor when the stage goes green."""
    curve = bpy.data.curves.new(f"Label {text}", "FONT")
    curve.body = text
    curve.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    curve.size = 1.15
    curve.extrude = 0.05
    curve.align_x = "CENTER"
    curve.materials.append(bpy.data.materials["Label"])
    obj = bpy.data.objects.new(f"Label {text}", curve)
    obj.location = (x, -3.1, 0.02)
    bpy.context.scene.collection.objects.link(obj)
    flat, upright = 0.0, math.pi / 2
    key(
        obj,
        "rotation_euler",
        [(1, flat, "CONSTANT", "AUTO"), (shown, flat, "EXPO", "EASE_OUT"), (shown + 8, upright, "LINEAR", "AUTO")],
        index=0,
    )
    # Lying flat it would show through the floor's reflections; keep it hidden until it flips.
    key(obj, "hide_render", [(1, True, "CONSTANT", "AUTO"), (shown, False, "CONSTANT", "AUTO")])
    key(obj, "hide_viewport", [(1, True, "CONSTANT", "AUTO"), (shown, False, "CONSTANT", "AUTO")])


def add_glow(name, mat, location, landings):
    """Green light for a cap: flashes on each frame in `landings`, then idles as a soft glow."""
    data = bpy.data.lights.new(name, "POINT")
    data.color = (0.25, 1.0, 0.4)
    data.shadow_soft_size = 1.0
    light = bpy.data.objects.new(name, data)
    light.location = location
    bpy.context.scene.collection.objects.link(light)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    strength = bsdf.inputs["Emission Strength"]
    for scale, target, path in ((1.0, strength, "default_value"), (160.0, data, "energy")):
        setattr(target, path, 0.0)
        target.keyframe_insert(path, frame=1)
        for land in landings:
            for frame, value in ((land - 1, None), (land + 1, 6.0), (land + 10, 1.2)):
                if value is not None:
                    setattr(target, path, value * scale)
                target.keyframe_insert(path, frame=frame)


def build_pipeline():
    """Returns (frame the last cap lands, x of each stage)."""
    mats = {n: brick_material(f"Brick {n}", rgb) for n, rgb in COLORS.items() if n != "green"}
    material("Label", (0.85, 0.85, 0.82), 0.6, emission=0.35)
    long_brick, cap_mesh = brick_mesh(4), brick_mesh(4, 4)
    xs = [(i - (len(STAGES) - 1) / 2) * STAGE_PITCH for i in range(len(STAGES))]

    # Schedule every landing first: the last cap's frame is when every cap flashes together.
    frame = FIRST_LANDING
    plan = []
    for i, (label, color, courses) in enumerate(STAGES):
        last = i == len(STAGES) - 1
        bricks = []
        for course in range(courses):
            for side in (-1, 1):
                bricks.append((course, side, frame))
                frame += STEP
        cap = frame - STEP + (FINAL_BEAT if last else BEAT)
        link = None if last else cap + 4
        frame = cap + 7
        plan.append((label, color, courses, bricks, cap, link))
    finale = plan[-1][4]

    for x, (label, color, courses, bricks, cap, link) in zip(xs, plan):
        for course, side, land in bricks:
            turned = course % 2 == 1  # alternate direction each course so the stage is bonded
            offset = (side, 0) if turned else (0, side)
            add_brick(
                f"{label} {course}{'ab'[side > 0]}",
                long_brick,
                mats[color],
                (x + offset[0], offset[1], course * BRICK_H),
                land,
                turned,
            )
        top = courses * BRICK_H
        green = brick_material(f"Cap {label}", COLORS["green"])
        add_brick(f"{label} cap", cap_mesh, green, (x, 0, top), cap, fall=FINAL_FALL if cap == finale else FALL)
        add_glow(f"{label} glow", green, (x, -2.6, top + BRICK_H + 0.6), sorted({cap, finale}))
        add_label(label, x, cap)
        if link:
            add_brick(f"{label} link", long_brick, mats["grey"], (x + STAGE_PITCH / 2, 0, 0), link)
    return finale, xs


# Area lights: name, location, rotation in degrees, watts, size, colour.
LIGHTS = [
    ("Key", (2, -12, 14), (40, 0, 8), 9000, 14, (1.0, 0.96, 0.9)),
    ("Fill", (-16, -16, 12), (50, 0, -45), 1500, 14, (0.75, 0.85, 1.0)),
    ("Rim", (6, 12, 10), (-50, 0, 170), 5000, 12, (0.7, 0.8, 1.0)),
]


def build_stage(lights=LIGHTS):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*BACKGROUND, 1.0)
    scene.world = world

    bpy.ops.mesh.primitive_plane_add(size=400)
    floor = bpy.context.object
    floor.name = "Floor"
    floor.data.materials.append(material("Floor", (0.02, 0.022, 0.028), 0.5))

    def area(name, location, rotation, power, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = power, size, color
        light = bpy.data.objects.new(name, data)
        light.location = location
        light.rotation_euler = [math.radians(a) for a in rotation]
        scene.collection.objects.link(light)

    for light in lights:
        area(*light)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    target = bpy.data.objects.new("Camera Target", None)
    scene.collection.objects.link(target)
    cam.constraints.new("TRACK_TO").target = target
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 5.6
    cam_data.dof.focus_object = target
    return cam, target


# Camera per cut: (lens, start position, start target, end position, end target). The move
# opens close on the first stage and pulls back along the line as the later stages arrive.
SHOTS = {
    "wide": (45, (4, -24, 5), (-7, 0, 1.6), (25, -44, 11), (-10, 0, 1.6)),
    "tall": (45, (2, -26, 6), (-7, 0, 0.5), (16, -56, 15), (0.6, 0, -8)),
}
# 1440p: sharp when the hero fills a large or high-density screen.
SIZES = {"wide": (2560, 1440), "tall": (1440, 2560)}


def animate_camera(cam, target, finale):
    lens, cam_from, look_from, cam_to, look_to = SHOTS[CUT]
    cam.data.lens = lens
    for obj, start, end in ((cam, cam_from, cam_to), (target, look_from, look_to)):
        for axis in range(3):
            key(
                obj,
                "location",
                [(1, start[axis], "SINE", "EASE_IN_OUT"), (finale, end[axis], "LINEAR", "AUTO")],
                index=axis,
            )
    # The last cap lands hard enough to jolt the camera.
    z = cam_to[2]
    key(
        cam,
        "location",
        [
            (1, cam_from[2], "SINE", "EASE_IN_OUT"),
            (finale, z, "LINEAR", "AUTO"),
            (finale + 1, z - 0.14, "LINEAR", "AUTO"),
            (finale + 3, z + 0.05, "SINE", "EASE_OUT"),
            (finale + 7, z, "LINEAR", "AUTO"),
        ],
        index=2,
    )


def configure_render(end, size):
    """Render settings shared by every scene. `size` is (width, height) in pixels."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        print("engine fallback:", err)
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, end
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.use_motion_blur = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"  # plain AgX washes the brick colours out
    scene.eevee.taa_render_samples = 64
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True


def clear_scene():
    """Empty the file without resetting preferences, which would unload the MCP add-on."""
    for collection in (
        bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights,
        bpy.data.cameras, bpy.data.worlds, bpy.data.actions,
    ):
        bpy.data.batch_remove(list(collection))


def main():
    clear_scene()
    cam, target = build_stage()
    finale, _ = build_pipeline()
    end = finale + TAIL
    animate_camera(cam, target, finale)
    configure_render(end, SIZES[CUT])
    bpy.context.scene.frame_set(end)
    # The page starts its own entrance when the last cap lands; print the time it needs.
    print(f"cut={CUT} finale={finale} end={end} finale_seconds={(finale - 1) / FPS:.3f} seconds={end / FPS:.2f}")


if __name__ == "__main__":
    main()
