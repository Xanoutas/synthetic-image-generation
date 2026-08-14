import bpy
import os

print("=== Eevee Render Test ===")
os.makedirs("/tmp/test_render", exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
bpy.ops.object.camera_add(location=(3, -3, 2))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0.8)
bpy.context.scene.camera = cam

bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.filepath = "/tmp/test_render/eevee_test.png"

print("Rendering with Eevee...")
bpy.ops.render.render(write_still=True)

print("Render complete!")
print(f"File exists: {os.path.exists('/tmp/test_render/eevee_test.png')}")
