import bpy
import random
import os
import json
import math
import mathutils

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/tmp/renders')
SCENE_COUNT = int(os.environ.get('SCENE_COUNT', '10'))
RES_X = int(os.environ.get('RES_X', '1024'))
RES_Y = int(os.environ.get('RES_Y', '768'))

os.makedirs(f"{OUTPUT_DIR}/images", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/annotations", exist_ok=True)

DEFECT_TYPES = ['scratch', 'dent', 'crack', 'corrosion', 'discoloration']

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for curve in bpy.data.curves:
        bpy.data.curves.remove(curve)

def create_metal_plate():
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plate = bpy.context.active_object
    plate.name = "MetalPlate"
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=32)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    mat = bpy.data.materials.new(name="MetalMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.3, 0.3, 0.35, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.95
    bsdf.inputs['Roughness'].default_value = random.uniform(0.2, 0.5)
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    plate.data.materials.append(mat)
    return plate

def add_scratch(plate):
    bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0.001))
    scratch = bpy.context.active_object
    scratch.name = "Defect_scratch"
    for spline in scratch.data.splines:
        for point in spline.bezier_points:
            # Blender 4.2: co is 3D (x, y, z) - NOT 4D!
            x = random.uniform(-0.8, 0.8)
            y = random.uniform(-0.8, 0.8)
            z = 0.001
            point.co = (x, y, z)
            point.handle_left = (x - 0.1, y, z)
            point.handle_right = (x + 0.1, y, z)
    scratch.data.bevel_depth = random.uniform(0.0005, 0.003)
    scratch.data.bevel_resolution = 2
    scratch.rotation_euler = (0, 0, random.uniform(0, 6.28))
    mat = bpy.data.materials.new(name="ScratchMat")
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1.0)
    scratch.data.materials.append(mat)
    return scratch

def add_dent(plate):
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    dent_center = (random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 0)
    radius = random.uniform(0.05, 0.15)
    depth = random.uniform(-0.02, -0.05)
    for v in plate.data.vertices:
        dist = math.sqrt((v.co[0]-dent_center[0])**2 + (v.co[1]-dent_center[1])**2)
        if dist < radius:
            v.co[2] += depth * (1 - dist/radius)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    plate.name = "Defect_dent"
    return plate

def add_crack(plate):
    start = (random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7), 0.001)
    for i in range(random.randint(3, 6)):
        bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.005, 0.015), location=start)
        cube = bpy.context.active_object
        cube.name = f"Defect_crack_{i}"
        cube.scale = (random.uniform(2, 5), 0.3, 0.1)
        cube.rotation_euler = (0, 0, random.uniform(0, 6.28))
        start = (start[0] + random.uniform(-0.05, 0.05), start[1] + random.uniform(-0.05, 0.05), 0.001)
    return plate

def setup_camera():
    bpy.ops.object.camera_add(location=(0, 0, 1.5))
    cam = bpy.context.active_object
    cam.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = cam
    return cam

def setup_lighting():
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.light_add(type='AREA', location=(random.uniform(-2, 2), random.uniform(-2, 2), 2.5))
    key = bpy.context.active_object
    key.data.energy = random.uniform(50, 200)
    key.data.size = random.uniform(1, 3)
    bpy.ops.object.light_add(type='AREA', location=(random.uniform(-1, 1), -2, 1.5))
    fill = bpy.context.active_object
    fill.data.energy = random.uniform(20, 80)
    return key, fill

def get_bbox_yolo(obj, cam):
    import bpy_extras
    scene = bpy.context.scene
    corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    coords_2d = []
    for corner in corners:
        co_2d = bpy_extras.object_utils.world_to_camera_view(scene, cam, corner)
        coords_2d.append((co_2d.x, co_2d.y))
    xs = [c[0] for c in coords_2d]
    ys = [c[1] for c in coords_2d]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    width = x_max - x_min
    height = y_max - y_min
    return [x_center, y_center, width, height]

def render_scene(idx, defect_type):
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    img_path = f"{OUTPUT_DIR}/images/defect_{idx:05d}.png"
    ann_path = f"{OUTPUT_DIR}/annotations/defect_{idx:05d}.json"
    scene.render.filepath = img_path
    scene.render.image_settings.file_format = 'PNG'
    
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    eevee = scene.eevee
    eevee.taa_render_samples = 16
    eevee.use_raytracing = True
    
    bpy.ops.render.render(write_still=True)
    
    cam = bpy.data.objects['Camera']
    annotations = {'image_id': idx, 'defect_type': defect_type, 'objects': []}
    for obj in bpy.data.objects:
        if obj.name.startswith('Defect_'):
            bbox = get_bbox_yolo(obj, cam)
            annotations['objects'].append({
                'class': defect_type,
                'bbox_yolo': bbox,
                'bbox_coco': [bbox[0]-bbox[2]/2, bbox[1]-bbox[3]/2, bbox[2], bbox[3]]
            })
    with open(ann_path, 'w') as f:
        json.dump(annotations, f, indent=2)
    print(f"Rendered: {img_path}")

print(f"Starting generation of {SCENE_COUNT} images using Eevee...")
print(f"Output: {OUTPUT_DIR}")

for i in range(SCENE_COUNT):
    clear_scene()
    plate = create_metal_plate()
    defect_type = random.choice(DEFECT_TYPES)
    
    if defect_type == 'scratch':
        add_scratch(plate)
    elif defect_type == 'dent':
        add_dent(plate)
    elif defect_type == 'crack':
        add_crack(plate)
    elif defect_type == 'corrosion':
        mat = plate.data.materials[0]
        nodes = mat.node_tree.nodes
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = random.uniform(20, 50)
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.color_ramp.elements[0].color = (0.3, 0.2, 0.1, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.6, 0.5, 0.3, 1.0)
        mat.node_tree.links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
        bsdf = nodes['Principled BSDF']
        mat.node_tree.links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
        plate.name = "Defect_corrosion"
    elif defect_type == 'discoloration':
        mat = plate.data.materials[0]
        bsdf = mat.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = (random.uniform(0.4, 0.8), random.uniform(0.1, 0.3), random.uniform(0.1, 0.3), 1.0)
        plate.name = "Defect_discoloration"
    
    setup_camera()
    setup_lighting()
    cam = bpy.data.objects['Camera']
    cam.location = (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(1.2, 2.0))
    cam.rotation_euler = (random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), random.uniform(-0.1, 0.1))
    render_scene(i, defect_type)
    
    if i % 100 == 0 and i > 0:
        print(f"Progress: {i}/{SCENE_COUNT}")

print(f"\nDone! Generated {SCENE_COUNT} images in {OUTPUT_DIR}")
