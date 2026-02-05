import bpy
import os
from bpy.props import StringProperty, EnumProperty
from bpy.types import PropertyGroup

from . import models

# ---------------------------------------------------------------------------
#  Preview image collection
# ---------------------------------------------------------------------------

_preview_collection = None


def _get_preview_dir():
    return os.path.join(os.path.dirname(__file__), "previews")


def _ensure_preview_collection():
    global _preview_collection
    if _preview_collection is not None:
        return _preview_collection

    import bpy.utils.previews
    _preview_collection = bpy.utils.previews.new()
    _load_previews()
    return _preview_collection


def _load_previews():
    """Load preview PNGs from the previews/ folder into the collection."""
    if _preview_collection is None:
        return
    _preview_collection.clear()
    preview_dir = _get_preview_dir()
    if not os.path.isdir(preview_dir):
        return

    for entry in models.MODEL_CATALOG:
        img_path = os.path.join(preview_dir, f"{entry['id']}.png")
        if os.path.isfile(img_path):
            _preview_collection.load(entry["id"], img_path, 'IMAGE')


def reload_previews():
    """Reload all previews (called after generating new thumbnails)."""
    _load_previews()


def _remove_preview_collection():
    global _preview_collection
    if _preview_collection is not None:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None


# ---------------------------------------------------------------------------
#  Filtered model list helpers
# ---------------------------------------------------------------------------

def _get_filtered_models(props):
    """Return models matching current category + search filters."""
    result = models.MODEL_CATALOG
    # Category filter
    if props.category_filter != 'ALL':
        result = [m for m in result if m["category"] == props.category_filter]
    # Search filter
    search = props.search_text.strip().lower()
    if search:
        result = [m for m in result
                  if search in m["name"].lower()
                  or search in m["description"].lower()
                  or any(search in t for t in m["tags"])]
    return result


# ---------------------------------------------------------------------------
#  Category enum items (built dynamically)
# ---------------------------------------------------------------------------

def _category_items(self, context):
    items = [('ALL', 'All', 'Show all categories', 'NONE', 0)]
    for i, cat in enumerate(models.get_categories(), start=1):
        items.append((cat, cat, f'Show {cat} models', 'NONE', i))
    return items


# ---------------------------------------------------------------------------
#  Property group — stores per-scene UI state
# ---------------------------------------------------------------------------

class MODELLIB_PG_properties(PropertyGroup):
    search_text: StringProperty(
        name="Search",
        description="Filter models by name or tag",
        default="",
    )  # type: ignore[assignment]
    category_filter: EnumProperty(
        name="Category",
        description="Filter by category",
        items=_category_items,
    )  # type: ignore[assignment]
    selected_model: StringProperty(
        name="Selected Model",
        default="",
    )  # type: ignore[assignment]


# ---------------------------------------------------------------------------
#  Panel
# ---------------------------------------------------------------------------

class MODELLIB_PT_main_panel(bpy.types.Panel):
    bl_label = "Model Library"
    bl_idname = "MODELLIB_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Model Library"

    def draw(self, context):
        layout = self.layout
        props = context.scene.model_library

        # -- Search --
        row = layout.row(align=True)
        row.prop(props, "search_text", text="", icon='VIEWZOOM')

        # -- Category filter --
        row = layout.row(align=True)
        row.prop(props, "category_filter", text="")

        layout.separator()

        # -- Model list with previews --
        pcoll = _ensure_preview_collection()
        filtered = _get_filtered_models(props)
        previews_available = len(pcoll) > 0

        if not filtered:
            layout.label(text="No models match the filter.", icon='INFO')
        else:
            # Grid layout: show models as boxes with preview + name + button
            for entry in filtered:
                box = layout.box()

                # Preview image row
                if previews_available and entry["id"] in pcoll:
                    icon_id = pcoll[entry["id"]].icon_id
                    box.template_icon(icon_value=icon_id, scale=5.0)
                else:
                    # Fallback: use a built-in icon
                    fallback_icons = {
                        "Primitives": "MESH_CUBE",
                        "Furniture": "OBJECT_DATA",
                        "Nature": "FORCE_WIND",
                    }
                    icon = fallback_icons.get(entry["category"], "MESH_DATA")
                    row_icon = box.row()
                    row_icon.scale_y = 2.0
                    row_icon.label(text="", icon=icon)

                # Name and description
                box.label(text=entry["name"], icon='NONE')
                desc_row = box.row()
                desc_row.scale_y = 0.6
                desc_row.label(text=entry["description"])

                # Category tag
                tag_row = box.row()
                tag_row.scale_y = 0.5
                tag_row.label(text=entry["category"], icon='TAG')

                # Add button
                op = box.operator("model_library.add_model",
                                  text="Add to Scene", icon='ADD')
                op.model_id = entry["id"]

        layout.separator()

        # -- Generate previews button --
        if not previews_available:
            layout.separator()
            layout.label(text="No preview images found.", icon='ERROR')
            layout.operator("model_library.generate_previews",
                            text="Generate Previews", icon='RENDER_STILL')
        else:
            layout.separator()
            layout.operator("model_library.generate_previews",
                            text="Regenerate Previews", icon='FILE_REFRESH')


# -------------------------------------------------------------------
#  Registration
# -------------------------------------------------------------------

classes = (
    MODELLIB_PG_properties,
    MODELLIB_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.model_library = bpy.props.PointerProperty(type=MODELLIB_PG_properties)
    _ensure_preview_collection()


def unregister():
    _remove_preview_collection()
    del bpy.types.Scene.model_library
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
