import bpy
import bmesh
import math
from mathutils import Vector

from . import materials


# ---------------------------------------------------------------------------
# Model catalog – each entry describes one model the user can add.
# ---------------------------------------------------------------------------

MODEL_CATALOG = [
    # -- Primitives --
    {
        "id": "rounded_cube",
        "name": "Rounded Cube",
        "description": "A cube with beveled edges",
        "category": "Primitives",
        "tags": ["cube", "rounded", "primitive"],
        "generator": "generate_rounded_cube",
    },
    {
        "id": "torus_knot",
        "name": "Torus Knot",
        "description": "A decorative torus knot shape",
        "category": "Primitives",
        "tags": ["torus", "knot", "primitive"],
        "generator": "generate_torus_knot",
    },
    {
        "id": "diamond",
        "name": "Diamond",
        "description": "A diamond / gem shape",
        "category": "Primitives",
        "tags": ["diamond", "gem", "primitive"],
        "generator": "generate_diamond",
    },
    {
        "id": "star",
        "name": "Star",
        "description": "A 3D extruded star",
        "category": "Primitives",
        "tags": ["star", "primitive"],
        "generator": "generate_star",
    },
    # -- Furniture --
    {
        "id": "table",
        "name": "Table",
        "description": "A simple four-legged table",
        "category": "Furniture",
        "tags": ["table", "furniture"],
        "generator": "generate_table",
    },
    {
        "id": "chair",
        "name": "Chair",
        "description": "A basic chair with backrest",
        "category": "Furniture",
        "tags": ["chair", "furniture", "seat"],
        "generator": "generate_chair",
    },
    {
        "id": "bookshelf",
        "name": "Bookshelf",
        "description": "A bookshelf with shelves",
        "category": "Furniture",
        "tags": ["bookshelf", "furniture", "storage"],
        "generator": "generate_bookshelf",
    },
    # -- Nature --
    {
        "id": "tree",
        "name": "Simple Tree",
        "description": "A stylised low-poly tree",
        "category": "Nature",
        "tags": ["tree", "nature", "plant"],
        "generator": "generate_tree",
    },
    {
        "id": "rock",
        "name": "Rock",
        "description": "A rough rock / boulder",
        "category": "Nature",
        "tags": ["rock", "nature", "stone"],
        "generator": "generate_rock",
    },
    {
        "id": "mushroom",
        "name": "Mushroom",
        "description": "A cartoon-style mushroom",
        "category": "Nature",
        "tags": ["mushroom", "nature", "plant"],
        "generator": "generate_mushroom",
    },
]


def get_categories():
    """Return sorted unique categories from the catalog."""
    cats = sorted({m["category"] for m in MODEL_CATALOG})
    return cats


def get_model_by_id(model_id):
    for m in MODEL_CATALOG:
        if m["id"] == model_id:
            return m
    return None


def call_generator(model_id):
    """Call the generator function for *model_id* and return the created object."""
    entry = get_model_by_id(model_id)
    if entry is None:
        return None
    fn = globals().get(entry["generator"])
    if fn is None:
        return None
    return fn()


# ===================================================================
#  Generator helpers
# ===================================================================

def _new_mesh_object(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def _deselect_all():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def _assign_material(obj, mat):
    """Append a material to the object's mesh data."""
    obj.data.materials.append(mat)


# ===================================================================
#  Primitives
# ===================================================================

def generate_rounded_cube():
    _deselect_all()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.1, segments=4, affect='EDGES')
    mesh = bpy.data.meshes.new("RoundedCube")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("RoundedCube", mesh)
    _assign_material(obj, materials.create_rounded_cube_material())
    return obj


def generate_torus_knot():
    _deselect_all()
    # Parametric torus knot (p=2, q=3)
    p, q = 2, 3
    segments = 128
    tube_radius = 0.08
    torus_radius = 0.5

    verts = []
    for i in range(segments):
        t = 2 * math.pi * i / segments
        r = torus_radius + 0.3 * math.cos(q * t)
        x = r * math.cos(p * t)
        y = r * math.sin(p * t)
        z = 0.3 * math.sin(q * t)
        verts.append(Vector((x, y, z)))

    bm = bmesh.new()
    bm_verts = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()

    for i in range(segments):
        bm.edges.new((bm_verts[i], bm_verts[(i + 1) % segments]))

    # Convert the curve to a tube using spin
    mesh = bpy.data.meshes.new("TorusKnot")
    bm.to_mesh(mesh)
    bm.free()

    obj = _new_mesh_object("TorusKnot", mesh)

    # Add a skin modifier to give it thickness, then a subdivision surface
    skin = obj.modifiers.new("Skin", 'SKIN')
    for v in obj.data.skin_vertices[0].data:
        v.radius = (tube_radius, tube_radius)
    sub = obj.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 2
    sub.render_levels = 2

    _assign_material(obj, materials.create_torus_knot_material())
    return obj


def generate_diamond():
    _deselect_all()
    bm = bmesh.new()
    segments = 8
    radius = 0.5
    top_height = 0.3
    bottom_height = -0.8

    # Top center
    top = bm.verts.new((0, 0, top_height))
    # Bottom point
    bottom = bm.verts.new((0, 0, bottom_height))
    # Middle ring
    ring = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        v = bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), 0))
        ring.append(v)

    bm.verts.ensure_lookup_table()

    # Top faces
    for i in range(segments):
        bm.faces.new((top, ring[i], ring[(i + 1) % segments]))
    # Bottom faces
    for i in range(segments):
        bm.faces.new((bottom, ring[(i + 1) % segments], ring[i]))

    mesh = bpy.data.meshes.new("Diamond")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Diamond", mesh)
    _assign_material(obj, materials.create_diamond_material())
    return obj


def generate_star():
    _deselect_all()
    bm = bmesh.new()
    points = 5
    outer_r = 0.6
    inner_r = 0.25
    depth = 0.15

    # Create star profile vertices (front and back)
    front_verts = []
    back_verts = []
    for i in range(points * 2):
        angle = math.pi / 2 + 2 * math.pi * i / (points * 2)
        r = outer_r if i % 2 == 0 else inner_r
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        front_verts.append(bm.verts.new((x, y, depth)))
        back_verts.append(bm.verts.new((x, y, -depth)))

    bm.verts.ensure_lookup_table()
    n = points * 2

    # Front face
    bm.faces.new(front_verts)
    # Back face
    bm.faces.new(list(reversed(back_verts)))
    # Side faces
    for i in range(n):
        ni = (i + 1) % n
        bm.faces.new((front_verts[i], front_verts[ni], back_verts[ni], back_verts[i]))

    mesh = bpy.data.meshes.new("Star")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Star", mesh)
    _assign_material(obj, materials.create_star_material())
    return obj


# ===================================================================
#  Furniture
# ===================================================================

def _add_box(bm, center, size):
    """Add a box to a bmesh at *center* with *size* (x, y, z)."""
    mat = bmesh.ops.create_cube(bm, size=1.0)
    verts = mat["verts"] if "verts" in mat else [v for v in bm.verts if v.is_valid]
    # We need to get the newly created verts — create_cube returns them
    new_verts = mat.get("verts", [])
    # Scale and translate
    for v in new_verts:
        v.co.x = v.co.x * size[0] + center[0]
        v.co.y = v.co.y * size[1] + center[1]
        v.co.z = v.co.z * size[2] + center[2]
    return new_verts


def generate_table():
    _deselect_all()
    bm = bmesh.new()

    top_height = 0.75
    top_thickness = 0.05
    top_width = 1.2
    top_depth = 0.7
    leg_thickness = 0.05
    leg_inset = 0.08

    # Table top
    _add_box(bm, (0, 0, top_height), (top_width, top_depth, top_thickness))

    # Four legs
    leg_h = top_height - top_thickness / 2
    positions = [
        (top_width / 2 - leg_inset, top_depth / 2 - leg_inset),
        (-top_width / 2 + leg_inset, top_depth / 2 - leg_inset),
        (top_width / 2 - leg_inset, -top_depth / 2 + leg_inset),
        (-top_width / 2 + leg_inset, -top_depth / 2 + leg_inset),
    ]
    for px, py in positions:
        _add_box(bm, (px, py, leg_h / 2), (leg_thickness, leg_thickness, leg_h))

    mesh = bpy.data.meshes.new("Table")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Table", mesh)
    _assign_material(obj, materials.create_table_material())
    return obj


def generate_chair():
    _deselect_all()
    bm = bmesh.new()

    seat_h = 0.45
    seat_size = 0.45
    seat_thick = 0.04
    leg_thick = 0.04
    back_height = 0.45
    back_thick = 0.04
    leg_inset = 0.04

    # Seat
    _add_box(bm, (0, 0, seat_h), (seat_size, seat_size, seat_thick))

    # Legs
    positions = [
        (seat_size / 2 - leg_inset, seat_size / 2 - leg_inset),
        (-seat_size / 2 + leg_inset, seat_size / 2 - leg_inset),
        (seat_size / 2 - leg_inset, -seat_size / 2 + leg_inset),
        (-seat_size / 2 + leg_inset, -seat_size / 2 + leg_inset),
    ]
    for px, py in positions:
        _add_box(bm, (px, py, seat_h / 2), (leg_thick, leg_thick, seat_h))

    # Backrest
    _add_box(bm, (0, -seat_size / 2 + back_thick / 2, seat_h + back_height / 2),
             (seat_size, back_thick, back_height))

    mesh = bpy.data.meshes.new("Chair")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Chair", mesh)
    _assign_material(obj, materials.create_chair_material())
    return obj


def generate_bookshelf():
    _deselect_all()
    bm = bmesh.new()

    width = 0.8
    depth = 0.3
    height = 1.6
    board_thick = 0.03
    n_shelves = 4

    # Side panels
    _add_box(bm, (-width / 2, 0, height / 2), (board_thick, depth, height))
    _add_box(bm, (width / 2, 0, height / 2), (board_thick, depth, height))

    # Top and bottom + shelves
    inner_w = width - board_thick
    for i in range(n_shelves + 1):
        z = (height / n_shelves) * i + board_thick / 2
        if z > height:
            z = height - board_thick / 2
        _add_box(bm, (0, 0, z), (inner_w, depth, board_thick))

    # Back panel
    _add_box(bm, (0, -depth / 2 + board_thick / 2, height / 2),
             (width, board_thick, height))

    mesh = bpy.data.meshes.new("Bookshelf")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Bookshelf", mesh)
    _assign_material(obj, materials.create_bookshelf_material())
    return obj


# ===================================================================
#  Nature
# ===================================================================

def generate_tree():
    _deselect_all()
    bm = bmesh.new()

    # Trunk — cylinder approximation via octagonal prism
    trunk_r = 0.08
    trunk_h = 0.8
    segments = 8
    bottom_ring = []
    top_ring = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        bottom_ring.append(bm.verts.new((trunk_r * math.cos(a), trunk_r * math.sin(a), 0)))
        top_ring.append(bm.verts.new((trunk_r * math.cos(a), trunk_r * math.sin(a), trunk_h)))

    bm.verts.ensure_lookup_table()
    # Side faces
    for i in range(segments):
        ni = (i + 1) % segments
        bm.faces.new((bottom_ring[i], bottom_ring[ni], top_ring[ni], top_ring[i]))
    # Bottom cap
    bm.faces.new(list(reversed(bottom_ring)))
    # Top cap
    bm.faces.new(top_ring)

    # Foliage — 3 stacked cones
    for layer_i, (cone_r, cone_h, z_off) in enumerate([
        (0.45, 0.45, trunk_h - 0.1),
        (0.35, 0.40, trunk_h + 0.25),
        (0.25, 0.35, trunk_h + 0.55),
    ]):
        tip = bm.verts.new((0, 0, z_off + cone_h))
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(bm.verts.new((cone_r * math.cos(a), cone_r * math.sin(a), z_off)))
        bm.verts.ensure_lookup_table()
        for i in range(segments):
            ni = (i + 1) % segments
            bm.faces.new((ring[i], ring[ni], tip))
        bm.faces.new(list(reversed(ring)))

    mesh = bpy.data.meshes.new("SimpleTree")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("SimpleTree", mesh)
    _assign_material(obj, materials.create_tree_material())
    return obj


def generate_rock():
    _deselect_all()
    import random
    seed = 42
    rng = random.Random(seed)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)

    # Randomly displace vertices for a rocky look
    for v in bm.verts:
        displacement = rng.uniform(0.85, 1.15)
        v.co *= displacement
        # Flatten bottom slightly
        if v.co.z < 0:
            v.co.z *= 0.6

    mesh = bpy.data.meshes.new("Rock")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Rock", mesh)
    _assign_material(obj, materials.create_rock_material())
    return obj


def generate_mushroom():
    _deselect_all()
    bm = bmesh.new()
    segments = 12

    # Stem — cylinder
    stem_r = 0.06
    stem_h = 0.35
    bottom_ring = []
    top_ring = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        bottom_ring.append(bm.verts.new((stem_r * math.cos(a), stem_r * math.sin(a), 0)))
        top_ring.append(bm.verts.new((stem_r * math.cos(a), stem_r * math.sin(a), stem_h)))

    bm.verts.ensure_lookup_table()
    for i in range(segments):
        ni = (i + 1) % segments
        bm.faces.new((bottom_ring[i], bottom_ring[ni], top_ring[ni], top_ring[i]))
    bm.faces.new(list(reversed(bottom_ring)))

    # Cap — dome (half sphere approximation with rings)
    cap_base_z = stem_h - 0.02
    cap_r = 0.25
    cap_h = 0.18
    n_rings = 4

    rings = []
    for j in range(n_rings):
        angle = (math.pi / 2) * (j + 1) / (n_rings + 1)
        r = cap_r * math.cos(angle)
        z = cap_base_z + cap_h * math.sin(angle)
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)

    # Cap base ring (widest)
    base_ring = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        base_ring.append(bm.verts.new((cap_r * math.cos(a), cap_r * math.sin(a), cap_base_z)))

    # Cap top vertex
    cap_top = bm.verts.new((0, 0, cap_base_z + cap_h))

    bm.verts.ensure_lookup_table()

    # Connect base ring to first ring
    all_rings = [base_ring] + rings
    for ri in range(len(all_rings) - 1):
        for i in range(segments):
            ni = (i + 1) % segments
            bm.faces.new((all_rings[ri][i], all_rings[ri][ni],
                          all_rings[ri + 1][ni], all_rings[ri + 1][i]))

    # Connect last ring to top vertex
    last_ring = all_rings[-1]
    for i in range(segments):
        ni = (i + 1) % segments
        bm.faces.new((last_ring[i], last_ring[ni], cap_top))

    # Bottom cap of mushroom cap
    bm.faces.new(list(reversed(base_ring)))

    mesh = bpy.data.meshes.new("Mushroom")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = _new_mesh_object("Mushroom", mesh)
    _assign_material(obj, materials.create_mushroom_material())
    return obj
