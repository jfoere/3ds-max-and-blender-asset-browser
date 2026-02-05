"""
Procedural materials for the Model Library addon.

Each public function creates and returns a bpy.data.materials.Material
with a fully procedural node setup.
"""

import bpy


# ===================================================================
#  Private helpers
# ===================================================================

def _new_material(name):
    """Create a new node-based material with 'ML_' prefix."""
    mat = bpy.data.materials.new(f"ML_{name}")
    mat.use_nodes = True
    return mat


def _get_principled(mat):
    """Return the Principled BSDF node."""
    return mat.node_tree.nodes.get("Principled BSDF")


def _add_node(mat, node_type, location=(0, 0)):
    """Add a shader node at the given location."""
    node = mat.node_tree.nodes.new(node_type)
    node.location = location
    return node


def _link(mat, from_node, from_socket, to_node, to_socket):
    """Shorthand for creating a node link."""
    mat.node_tree.links.new(
        from_node.outputs[from_socket],
        to_node.inputs[to_socket],
    )


def _set_bsdf_input(bsdf, name, value, fallback_name=None):
    """Set a Principled BSDF input, handling Blender 3.x vs 4.0+ name changes."""
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value
    elif fallback_name and fallback_name in bsdf.inputs:
        bsdf.inputs[fallback_name].default_value = value


def _is_blender_4():
    """Check if running Blender 4.0+."""
    return bpy.app.version >= (4, 0, 0)


def _add_mix_color_node(mat, location=(0, 0), blend_type='MIX', fac=0.5):
    """Add a color mix node, compatible with Blender 3.x and 4.0+."""
    if _is_blender_4():
        node = _add_node(mat, "ShaderNodeMix", location)
        node.data_type = 'RGBA'
        node.blend_type = blend_type
        node.inputs["Factor"].default_value = fac
        return node
    else:
        node = _add_node(mat, "ShaderNodeMixRGB", location)
        node.blend_type = blend_type
        node.inputs["Fac"].default_value = fac
        return node


def _mix_color_sockets(is_b4):
    """Return (fac, color1, color2, result) socket names for the mix node."""
    if is_b4:
        return ("Factor", "A", "B", "Result")
    else:
        return ("Fac", "Color1", "Color2", "Color")


# ===================================================================
#  Shared material builders
# ===================================================================

def _create_wood_material(name, color_light, color_dark, roughness=0.45):
    """Shared procedural wood-grain material for furniture."""
    mat = _new_material(name)
    tree = mat.node_tree
    bsdf = _get_principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    _set_bsdf_input(bsdf, "Specular", 0.3, "Specular IOR Level")

    # Texture Coordinate -> Mapping
    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-800, 300))
    mapping = _add_node(mat, "ShaderNodeMapping", (-600, 300))
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 5.0)
    _link(mat, tex_coord, "Object", mapping, "Vector")

    # Wave Texture (wood grain bands)
    wave = _add_node(mat, "ShaderNodeTexWave", (-400, 300))
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 2.0
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 3.0
    _link(mat, mapping, "Vector", wave, "Vector")

    # Noise Texture (grain irregularity)
    noise = _add_node(mat, "ShaderNodeTexNoise", (-400, 50))
    noise.inputs["Scale"].default_value = 15.0
    _link(mat, mapping, "Vector", noise, "Vector")

    # Mix wave and noise for variation
    b4 = _is_blender_4()
    mix = _add_mix_color_node(mat, (-200, 200), blend_type='ADD', fac=0.15)
    fac_s, c1_s, c2_s, out_s = _mix_color_sockets(b4)
    _link(mat, wave, "Color", mix, c1_s)
    _link(mat, noise, "Fac", mix, c2_s)

    # ColorRamp (wood tones)
    ramp = _add_node(mat, "ShaderNodeValToRGB", (-50, 200))
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (*color_light, 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*color_dark, 1.0)
    _link(mat, mix, out_s, ramp, "Fac")

    # Connect to BSDF
    _link(mat, ramp, "Color", bsdf, "Base Color")

    return mat


# ===================================================================
#  Primitives
# ===================================================================

def create_rounded_cube_material():
    """Warm ceramic with subtle noise variation."""
    mat = _new_material("RoundedCube_Ceramic")
    bsdf = _get_principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.35
    _set_bsdf_input(bsdf, "Specular", 0.5, "Specular IOR Level")

    # Texture Coordinate -> Noise Texture
    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-600, 300))
    noise = _add_node(mat, "ShaderNodeTexNoise", (-400, 300))
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.5
    _link(mat, tex_coord, "Object", noise, "Vector")

    # ColorRamp (warm beige tones)
    ramp = _add_node(mat, "ShaderNodeValToRGB", (-200, 300))
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.831, 0.647, 0.455, 1.0)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.722, 0.525, 0.361, 1.0)
    _link(mat, noise, "Fac", ramp, "Fac")

    _link(mat, ramp, "Color", bsdf, "Base Color")
    return mat


def create_torus_knot_material():
    """Iridescent metallic rainbow along the knot."""
    mat = _new_material("TorusKnot_Iridescent")
    bsdf = _get_principled(mat)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.15
    _set_bsdf_input(bsdf, "Specular", 0.8, "Specular IOR Level")

    # Texture Coordinate -> Separate XYZ
    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-800, 300))
    sep_xyz = _add_node(mat, "ShaderNodeSeparateXYZ", (-600, 300))
    _link(mat, tex_coord, "Object", sep_xyz, "Vector")

    # Add X + Y
    add_xy = _add_node(mat, "ShaderNodeMath", (-400, 300))
    add_xy.operation = 'ADD'
    _link(mat, sep_xyz, "X", add_xy, 0)
    _link(mat, sep_xyz, "Y", add_xy, 1)

    # Add (X+Y) + Z
    add_xyz = _add_node(mat, "ShaderNodeMath", (-250, 300))
    add_xyz.operation = 'ADD'
    _link(mat, add_xy, "Value", add_xyz, 0)
    _link(mat, sep_xyz, "Z", add_xyz, 1)

    # Multiply to spread the gradient
    mult = _add_node(mat, "ShaderNodeMath", (-100, 300))
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 2.0
    _link(mat, add_xyz, "Value", mult, 0)

    # Rainbow ColorRamp
    ramp = _add_node(mat, "ShaderNodeValToRGB", (100, 300))
    elems = ramp.color_ramp.elements
    # Start with 2 default elements, add 4 more
    elems[0].position = 0.0
    elems[0].color = (0.8, 0.1, 0.1, 1.0)
    elems[1].position = 0.2
    elems[1].color = (0.9, 0.5, 0.1, 1.0)
    e = elems.new(0.4)
    e.color = (0.9, 0.9, 0.2, 1.0)
    e = elems.new(0.6)
    e.color = (0.2, 0.8, 0.3, 1.0)
    e = elems.new(0.8)
    e.color = (0.2, 0.4, 0.9, 1.0)
    e = elems.new(1.0)
    e.color = (0.6, 0.2, 0.8, 1.0)
    _link(mat, mult, "Value", ramp, "Fac")

    _link(mat, ramp, "Color", bsdf, "Base Color")
    return mat


def create_diamond_material():
    """Transparent crystal with high IOR."""
    mat = _new_material("Diamond_Crystal")
    bsdf = _get_principled(mat)

    bsdf.inputs["Base Color"].default_value = (0.85, 0.92, 1.0, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 2.42
    _set_bsdf_input(bsdf, "Transmission", 1.0, "Transmission Weight")
    _set_bsdf_input(bsdf, "Specular", 0.5, "Specular IOR Level")

    # Eevee transparency support (Blender 3.x)
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'HASHED'

    return mat


def create_star_material():
    """Glossy gold metal."""
    mat = _new_material("Star_Gold")
    bsdf = _get_principled(mat)

    bsdf.inputs["Base Color"].default_value = (1.0, 0.766, 0.336, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.2
    _set_bsdf_input(bsdf, "Specular", 0.5, "Specular IOR Level")

    # Subtle roughness variation via noise
    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-400, 0))
    noise = _add_node(mat, "ShaderNodeTexNoise", (-200, 0))
    noise.inputs["Scale"].default_value = 20.0
    noise.inputs["Detail"].default_value = 5.0
    _link(mat, tex_coord, "Object", noise, "Vector")

    # Multiply noise to keep roughness variation subtle
    mult = _add_node(mat, "ShaderNodeMath", (0, 0))
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 0.05
    _link(mat, noise, "Fac", mult, 0)

    # Add base roughness + noise variation
    add = _add_node(mat, "ShaderNodeMath", (150, 0))
    add.operation = 'ADD'
    add.inputs[1].default_value = 0.2
    _link(mat, mult, "Value", add, 0)

    _link(mat, add, "Value", bsdf, "Roughness")
    return mat


# ===================================================================
#  Furniture (all use the shared wood helper)
# ===================================================================

def create_table_material():
    """Medium-tone wood grain."""
    return _create_wood_material(
        "Table_Wood",
        color_light=(0.769, 0.580, 0.290),
        color_dark=(0.545, 0.369, 0.235),
        roughness=0.45,
    )


def create_chair_material():
    """Dark walnut wood grain."""
    return _create_wood_material(
        "Chair_Walnut",
        color_light=(0.545, 0.369, 0.235),
        color_dark=(0.361, 0.220, 0.125),
        roughness=0.5,
    )


def create_bookshelf_material():
    """Light pine wood grain."""
    return _create_wood_material(
        "Bookshelf_Pine",
        color_light=(0.878, 0.741, 0.529),
        color_dark=(0.710, 0.557, 0.353),
        roughness=0.5,
    )


# ===================================================================
#  Nature
# ===================================================================

def create_tree_material():
    """Height-based brown trunk to green foliage transition."""
    mat = _new_material("Tree_TrunkFoliage")
    bsdf = _get_principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.7

    # Object-space Z coordinate
    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-800, 300))
    sep_xyz = _add_node(mat, "ShaderNodeSeparateXYZ", (-600, 300))
    _link(mat, tex_coord, "Object", sep_xyz, "Vector")

    # Normalize Z: divide by approximate total height (~1.7)
    normalize = _add_node(mat, "ShaderNodeMath", (-400, 300))
    normalize.operation = 'DIVIDE'
    normalize.inputs[1].default_value = 1.7
    _link(mat, sep_xyz, "Z", normalize, 0)

    # Noise for organic boundary variation
    noise = _add_node(mat, "ShaderNodeTexNoise", (-600, 50))
    noise.inputs["Scale"].default_value = 8.0
    _link(mat, tex_coord, "Object", noise, "Vector")

    noise_scale = _add_node(mat, "ShaderNodeMath", (-400, 50))
    noise_scale.operation = 'MULTIPLY'
    noise_scale.inputs[1].default_value = 0.1
    _link(mat, noise, "Fac", noise_scale, 0)

    # Add noise to normalized Z
    add_noise = _add_node(mat, "ShaderNodeMath", (-200, 200))
    add_noise.operation = 'ADD'
    _link(mat, normalize, "Value", add_noise, 0)
    _link(mat, noise_scale, "Value", add_noise, 1)

    # ColorRamp: brown trunk -> green foliage
    ramp = _add_node(mat, "ShaderNodeValToRGB", (0, 200))
    elems = ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = (0.361, 0.227, 0.118, 1.0)  # trunk base
    elems[1].position = 0.40
    elems[1].color = (0.420, 0.259, 0.149, 1.0)  # trunk top
    e = elems.new(0.45)
    e.color = (0.176, 0.353, 0.118, 1.0)  # foliage start
    e = elems.new(0.55)
    e.color = (0.239, 0.478, 0.180, 1.0)  # foliage mid
    e = elems.new(1.0)
    e.color = (0.118, 0.290, 0.071, 1.0)  # foliage tips
    _link(mat, add_noise, "Value", ramp, "Fac")

    _link(mat, ramp, "Color", bsdf, "Base Color")
    return mat


def create_rock_material():
    """Gray stone with noise-driven color variation and bump."""
    mat = _new_material("Rock_Stone")
    bsdf = _get_principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.85
    _set_bsdf_input(bsdf, "Specular", 0.3, "Specular IOR Level")

    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-800, 300))

    # Color noise
    color_noise = _add_node(mat, "ShaderNodeTexNoise", (-500, 300))
    color_noise.inputs["Scale"].default_value = 3.0
    color_noise.inputs["Detail"].default_value = 6.0
    color_noise.inputs["Roughness"].default_value = 0.8
    _link(mat, tex_coord, "Object", color_noise, "Vector")

    # Color ramp (grays with slight warm tone)
    ramp = _add_node(mat, "ShaderNodeValToRGB", (-200, 300))
    elems = ramp.color_ramp.elements
    elems[0].position = 0.3
    elems[0].color = (0.24, 0.24, 0.24, 1.0)
    elems[1].position = 0.6
    elems[1].color = (0.42, 0.42, 0.42, 1.0)
    e = elems.new(0.9)
    e.color = (0.478, 0.455, 0.408, 1.0)  # warm gray
    _link(mat, color_noise, "Fac", ramp, "Fac")
    _link(mat, ramp, "Color", bsdf, "Base Color")

    # Bump noise (finer detail)
    bump_noise = _add_node(mat, "ShaderNodeTexNoise", (-500, 0))
    bump_noise.inputs["Scale"].default_value = 8.0
    _link(mat, tex_coord, "Object", bump_noise, "Vector")

    bump_scale = _add_node(mat, "ShaderNodeMath", (-300, 0))
    bump_scale.operation = 'MULTIPLY'
    bump_scale.inputs[1].default_value = 0.3
    _link(mat, bump_noise, "Fac", bump_scale, 0)

    bump = _add_node(mat, "ShaderNodeBump", (-100, 0))
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.02
    _link(mat, bump_scale, "Value", bump, "Height")
    _link(mat, bump, "Normal", bsdf, "Normal")

    return mat


def create_mushroom_material():
    """Cream stem, red cap with white voronoi spots."""
    mat = _new_material("Mushroom_Spotted")
    bsdf = _get_principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.6
    _set_bsdf_input(bsdf, "Specular", 0.3, "Specular IOR Level")

    tex_coord = _add_node(mat, "ShaderNodeTexCoord", (-900, 300))

    # --- Height-based stem/cap color ---
    sep_xyz = _add_node(mat, "ShaderNodeSeparateXYZ", (-700, 300))
    _link(mat, tex_coord, "Object", sep_xyz, "Vector")

    # Normalize Z by cap top height (~0.53)
    normalize = _add_node(mat, "ShaderNodeMath", (-500, 300))
    normalize.operation = 'DIVIDE'
    normalize.inputs[1].default_value = 0.53
    _link(mat, sep_xyz, "Z", normalize, 0)

    # Height ramp: cream stem -> red cap
    height_ramp = _add_node(mat, "ShaderNodeValToRGB", (-300, 300))
    elems = height_ramp.color_ramp.elements
    elems[0].position = 0.0
    elems[0].color = (0.960, 0.902, 0.784, 1.0)  # cream stem base
    elems[1].position = 0.55
    elems[1].color = (0.929, 0.851, 0.710, 1.0)  # cream stem top
    e = elems.new(0.65)
    e.color = (0.800, 0.133, 0.133, 1.0)  # red cap start
    e = elems.new(1.0)
    e.color = (0.600, 0.067, 0.067, 1.0)  # dark red cap top
    _link(mat, normalize, "Value", height_ramp, "Fac")

    # --- White spots on cap (Voronoi) ---
    voronoi = _add_node(mat, "ShaderNodeTexVoronoi", (-700, 0))
    voronoi.inputs["Scale"].default_value = 12.0
    if hasattr(voronoi, 'feature'):
        voronoi.feature = 'F1'
    _link(mat, tex_coord, "Object", voronoi, "Vector")

    # Spot mask: distance < threshold = white spot
    spot_thresh = _add_node(mat, "ShaderNodeMath", (-500, 0))
    spot_thresh.operation = 'LESS_THAN'
    spot_thresh.inputs[1].default_value = 0.08
    _link(mat, voronoi, "Distance", spot_thresh, 0)

    # Cap mask: only apply spots where Z > 0.6 (normalized)
    cap_mask = _add_node(mat, "ShaderNodeMath", (-500, -150))
    cap_mask.operation = 'GREATER_THAN'
    cap_mask.inputs[1].default_value = 0.6
    _link(mat, normalize, "Value", cap_mask, 0)

    # Combine: spots only on cap
    spot_on_cap = _add_node(mat, "ShaderNodeMath", (-300, -50))
    spot_on_cap.operation = 'MULTIPLY'
    _link(mat, spot_thresh, "Value", spot_on_cap, 0)
    _link(mat, cap_mask, "Value", spot_on_cap, 1)

    # Mix height color with white where spots are
    b4 = _is_blender_4()
    mix = _add_mix_color_node(mat, (-100, 200), blend_type='MIX', fac=0.0)
    fac_s, c1_s, c2_s, out_s = _mix_color_sockets(b4)
    mix.inputs[c2_s].default_value = (0.933, 0.933, 0.900, 1.0)  # off-white spots
    _link(mat, spot_on_cap, "Value", mix, fac_s)
    _link(mat, height_ramp, "Color", mix, c1_s)

    _link(mat, mix, out_s, bsdf, "Base Color")
    return mat
