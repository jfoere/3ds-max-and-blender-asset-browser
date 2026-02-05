import bpy
import os
import math
from bpy.props import StringProperty

from . import models


class MODELLIB_OT_add_model(bpy.types.Operator):
    """Add a model from the library to the scene"""
    bl_idname = "model_library.add_model"
    bl_label = "Add Model to Scene"
    bl_options = {'REGISTER', 'UNDO'}

    model_id: StringProperty(name="Model ID")  # type: ignore[assignment]

    def execute(self, context):
        entry = models.get_model_by_id(self.model_id)
        if entry is None:
            self.report({'ERROR'}, f"Model '{self.model_id}' not found")
            return {'CANCELLED'}

        cursor_loc = context.scene.cursor.location.copy()

        obj = models.call_generator(self.model_id)
        if obj is None:
            self.report({'ERROR'}, f"Failed to generate model '{self.model_id}'")
            return {'CANCELLED'}

        obj.location = cursor_loc
        self.report({'INFO'}, f"Added '{entry['name']}' at cursor")
        return {'FINISHED'}


class MODELLIB_OT_generate_previews(bpy.types.Operator):
    """Render preview thumbnails for all library models"""
    bl_idname = "model_library.generate_previews"
    bl_label = "Generate Previews"
    bl_options = {'REGISTER'}

    def execute(self, context):
        preview_dir = os.path.join(os.path.dirname(__file__), "previews")
        os.makedirs(preview_dir, exist_ok=True)

        # Save current state
        original_scene = context.window.scene

        # Create a temporary scene for rendering previews
        tmp_scene = bpy.data.scenes.new("_ModelLib_Preview")
        context.window.scene = tmp_scene

        # Setup camera
        cam_data = bpy.data.cameras.new("_PreviewCam")
        cam_data.lens = 50
        cam_obj = bpy.data.objects.new("_PreviewCam", cam_data)
        tmp_scene.collection.objects.link(cam_obj)
        tmp_scene.camera = cam_obj

        # Setup lighting
        light_data = bpy.data.lights.new("_PreviewLight", type='SUN')
        light_data.energy = 3.0
        light_obj = bpy.data.objects.new("_PreviewLight", light_data)
        light_obj.rotation_euler = (math.radians(45), math.radians(15), math.radians(30))
        tmp_scene.collection.objects.link(light_obj)

        # Render settings for small thumbnails
        tmp_scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'ShaderNodeEeveeSpecular') else 'BLENDER_EEVEE'
        tmp_scene.render.resolution_x = 256
        tmp_scene.render.resolution_y = 256
        tmp_scene.render.resolution_percentage = 100
        tmp_scene.render.film_transparent = True
        tmp_scene.render.image_settings.file_format = 'PNG'
        tmp_scene.render.image_settings.color_mode = 'RGBA'

        # Set world background to a neutral gray
        world = bpy.data.worlds.new("_PreviewWorld")
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs[0].default_value = (0.15, 0.15, 0.18, 1.0)
            bg_node.inputs[1].default_value = 0.5
        tmp_scene.world = world

        generated_count = 0
        for entry in models.MODEL_CATALOG:
            model_id = entry["id"]
            filepath = os.path.join(preview_dir, f"{model_id}.png")

            # Generate the model
            obj = models.call_generator(model_id)
            if obj is None:
                continue

            # Use the model's own material if it has one, otherwise add a fallback
            if not obj.data.materials:
                mat = bpy.data.materials.new(f"_Preview_{model_id}")
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Base Color"].default_value = (0.6, 0.65, 0.75, 1.0)
                    bsdf.inputs["Roughness"].default_value = 0.4
                obj.data.materials.append(mat)

            # Frame the object with the camera
            _frame_object(cam_obj, obj)

            # Render
            tmp_scene.render.filepath = filepath
            bpy.ops.render.render(write_still=True, scene=tmp_scene.name)

            # Clean up this model's objects and materials
            mats_to_remove = [m for m in obj.data.materials if m]
            _delete_object_and_data(obj)
            for m in mats_to_remove:
                if m.users == 0:
                    bpy.data.materials.remove(m)

            generated_count += 1

        # Restore original scene and clean up temp scene
        context.window.scene = original_scene
        bpy.data.scenes.remove(tmp_scene)
        bpy.data.cameras.remove(cam_data)
        bpy.data.lights.remove(light_data)
        bpy.data.worlds.remove(world)

        # Reload the preview collection
        from . import ui
        ui.reload_previews()

        self.report({'INFO'}, f"Generated {generated_count} preview thumbnails")
        return {'FINISHED'}


def _frame_object(cam_obj, target_obj):
    """Position camera to nicely frame the target object."""
    # Compute bounding box in world space
    bbox = [target_obj.matrix_world @ bpy.app.driver_namespace.get("Vector", __import__('mathutils').Vector)(corner)
            for corner in target_obj.bound_box]

    center = sum(bbox, __import__('mathutils').Vector((0, 0, 0))) / 8
    # Rough size
    max_dim = max(
        max(v.x for v in bbox) - min(v.x for v in bbox),
        max(v.y for v in bbox) - min(v.y for v in bbox),
        max(v.z for v in bbox) - min(v.z for v in bbox),
    )

    distance = max_dim * 2.2
    cam_obj.location = center + __import__('mathutils').Vector((distance * 0.6, -distance * 0.8, distance * 0.5))

    # Point camera at center
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()


def _delete_object_and_data(obj):
    """Remove an object and its mesh data."""
    mesh = obj.data if obj.type == 'MESH' else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


# -------------------------------------------------------------------
#  Registration
# -------------------------------------------------------------------

classes = (
    MODELLIB_OT_add_model,
    MODELLIB_OT_generate_previews,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
