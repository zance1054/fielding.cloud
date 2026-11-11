"""The brick figure of Alec. The head is taken from public/profile.webp: the face is printed from
the picture and the hair piece is cut to its outline. The body is a grey suit, white shirt and
blue tie, or a chef's or gardener's outfit with a hat. Moulded parts are hard-edged with a fine bevel. It faces -y and stands on z = 0.
"""

import math

from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

from headart import read_head
from intro import material

HEAD_R = 0.78
HEAD_H = 1.3
HEAD_Z = 4.5  # centre of the head
HIP_Z = 1.5
WAIST_Z = 1.8
ELBOW = math.radians(32)  # how far the forearm bends forward
HAIR_STEP = 3  # picture pixels per facet of the hair piece
HAT_Z = 0.75  # where a hat rests, above the centre of the head
PICTURE = Path(__file__).parent.parent / "public" / "profile.webp"


def link(name, bm, mat, parent, location=(0, 0, 0), bevel=0.035):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.parent = parent
    bpy.context.scene.collection.objects.link(obj)
    if bevel:
        # A fine bevel with hardened normals: flat faces stay flat and the edges catch the light.
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width, mod.segments = bevel, 3
        mod.limit_method, mod.angle_limit = "ANGLE", math.radians(35)
        mod.harden_normals = True
    else:
        mesh.set_sharp_from_angle(angle=math.radians(35))
    return obj


def box(name, size, location, mat, parent, offset=(0, 0, 0), taper=1.0, bevel=0.035):
    bm = bmesh.new()
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=size, verts=verts)
    # A taper of 1 leaves the top face as it is.
    bmesh.ops.scale(bm, vec=(taper, 1, 1), verts=[v for v in verts if v.co.z > 0])
    bmesh.ops.translate(bm, vec=offset, verts=verts)
    return link(name, bm, mat, parent, location, bevel)


def cylinder(name, radius, depth, location, mat, parent, offset=(0, 0, 0), bevel=0.035, back_of=None):
    """Upright cylinder. `back_of` keeps only the part behind that y, for hair round the face."""
    bm = bmesh.new()
    verts = bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=radius, radius2=radius, depth=depth)["verts"]
    bmesh.ops.translate(bm, vec=offset, verts=verts)
    if back_of is not None:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, back_of, 0), plane_no=(0, -1, 0), clear_outer=True)
        bmesh.ops.holes_fill(bm, edges=bm.edges[:])
    return link(name, bm, mat, parent, location, bevel)


def clip_hand(name, mat, parent, location):
    """The C-shaped clip hand, open at the bottom, on a short wrist."""
    bm = bmesh.new()
    inner, outer, half, gap, steps = 0.15, 0.29, 0.2, math.radians(80), 20
    rings = []
    for i in range(steps + 1):
        a = -math.pi / 2 + gap / 2 + i * (2 * math.pi - gap) / steps
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * c, y, r * s)) for r, y in ((inner, -half), (outer, -half), (outer, half), (inner, half))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    wrist = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.17, radius2=0.17, depth=0.3)["verts"]
    bmesh.ops.translate(bm, vec=(0, 0, outer + 0.1), verts=wrist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return link(name, bm, mat, parent, location, bevel=0.02)


def flat(name, points, mat, parent, lift):
    """Print on the front of the torso: a polygon of (x, z) points."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, -0.5 - lift, z)) for x, z in points])
    face.normal_update()
    if face.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=[face])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return link(name, bm, mat, parent, bevel=0)


def linear(srgb):
    """sRGB colour to the linear values a material wants."""
    return tuple(float(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in srgb)


def load_picture():
    """The profile picture as rows from the top, plus the Blender image."""
    image = bpy.data.images.load(str(PICTURE), check_existing=True)
    width, height = image.size
    flat_pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(flat_pixels)
    return flat_pixels.reshape(height, width, 4)[::-1, :, :3], image


def picture_uv(nodes, links, art, size):
    """Nodes that lay the picture over the head as seen from the front. Head-local x and z map
    straight onto picture pixels. Returns (uv socket, front-facing socket, coordinate node)."""
    width, height = size
    left, right, _, chin = art["box"]
    scale = (right - left) / (2 * HEAD_R)  # pixels per unit
    coords = nodes.new("ShaderNodeTexCoord")
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Object"], split.inputs[0])
    join = nodes.new("ShaderNodeCombineXYZ")
    for axis, out, mul, add in (
        (0, "X", scale / width, (left + right) / 2 / width),
        (1, "Z", scale / height, 1 - (chin - HEAD_H / 2 * scale) / height),
    ):
        math_node = nodes.new("ShaderNodeMath")
        math_node.operation = "MULTIPLY_ADD"
        math_node.inputs[1].default_value, math_node.inputs[2].default_value = mul, add
        links.new(split.outputs[out], math_node.inputs[0])
        links.new(math_node.outputs[0], join.inputs[axis])
    front = nodes.new("ShaderNodeMath")
    front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    links.new(split.outputs["Y"], front.inputs[0])
    return join.outputs[0], front.outputs[0], coords


def mix_colour(nodes, links, factor, a, b, target):
    """target = a where factor is 0, b where it is 1. a and b are sockets or colours."""
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    sockets = {i.identifier: i for i in mix.inputs}
    links.new(factor, sockets["Factor_Float"])
    for value, socket in ((a, sockets["A_Color"]), (b, sockets["B_Color"])):
        if isinstance(value, tuple):
            socket.default_value = (*value, 1.0)
        else:
            links.new(value, socket)
    links.new(next(o for o in mix.outputs if o.identifier == "Result_Color"), target)


def head_material(art, picture, skin):
    """Skin with the face from the picture printed on the front: eyes, brows, smile, stubble."""
    height, width = art["ink"].shape
    alpha = np.maximum(art["ink"], art["white"])
    pixels = np.dstack([picture, alpha]).astype(np.float32)[::-1]
    image = bpy.data.images.new("Face print", width, height, alpha=True)
    image.pixels.foreach_set(pixels.ravel())

    mat = material("Head", skin, 0.22, coat=0.5)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    uv, front, _ = picture_uv(nodes, links, art, (width, height))
    tex = nodes.new("ShaderNodeTexImage")
    tex.image, tex.extension = image, "CLIP"
    links.new(uv, tex.inputs["Vector"])
    printed = nodes.new("ShaderNodeMath")
    printed.operation = "MULTIPLY"
    links.new(tex.outputs["Alpha"], printed.inputs[0])
    links.new(front, printed.inputs[1])
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    mix_colour(nodes, links, printed.outputs[0], skin, tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def hair_material(art, image, brown):
    """The hair from the picture on the front and back faces, plain brown round the edge."""
    mat = material("Hair", brown, 0.5)  # matt enough that the flat front keeps its colour
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    uv, _, coords = picture_uv(nodes, links, art, tuple(image.size))
    tex = nodes.new("ShaderNodeTexImage")
    tex.image, tex.extension = image, "EXTEND"
    links.new(uv, tex.inputs["Vector"])
    normal = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Normal"], normal.inputs[0])
    facing = nodes.new("ShaderNodeMath")
    facing.operation = "ABSOLUTE"
    links.new(normal.outputs["Y"], facing.inputs[0])
    flat_face = nodes.new("ShaderNodeMath")
    flat_face.operation = "GREATER_THAN"
    flat_face.inputs[1].default_value = 0.5
    links.new(facing.outputs[0], flat_face.inputs[0])
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    mix_colour(nodes, links, flat_face.outputs[0], brown, tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def hair_piece(art, mat, parent, below=None):
    """The hair as one moulded piece: the exact outline in the picture, from the face back past the crown.
    `below` keeps only the hair under that height, for wearing a hat."""
    left, right, _, chin = art["box"]
    scale = (right - left) / (2 * HEAD_R)
    centre = (left + right) / 2
    front, back = -(HEAD_R + 0.05), 0.3  # the shell behind it rounds off the back of the head
    cells = art["hair"][HAIR_STEP // 2 :: HAIR_STEP, HAIR_STEP // 2 :: HAIR_STEP]
    rows, cols = cells.shape
    if below is not None:
        heights = (chin - np.arange(rows) * HAIR_STEP) / scale - HEAD_H / 2
        cells = cells & (heights <= below)[:, None]
    bm = bmesh.new()
    verts = {}

    def vert(col, row, y):
        if (col, row, y) not in verts:
            x = (col * HAIR_STEP - centre) / scale
            z = (chin - row * HAIR_STEP) / scale - HEAD_H / 2
            verts[col, row, y] = bm.verts.new((x, y, z))
        return verts[col, row, y]

    filled = lambda r, c: 0 <= r < rows and 0 <= c < cols and cells[r, c]
    for row, col in zip(*np.nonzero(cells)):
        row, col = int(row), int(col)
        corners = [(col, row), (col + 1, row), (col + 1, row + 1), (col, row + 1)]
        for y in (front, back):
            bm.faces.new([vert(c, r, y) for c, r in corners])
        # A wall along every side that has no hair beyond it.
        for (dr, dc), (a, b) in zip(((-1, 0), (0, 1), (1, 0), (0, -1)), zip(corners, corners[1:] + corners[:1])):
            if not filled(row + dr, col + dc):
                bm.faces.new([vert(*a, front), vert(*b, front), vert(*b, back), vert(*a, back)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return link("Hair", bm, mat, parent, bevel=0)


def print_suit(torso, mats):
    """Lapels, shirt and tie on the torso front; z runs -0.95 to 0.95 up the torso."""
    top = 0.95
    for side in (-1, 1):
        lapel = [(0.33, top), (0.68, top), (0.56, 0.42), (0.66, 0.3), (0.0, -0.55)]
        flat(f"Lapel {side}", [(side * x, z) for x, z in lapel], mats["lapel"], torso, 0.004)
        flat(f"Collar {side}", [(side * 0.36, top), (side * 0.1, top), (side * 0.2, 0.62)], mats["shirt"], torso, 0.012)
    flat("Shirt", [(-0.33, top), (0.33, top), (0.0, -0.55)], mats["shirt"], torso, 0.004)
    flat("Tie knot", [(-0.11, top), (0.11, top), (0.07, 0.72), (-0.07, 0.72)], mats["tie"], torso, 0.016)
    flat("Tie", [(-0.07, 0.72), (0.07, 0.72), (0.15, -0.12), (0.0, -0.36), (-0.15, -0.12)], mats["tie"], torso, 0.014)
    flat("Opening", [(-0.012, -0.55), (0.012, -0.55), (0.012, -0.95), (-0.012, -0.95)], mats["ink"], torso, 0.004)
    flat("Button", [(0.1 + 0.035 * math.cos(a), -0.72 + 0.035 * math.sin(a)) for a in [i * math.pi / 5 for i in range(10)]], mats["ink"], torso, 0.004)


def dots(name, centres, radius, mat, torso, lift):
    for n, (cx, cz) in enumerate(centres):
        ring = [(cx + radius * math.cos(i * math.pi / 5), cz + radius * math.sin(i * math.pi / 5)) for i in range(10)]
        flat(f"{name} {n}", ring, mat, torso, lift)


def print_chef(torso, mats):
    """A double-breasted chef's jacket with a red neckerchief."""
    top = 0.95
    flat("Overlap", [(0.47, top), (0.5, top), (0.44, -0.95), (0.41, -0.95)], mats["trim"], torso, 0.004)
    dots("Button", [(x, z) for x in (-0.24, 0.24) for z in (0.3, -0.1, -0.5)], 0.06, mats["trim"], torso, 0.006)
    flat("Neckerchief", [(-0.36, top), (0.36, top), (0.0, 0.5)], mats["accent"], torso, 0.008)
    flat("Knot", [(-0.1, 0.78), (0.1, 0.78), (0.07, 0.6), (-0.07, 0.6)], mats["accent"], torso, 0.014)


def print_overalls(torso, mats):
    """The bib and straps of a pair of overalls over a shirt."""
    top = 0.95
    flat("Bib", [(-0.62, -0.95), (0.62, -0.95), (0.52, 0.38), (-0.52, 0.38)], mats["legs"], torso, 0.004)
    for side in (-1, 1):
        strap = [(0.5, 0.38), (0.28, 0.38), (0.44, top), (0.66, top)]
        flat(f"Strap {side}", [(side * x, z) for x, z in strap], mats["legs"], torso, 0.004)
    flat("Pocket", [(-0.26, 0.1), (0.26, 0.1), (0.26, -0.3), (0.0, -0.4), (-0.26, -0.3)], mats["trim"], torso, 0.008)
    dots("Stud", [(-0.4, 0.27), (0.4, 0.27)], 0.06, mats["accent"], torso, 0.012)


def dome(name, radius, squash, location, mat, parent):
    bm = bmesh.new()
    verts = bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)["verts"]
    bmesh.ops.scale(bm, vec=(1, 1, squash), verts=verts)
    return link(name, bm, mat, parent, location, bevel=0)


def chef_hat(mats, head):
    """A toque: a tall band with a puffed top. Its origin is where it rests on the head."""
    hat = bpy.data.objects.new("Hat", None)
    hat.parent, hat.location = head, (0, 0, HAT_Z)
    bpy.context.scene.collection.objects.link(hat)
    cylinder("Hat band", 0.95, 0.7, (0, 0, 0.35), mats["top"], hat, bevel=0.04)
    dome("Hat puff", 1.18, 0.55, (0, 0, 1.0), mats["top"], hat)
    return hat


def straw_hat(mats, head):
    """A wide-brimmed straw hat with a band."""
    hat = bpy.data.objects.new("Hat", None)
    hat.parent, hat.location = head, (0, 0, HAT_Z)
    hat.rotation_euler.x = 0.12  # tipped back, so the brim clears the face
    bpy.context.scene.collection.objects.link(hat)
    cylinder("Brim", 1.7, 0.09, (0, 0, 0.05), mats["straw"], hat, bevel=0.03)
    cylinder("Crown", 0.95, 0.5, (0, 0, 0.3), mats["straw"], hat, bevel=0.03)
    dome("Crown top", 0.95, 0.35, (0, 0, 0.55), mats["straw"], hat)
    cylinder("Hat ribbon", 0.97, 0.16, (0, 0, 0.18), mats["accent"], hat, bevel=0.02)
    return hat


# What each outfit changes from the suit: materials, the print on the torso, and a hat.
OUTFITS = {
    "suit": ({}, print_suit, None),
    "chef": (
        {
            "top": ("Jacket", (0.8, 0.8, 0.77), 0.4, 0.2),
            "cuff": ("Jacket cuff", (0.8, 0.8, 0.77), 0.4, 0.2),
            "legs": ("Chef trousers", (0.05, 0.055, 0.065), 0.4, 0.2),
            "belt": ("Apron tie", (0.8, 0.8, 0.77), 0.4, 0.2),
            "trim": ("Jacket trim", (0.3, 0.31, 0.33), 0.35, 0.0),
            "accent": ("Neckerchief", (0.6, 0.03, 0.02), 0.35, 0.0),
        },
        print_chef,
        chef_hat,
    ),
    "gardener": (
        {
            "top": ("Work shirt", (0.55, 0.05, 0.03), 0.45, 0.1),
            "cuff": ("Work shirt cuff", (0.55, 0.05, 0.03), 0.45, 0.1),
            "legs": ("Denim", (0.03, 0.11, 0.36), 0.45, 0.1),
            "belt": ("Denim waist", (0.03, 0.11, 0.36), 0.45, 0.1),
            "trim": ("Denim pocket", (0.05, 0.17, 0.48), 0.45, 0.0),
            "accent": ("Brass", (0.75, 0.42, 0.05), 0.25, 0.3),
            "shoe": ("Boot", (0.09, 0.04, 0.015), 0.4, 0.2),
            "straw": ("Straw", (0.72, 0.5, 0.16), 0.6, 0.0),
        },
        print_overalls,
        straw_hat,
    ),
}


def bent_arm(name, mats, parent, location):
    """One moulded arm, origin at the shoulder: it hangs down and bends forward at the elbow,
    with a shirt cuff and a clip hand on the end."""
    bm = bmesh.new()
    # The shoulder is a low dome no wider than the arm, not a ball.
    dome = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.3)["verts"]
    bmesh.ops.scale(bm, vec=(1, 1, 0.55), verts=dome)
    # Walk the centre line: straight upper arm, a short curve at the elbow, straight forearm.
    angles = [0.0] * 5 + [ELBOW * (i + 1) / 6 for i in range(6)] + [ELBOW] * 4
    steps = [0.11] * 5 + [0.05] * 6 + [0.1] * 4
    point, path = (0.0, 0.0, 0.0), []
    for angle, step in zip(angles, steps):
        path.append((point, angle))
        point = (0.0, point[1] - step * math.sin(angle), point[2] - step * math.cos(angle))
    path.append((point, ELBOW))
    rings = []
    for i, ((_, y, z), angle) in enumerate(path):
        radius = 0.3 - 0.05 * i / (len(path) - 1)
        ring = []
        for k in range(24):
            a = 2 * math.pi * k / 24
            across, along = radius * math.cos(a), radius * math.sin(a)
            ring.append(bm.verts.new((across, y + along * math.cos(angle), z - along * math.sin(angle))))
        rings.append(ring)
    for lower, upper in zip(rings, rings[1:]):
        for k in range(24):
            bm.faces.new((lower[k], lower[(k + 1) % 24], upper[(k + 1) % 24], upper[k]))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    arm = link(name, bm, mats["top"], parent, location, bevel=0)

    forearm = (0.0, -math.sin(ELBOW), -math.cos(ELBOW))
    cuff = cylinder(f"{name} cuff", 0.27, 0.1, tuple(c + 0.02 * d for c, d in zip(point, forearm)), mats["cuff"], arm, bevel=0.015)
    hand = clip_hand(f"{name} hand", mats["skin"], arm, tuple(c + 0.4 * d for c, d in zip(point, forearm)))
    hand.scale = (0.85,) * 3
    cuff.rotation_euler.x = hand.rotation_euler.x = -ELBOW  # in line with the forearm
    return arm, hand


def build_figure(outfit="suit"):
    """`outfit` is "suit", "chef" or "gardener". Returns the parts to animate:
    root  - place, turn and scale the whole figure
    pose  - squash and stretch from the feet
    body  - everything above the hips, pivoting at the waist
    head  - turns and tilts about its centre
    arms  - each pivots at its shoulder; negative x rotation raises it forward
    hands - each turns at its wrist
    legs  - each pivots at its hip
    hat   - the outfit's hat, resting on the head (None for the suit)
    hair  - the "full" hair piece and, with a hat, the "under hat" one that is shown
    """
    picture, image = load_picture()
    art = read_head(picture)
    skin = linear(art["skin"])
    strands = art["hair"] & (picture[..., 0] > 0.3) & (picture[..., 0] < 0.75)
    brown = linear(np.median(picture[strands], axis=0))
    mats = {
        "skin": material("Skin", skin, 0.22, coat=0.5),
        "suit": material("Suit", (0.09, 0.15, 0.22), 0.25, coat=0.5),
        "lapel": material("Lapel", (0.16, 0.25, 0.35), 0.3),
        "shirt": material("Shirt", (0.85, 0.85, 0.85), 0.3),
        "tie": material("Tie", (0.0, 0.22, 0.85), 0.3),
        "hair": material("Hair back", brown, 0.5),
        "ink": material("Ink", (0.012, 0.012, 0.02), 0.35),
        "belt": material("Belt", (0.012, 0.012, 0.014), 0.3, coat=0.3),
        "buckle": material("Buckle", (0.55, 0.55, 0.5), 0.25),
        "shoe": material("Shoe", (0.015, 0.013, 0.012), 0.18, coat=0.6),
    }
    mats.update(top=mats["suit"], legs=mats["suit"], cuff=mats["shirt"])
    changes, print_torso, make_hat = OUTFITS[outfit]
    for part, (name, rgb, roughness, coat) in changes.items():
        mats[part] = material(name, rgb, roughness, coat=coat)

    def empty(name, parent, location=(0, 0, 0)):
        obj = bpy.data.objects.new(name, None)
        obj.parent, obj.location = parent, location
        bpy.context.scene.collection.objects.link(obj)
        return obj

    root = empty("Figure", None)
    pose = empty("Pose", root)

    legs = []
    for side in (-1, 1):
        # Origin at the hip, so a leg swings from its rounded top like the real thing.
        leg = box(f"Leg {side}", (0.96, 1.0, 1.3), (side * 0.5, 0, HIP_Z), mats["legs"], pose, offset=(0, 0, -0.65))
        bm = bmesh.new()
        barrel = bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.5, radius2=0.5, depth=0.96)["verts"]
        bmesh.ops.rotate(bm, verts=barrel, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        link(f"Hip {side}", bm, mats["legs"], leg)
        box(f"Shoe {side}", (0.98, 1.3, 0.3), (0, -0.14, -1.35), mats["shoe"], leg, bevel=0.07)
        legs.append(leg)
    belt = box("Belt", (2.0, 1.0, 0.3), (0, 0, HIP_Z + 0.15), mats["belt"], pose)
    if outfit == "suit":
        flat("Buckle", [(-0.14, -0.09), (0.14, -0.09), (0.14, 0.09), (-0.14, 0.09)], mats["buckle"], belt, 0.004)

    body = empty("Body", pose, (0, 0, WAIST_Z))
    torso = box("Torso", (2.0, 1.0, 1.9), (0, 0, 0.95), mats["top"], body, taper=0.78)
    print_torso(torso, mats)
    arms, hands = [], []
    for side in (-1, 1):
        arm, hand = bent_arm(f"Arm {side}", mats, body, (side * 1.05, 0, 1.6))
        arm.rotation_euler.y = -side * 0.16  # hangs a little away from the body
        arms.append(arm)
        hands.append(hand)

    cylinder("Neck", 0.45, 0.2, (0, 0, 1.98), mats["skin"], body)
    head_z = HEAD_Z - WAIST_Z
    head = cylinder("Head", HEAD_R, HEAD_H, (0, 0, head_z), head_material(art, picture, skin), body, bevel=0.14)
    # Hair: the hair from the picture as one piece over the top, and a plain shell round the back.
    # A hat takes the place of the hair above its brim, so there are two hair pieces: the
    # full one, and the part that shows under a hat.
    hair_mat = hair_material(art, image, brown)
    hair = {"full": hair_piece(art, hair_mat, head)}
    if make_hat:
        hair["under hat"] = hair_piece(art, hair_mat, head, below=HAT_Z)
        hair["full"].hide_render = True
    cylinder("Hair back", HEAD_R + 0.04, 1.0, (0, 0, 0.25), mats["hair"], head, bevel=0.06, back_of=0.15)
    hat = make_hat(mats, head) if make_hat else None
    return {"root": root, "pose": pose, "body": body, "head": head, "arms": arms, "hands": hands, "legs": legs, "hat": hat, "hair": hair}
