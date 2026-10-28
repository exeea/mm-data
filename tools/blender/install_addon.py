"""Install the packaged add-on using Blender's own preferences operators.

Run Blender --background --python tools/blender/install_addon.py (not --factory-startup,
which would replace the user's existing preferences with defaults).
"""
from pathlib import Path
import bpy

HERE = Path(__file__).resolve().parent
bpy.ops.preferences.addon_install(filepath=str(HERE / 'mm_materials.zip'))
bpy.ops.preferences.addon_enable(module='mm_materials')
bpy.context.preferences.addons['mm_materials'].preferences.root = str(HERE.parents[1])
bpy.ops.wm.save_userpref()
print('INSTALLED', bpy.utils.user_resource('SCRIPTS', path='addons/mm_materials'))
