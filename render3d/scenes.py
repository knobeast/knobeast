import sys, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib3d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out') + '/'
import os; os.makedirs(OUT, exist_ok=True)
Q = float(os.environ.get('Q', '1'))   # calidad: 1 = final, 0.25 = prueba

def R(w, h, s):
    k = 1400 / w if w > 1400 else 1.0
    if Q < 1: k *= 0.3
    sc = reset(int(w * k), int(h * k), 36 if Q >= 1 else 8)
    sc.cycles.adaptive_threshold = 0.02
    return sc

def studio(col='#ece7df', key=22, fill=6):
    m = mat_simple('sweep', col, 0.85)
    box('floor', (6, 6, 0.01), (0, 0, -0.005), m)
    box('back', (6, 0.01, 3), (0, 1.0, 1.5), m)
    area('key', (-0.5, -0.35, 0.7), (math.radians(50), 0, math.radians(-55)), 1.0, key)
    area('fill', (0.6, -0.3, 0.35), (math.radians(70), 0, math.radians(60)), 0.8, fill)
    area('top', (0, 0.2, 1.0), (0, 0, 0), 1.2, key * 0.4)

def turntable(x, y, rot=0):
    walnut = mat_wood('walnut', '#6b3f22', '#3b2010', 9)
    alu = mat_simple('alu', '#c9c9c9', 0.25, metal=1.0)
    vinyl = mat_simple('vinyl', '#0b0b0c', 0.18, spec=0.6)
    objs = [box('plinth', (0.43, 0.34, 0.07), (0, 0, 0.035), walnut, 0.006)]
    objs.append(cyl('platter', 0.152, 0.014, (-0.04, 0, 0.077), alu, 128))
    objs.append(cyl('record', 0.151, 0.002, (-0.04, 0, 0.085), vinyl, 128))
    objs.append(cyl('label', 0.05, 0.0022, (-0.04, 0, 0.0852), mat_simple('lbl', '#e85d2a', 0.6), 64))
    objs.append(cyl('spindle', 0.0035, 0.02, (-0.04, 0, 0.09), alu, 24))
    objs.append(cyl('pivot', 0.016, 0.03, (0.16, 0.11, 0.085), alu, 48))
    arm = cyl('arm', 0.004, 0.24, (0.11, 0.02, 0.1), alu, 24, rot=(math.radians(90), 0, math.radians(-25)))
    arm.rotation_euler = (math.radians(88), 0, math.radians(28)); objs.append(arm)
    objs.append(box('head', (0.02, 0.035, 0.008), (0.055, -0.085, 0.095), mat_simple('hs', '#202020', 0.4), 0.002))
    for fx, fy in ((-0.19, -0.14), (0.19, -0.14), (-0.19, 0.14), (0.19, 0.14)):
        pass
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    for o in objs: o.matrix_world = M @ o.matrix_world
    return objs

def speaker(x, y, h=0.34, col='#2b2b2d', rot=0):
    body = box('spk', (0.2, 0.24, h), (0, 0, h / 2), mat_wood('oak', '#b58a5a', '#8a6038', 7, 0.5), 0.004)
    m = bpy.data.materials.new('cloth'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(col); b.inputs['Roughness'].default_value = 0.95
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    grille = box('grille', (0.186, 0.004, h - 0.014), (0, -0.121, h / 2), m, 0.002)
    M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
    for o in (body, grille): o.matrix_world = M @ o.matrix_world

def sleeve(x, y, col, col2, lean=-9, rot=0, pattern='half'):
    m = bpy.data.materials.new('sl'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.55
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = srgb(col); ramp.color_ramp.elements[1].position = 0.5; ramp.color_ramp.elements[1].color = srgb(col2)
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z' if pattern == 'half' else 'X'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    o = box('sleeve', (0.315, 0.004, 0.315), (0, 0, 0.1575), m)
    o.matrix_world = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rot), 4, 'Z') @ Matrix.Rotation(math.radians(lean), 4, 'X') @ o.matrix_world

# ------------------------------------------------------------------ escenas
def hero():
    R(1800, 1000, 128); studio('#efe9e0')
    combos = [('blanco', 'naranja', 'salon', 0.0, 0.0, -18), ('negro', 'amarillo', 'cocina', -0.13, 0.07, -8),
              ('menta', 'blanco', 'estudio', 0.13, 0.06, -28), ('terracota', 'crema', 'salon', -0.25, 0.17, 0),
              ('azul', 'naranja', 'estudio', 0.25, 0.16, -36)]
    for sh, kn, sc, x, y, r in combos:
        place(unit(sh, kn, screen=sc), on_table(x, y, r))
    camera((0.0, -0.56, 0.2), (0.0, 0.07, 0.015), lens=38, fstop=4.0, focus=0.56)
    render(OUT + 'hero.png')

def salon():
    R(1800, 1100, 128)
    box('top', (1.6, 0.48, 0.03), (0, 0.04, -0.015), mat_wood('sideboard', '#9b6a3f', '#6e4524', 5))
    box('front', (1.6, 0.02, 0.7), (0, -0.19, -0.38), mat_simple('door', '#e8e1d5', 0.6))
    box('wall', (4, 0.02, 3), (0, 0.29, 1.2), mat_plaster('wallg', '#a9b59d'))
    box('floor', (4, 3, 0.01), (0, 0, -0.75), mat_wood('floor', '#c49a6c', '#9a7148', 3))
    turntable(-0.3, 0.09, 6)
    speaker(0.42, 0.13, 0.34, rot=-10)
    sleeve(-0.05, 0.25, '#f2c14e', '#1d3557', -10); sleeve(0.04, 0.24, '#e76f51', '#264653', -13, pattern='x')
    place(unit('blanco', 'naranja', screen='estudio'), on_table(0.12, -0.06, -18))
    area('window', (-1.4, -0.2, 0.9), (math.radians(80), 0, math.radians(-75)), 1.4, 260, (1, 0.93, 0.82), size_y=1.6)
    area('fill', (0.8, -1.0, 0.6), (math.radians(65), 0, math.radians(35)), 1.5, 40, (0.85, 0.9, 1.0))
    camera((0.22, -0.4, 0.15), (0.05, 0.04, 0.06), lens=32, fstop=3.5, focus=0.36)
    render(OUT + 'salon.png')

def pared():
    R(1300, 1600, 128)
    box('wall', (4, 0.02, 3), (0, 0.01, 1.5), mat_plaster('wallw', '#d9c8b4'))
    box('floor', (4, 3, 0.01), (0, -1.5, 0), mat_wood('floor', '#b48a5e', '#8a6038', 3))
    box('skirting', (4, 0.012, 0.08), (0, -0.006, 0.04), mat_simple('sk', '#f1ede6', 0.5))
    # interruptor de la luz genérico
    plate = mat_simple('plate', '#f3f1ec', 0.35)
    box('switch', (0.082, 0.01, 0.082), (-0.16, -0.005, 1.22), plate, 0.003)
    box('rocker', (0.05, 0.006, 0.05), (-0.16, -0.012, 1.22), plate, 0.004)
    # mueble bajo con una planta
    box('console', (0.9, 0.3, 0.04), (0.25, -0.17, 0.8), mat_wood('oak2', '#c19a6b', '#9a7148', 6))
    for lx in (-0.17, 0.67):
        box('leg', (0.03, 0.03, 0.8), (lx, -0.17, 0.4), mat_simple('blk', '#1e1e1e', 0.5))
    pot = cyl('pot', 0.07, 0.16, (0.5, -0.17, 0.9), mat_simple('pot', '#c0613f', 0.7), 64)
    for i in range(7):
        a = i * 0.9; leaf = cyl('stem', 0.003, 0.35, (0.5 + 0.04 * math.cos(a), -0.17 + 0.04 * math.sin(a), 1.12), mat_simple('st', '#4e7d5b', 0.6), 12,
                                 rot=(0.35 * math.cos(a), 0.35 * math.sin(a), 0))
    place(unit('negro', 'naranja', bracket='negro', screen='salon'), on_wall(0.02, 1.2))
    area('window', (-1.6, -1.4, 1.6), (math.radians(70), 0, math.radians(-50)), 1.6, 380, (1, 0.94, 0.85))
    area('fill', (1.2, -1.6, 1.4), (math.radians(70), 0, math.radians(40)), 1.4, 60, (0.88, 0.92, 1.0))
    camera((0.2, -0.46, 1.1), (-0.03, 0, 1.17), lens=45, fstop=5.6, focus=0.5)
    render(OUT + 'pared.png')

def pared_lado():
    R(1500, 1000, 128)
    box('wall', (4, 0.02, 3), (0, 0.01, 1.5), mat_plaster('wallb', '#2f3e46'))
    place(unit('blanco', 'amarillo', bracket='blanco', screen='cocina'), on_wall(0.0, 1.2))
    area('key', (-0.6, -0.7, 1.6), (math.radians(55), 0, math.radians(-40)), 0.8, 120)
    area('fill', (0.8, -0.8, 1.1), (math.radians(80), 0, math.radians(55)), 0.8, 25)
    camera((0.34, -0.48, 1.26), (0.0, -0.03, 1.19), lens=60, fstop=5.6, focus=0.58)
    render(OUT + 'pared_lado.png')

def colores():
    R(1800, 1100, 112)
    box('floor', (4, 4, 0.01), (0, 0, -0.005), mat_simple('bg', '#f3e9dc', 0.9))
    area('key', (-0.4, -0.5, 1.2), (math.radians(30), 0, math.radians(-35)), 1.4, 70)
    area('fill', (0.5, 0.3, 0.9), (math.radians(-25), 0, math.radians(140)), 1.0, 20)
    combos = [('rojo', 'blanco'), ('menta', 'blanco'), ('lila', 'morado'), ('amarillo', 'negro'),
              ('celeste', 'azul'), ('crema', 'terracota'), ('negro', 'naranja'), ('rosa', 'rojo')]
    for i, (sh, kn) in enumerate(combos):
        x = (i % 4 - 1.5) * 0.15; y = (0.5 - i // 4) * 0.16
        place(unit(sh, kn, screen=('salon', 'cocina', 'estudio')[i % 3]), on_table(x, y, 0))
    camera((0.0, -0.38, 0.72), (0.0, 0.02, 0.0), lens=50)
    render(OUT + 'colores.png')

def detalle():
    R(1600, 1000, 128); studio('#e9e2d8', 18, 5)
    place(unit('crema', 'terracota', screen='estudio'), on_table(0, 0, -10))
    camera((0.1, -0.24, 0.16), (0.0, 0.0, 0.03), lens=85, fstop=5.6, focus=0.27)
    render(OUT + 'detalle.png')

if __name__ == '__main__':
    for n in sys.argv[1:]:
        globals()[n]()
