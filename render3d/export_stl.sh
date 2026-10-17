#!/bin/bash
# Exporta las piezas en coordenadas de montaje (no de impresión) para los renders de Blender.
#   bash render3d/export_stl.sh && python3 render3d/scenes.py hero salon pared
# Necesita OpenSCAD y el módulo de Python de Blender (pip install bpy).
cd "$(dirname "$0")"; mkdir -p stl
for p in shell bottom placed_knob wall; do
  openscad -o "stl/$p.stl" -D "part=\"$p\"" ../caja/knobeast_caja.scad
done
