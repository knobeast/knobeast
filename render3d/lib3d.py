# Utilidades Blender para los renders de knobeast.com
import bpy, math, mathutils, os
HERE = os.path.dirname(os.path.abspath(__file__))
from mathutils import Matrix, Vector

STL = os.path.join(HERE, 'stl') + '/'      # piezas exportadas con export_stl.sh
SCR = os.path.join(HERE, 'screens') + '/'  # imágenes de la pantalla (128x64)
TH = math.radians(13); HF = 15.0; W = 86.0; WALL = 2.4; FLOOR_T = 2.4; WALL_MIN = 5.0
S_WIN = W / math.cos(TH) - 19.5 - 1.0     # centro de la ventana a lo largo de la cara
MM = 0.001

PLA = {  # colores de PLA habituales (aprox. sRGB)
    'blanco': '#EDEBE6', 'crema': '#E8DDC4', 'negro': '#232325', 'gris': '#8C8F93',
    'naranja': '#FF6A1F', 'amarillo': '#F6C423', 'rojo': '#D2302C', 'menta': '#9FD8C0',
    'verde': '#4E7D5B', 'azul': '#22417A', 'celeste': '#86B9E0', 'lila': '#B9A6DB',
    'rosa': '#F2B6C4', 'terracota': '#C0613F', 'morado': '#5B3A86', 'oliva': '#7A7A45',
}

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, 1.0)

def reset(w=1600, h=1000, samples=96):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'
    s.cycles.samples = samples; s.cycles.use_denoising = True
    s.render.resolution_x = w; s.render.resolution_y = h; s.render.resolution_percentage = 100
    s.view_settings.view_transform = 'Khronos PBR Neutral'
    s.render.film_transparent = False
    s.cycles.max_bounces = 6; s.cycles.glossy_bounces = 3; s.cycles.transmission_bounces = 4
    w_ = bpy.data.worlds.new('w'); s.world = w_; w_.use_nodes = True
    bg = w_.node_tree.nodes['Background']; bg.inputs[0].default_value = srgb('#d9d4cc'); bg.inputs[1].default_value = 0.25
    return s

def mat_pla(name, hexcol, rough=0.42, layer_dir=(0, -math.sin(TH), math.cos(TH)), layers=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N['Principled BSDF']; b.inputs['Base Color'].default_value = srgb(hexcol)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = 0.45
    b.inputs['Subsurface Weight'].default_value = 0.04
    b.inputs['Subsurface Radius'].default_value = (0.002, 0.002, 0.002)
    if layers:   # líneas de capa de 0,2 mm, muy sutiles
        tc = N.new('ShaderNodeTexCoord'); dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'
        dp.inputs[1].default_value = layer_dir
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / 0.0002
        sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'
        bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12; bump.inputs['Distance'].default_value = 0.00002
        Lk.new(tc.outputs['Object'], dp.inputs[0]); Lk.new(dp.outputs['Value'], mul.inputs[0])
        Lk.new(mul.outputs[0], sn.inputs[0]); Lk.new(sn.outputs[0], bump.inputs['Height'])
        Lk.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_simple(name, hexcol, rough=0.5, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(hexcol); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Specular IOR Level'].default_value = spec
    return m

def mat_wood(name, base='#7a4b2a', dark='#4a2a15', scale=6.0, rough=0.45):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.25, 1, 1)
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    wv.inputs['Scale'].default_value = scale * 6; wv.inputs['Distortion'].default_value = 3; wv.inputs['Detail'].default_value = 4
    wv.inputs['Detail Scale'].default_value = 1.5
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = srgb(dark); ramp.color_ramp.elements[1].color = srgb(base)
    ramp.color_ramp.elements[0].position = 0.15; ramp.color_ramp.elements[1].position = 0.75
    L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], wv.inputs['Vector'])
    L.new(wv.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.05
    L.new(nz.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_plaster(name, hexcol, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Base Color'].default_value = srgb(hexcol); b.inputs['Roughness'].default_value = rough
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 400; nz.inputs['Detail'].default_value = 8
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08; bump.inputs['Distance'].default_value = 0.0005
    L.new(nz.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_screen(img_path):
    m = bpy.data.materials.new('screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    N.remove(N['Principled BSDF']); out = N['Material Output']
    tex = N.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(img_path); tex.interpolation = 'Closest'
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.85, 0.95, 1.0, 1)
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2.2
    L.new(tex.outputs['Color'], mul.inputs[0]); L.new(mul.outputs[0], em.inputs['Strength'])
    gl = N.new('ShaderNodeBsdfPrincipled'); gl.inputs['Base Color'].default_value = (0.002, 0.002, 0.003, 1); gl.inputs['Roughness'].default_value = 0.05
    add = N.new('ShaderNodeAddShader'); L.new(em.outputs[0], add.inputs[0]); L.new(gl.outputs[0], add.inputs[1])
    L.new(add.outputs[0], out.inputs['Surface'])
    return m

def import_stl(name):
    bpy.ops.wm.stl_import(filepath=STL + name + '.stl', global_scale=MM)
    o = bpy.context.selected_objects[0]
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return o

def face_pt(x, s, z):  # coordenadas de la cara -> caja (mm)
    return Vector((x, s * math.cos(TH) - z * math.sin(TH), HF + s * math.sin(TH) + z * math.cos(TH)))

def screen_plane(img, cx=44.0):
    w, h = 29.4, 14.7
    vs = [face_pt(cx + dx * w / 2, S_WIN + dy * h / 2, 0.08) * MM for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    me = bpy.data.meshes.new('scr'); me.from_pydata(vs, [], [(0, 1, 2, 3)]); me.update()
    uv = me.uv_layers.new();
    for i, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[i].uv = (u, v)
    o = bpy.data.objects.new('scr', me); bpy.context.collection.objects.link(o); o.data.materials.append(mat_screen(img))
    # cristal negro alrededor de la zona activa
    w2, h2 = 31, 17
    vs = [face_pt(cx + dx * w2 / 2, S_WIN + dy * h2 / 2, 0.03) * MM for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    me = bpy.data.meshes.new('glass'); me.from_pydata(vs, [], [(0, 1, 2, 3)]); me.update()
    g = bpy.data.objects.new('glass', me); bpy.context.collection.objects.link(g)
    g.data.materials.append(mat_simple('glassblk', '#050506', 0.06, spec=0.7))
    return [o, g]

def unit(shell='blanco', knob='naranja', bottom=None, bracket=None, screen='salon', logo_col=None):
    """Un knobeast completo en coordenadas de la caja (mm -> m). Devuelve la lista de objetos."""
    objs = []
    for part, col, ld in (('shell', shell, None), ('bottom', bottom or shell, (0, 0, 1)), ('placed_knob', knob, None)):
        o = import_stl(part); o.data.materials.append(mat_pla(part + col, PLA.get(col, col), layer_dir=ld or (0, -math.sin(TH), math.cos(TH)))); objs.append(o)
    if bracket:
        o = import_stl('wall'); o.data.materials.append(mat_pla('br' + bracket, PLA.get(bracket, bracket), layer_dir=(0, -math.sin(TH), math.cos(TH)))); objs.append(o)
    objs += screen_plane(SCR + 'scr_%s.png' % screen)
    return objs

def place(objs, M):
    for o in objs:
        o.matrix_world = M @ o.matrix_world

def on_table(x=0, y=0, rot_deg=0):
    # base de la caja (patas) a z=0; centro de la caja en (x, y)
    return Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rot_deg), 4, 'Z') @ \
        Matrix.Translation((-44 * MM, -43 * MM, (FLOOR_T + 0.5) * MM))

def on_wall(x=0, z=1.2, wall_y=0):
    # pared = plano y = wall_y, el mando hacia -y, "arriba" = +z
    A = Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation((0, 0, WALL_MIN * MM)) @ \
        Matrix.Rotation(-TH, 4, 'X') @ Matrix.Translation((0, -(W + WALL) * MM, FLOOR_T * MM))
    return Matrix.Translation((x - 44 * MM, wall_y, z)) @ A

def box(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = o.modifiers.new('bv', 'BEVEL'); md.width = bevel; md.segments = 3
    o.data.materials.append(mat); return o

def cyl(name, r, h, loc, mat, verts=96, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat); bpy.ops.object.shade_auto_smooth(angle=math.radians(40)); return o

def area(name, loc, rot, size, power, color=(1, 0.96, 0.9), shape='RECTANGLE', size_y=None):
    bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot); l = bpy.context.object; l.name = name
    l.data.shape = shape; l.data.size = size; l.data.energy = power; l.data.color = color
    if size_y: l.data.size_y = size_y
    return l

def camera(loc, look, lens=60, fstop=None, focus=None):
    bpy.ops.object.camera_add(location=loc); c = bpy.context.object
    d = Vector(look) - Vector(loc); c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    c.data.lens = lens; bpy.context.scene.camera = c
    if fstop:
        c.data.dof.use_dof = True; c.data.dof.aperture_fstop = fstop
        c.data.dof.focus_distance = focus if focus else d.length
    return c

def render(path):
    s = bpy.context.scene; s.render.filepath = path; s.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
