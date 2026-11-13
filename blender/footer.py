"""One transparent footer still, using the site's existing suit and brick helpers.

blender --background --python blender/footer.py --render-output /path/footer --render-frame 1
"""
import math
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).parent))
from figure import build_figure
from intro import COLORS, BRICK_H, brick_material, brick_mesh, brick_object, build_stage, clear_scene, configure_render

clear_scene()
cam, target = build_stage([
    ("Key", (-5, -10, 14), (25, 0, -25), 1700, 8, (1, .94, .85)),
    ("Fill", (7, -7, 9), (35, 0, 35), 1400, 7, (.8, .9, 1)),
    ("Rim", (1, 6, 11), (-35, 0, 170), 1800, 6, (1, .95, .85)),
])
bpy.data.objects.remove(bpy.data.objects["Floor"], do_unlink=True)
fig = build_figure("suit")
fig["root"].location = (-1.5, 0, 0)
fig["root"].rotation_euler.z = math.radians(-12)
fig["arms"][1].rotation_euler.y = -2.4
fig["arms"][1].rotation_euler.x = -.25
fig["head"].rotation_euler.y = .12
for i, (x, y, z, length, color, angle) in enumerate([
    (2.3, 0, 0, 4, "blue", -8), (2.3, 0, BRICK_H, 3, "red", -8),
    (2.5, 0, 2 * BRICK_H, 2, "yellow", 9), (3.7, -2, 0, 2, "green", 14),
]):
    obj = brick_object(f"Footer brick {i}", brick_mesh(length, 2), brick_material(color, COLORS[color]))
    obj.location = (x, y, z)
    obj.rotation_euler.z = math.radians(angle)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 12
cam.data.dof.use_dof = False
cam.location = (9, -30, 15)
target.location = (.6, 0, 2.8)
for light in bpy.data.lights:
    light.energy *= 1.65
configure_render(1, (1200, 900))
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.image_settings.color_mode = "RGBA"
bpy.context.scene.render.use_motion_blur = False
