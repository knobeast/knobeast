# Logo knobeast A8: Russo One, mayúsculas, cursiva 0.22, «O» rellena con ranura de pomo.
import math, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
# Russo One (SIL OFL): https://fonts.google.com/specimen/Russo+One — deja RussoOne-Regular.ttf en esta carpeta
FONT=os.path.join(HERE,'RussoOne-Regular.ttf'); SHEAR=0.22; WORD='KNOBEAST'; SLOT_W=0.27
class Flat(BasePen):
    def __init__(s,gs): super().__init__(gs); s.c=[]; s.cur=None
    def _moveTo(s,p): s.cur=[p]; s.c.append(s.cur)
    def _lineTo(s,p): s.cur.append(p)
    def _curveToOne(s,p1,p2,p3):
        p0=s.cur[-1]
        for i in range(1,13):
            t=i/12; a=(1-t)**3; b=3*(1-t)**2*t; c=3*(1-t)*t*t; d=t**3
            s.cur.append((a*p0[0]+b*p1[0]+c*p2[0]+d*p3[0], a*p0[1]+b*p1[1]+c*p2[1]+d*p3[1]))
    def _qCurveToOne(s,p1,p2):
        p0=s.cur[-1]
        for i in range(1,11):
            t=i/10; s.cur.append(((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]))
    def _closePath(s): pass
    def _endPath(s): pass
f=TTFont(FONT); gs=f.getGlyphSet(); cmap=f.getBestCmap(); hm=f['hmtx']
def glyph(ch, x0):
    p=Flat(gs); gs[cmap[ord(ch)]].draw(p); g=Polygon()
    for c in p.c:
        if len(c)>2: g=g.symmetric_difference(Polygon([(x+x0,y) for x,y in c]).buffer(0))
    return g
def build(word=WORD, shear=SHEAR):
    x=0; parts=[]; omark=None
    for i,ch in enumerate(word):
        g=glyph(ch,x)
        if ch=='O':
            outer=unary_union([Polygon(p.exterior) for p in (g.geoms if hasattr(g,'geoms') else [g])])
            cx,cy=outer.centroid.x,outer.centroid.y
            # grosor del trazo a la altura del centro
            hl=LineString([(outer.bounds[0]-1,cy),(outer.bounds[2]+1,cy)]).intersection(g)
            segs=list(hl.geoms) if hasattr(hl,'geoms') else [hl]; stroke=min(s.length for s in segs)
            a=math.radians(45); ray=LineString([(cx,cy),(cx+2000*math.cos(a),cy+2000*math.sin(a))])
            bx0,by0,bx1,by1=outer.bounds; R=min(bx1-bx0,by1-by0)/2
            w=R*SLOT_W
            slot=LineString([(cx+0.12*R*math.cos(a),cy+0.12*R*math.sin(a)),(cx+0.80*R*math.cos(a),cy+0.80*R*math.sin(a))]).buffer(w/2,quad_segs=12)
            g=outer.difference(slot); omark=g
        parts.append(g); x+=hm[cmap[ord(ch)]][0]+ (0)
    logo=unary_union(parts)
    sk=lambda G: affinity.skew(G,xs=math.degrees(math.atan(shear)),origin=(0,0))
    return sk(logo), sk(omark)
def polys(G): return list(G.geoms) if isinstance(G,MultiPolygon) else [G]
def svg_path(G, minx, maxy, k=1):
    d=[]
    for p in polys(G):
        for ring in [p.exterior]+list(p.interiors):
            pts=[((x-minx)*k,(maxy-y)*k) for x,y in ring.coords]
            d.append('M'+' L'.join('%.1f %.1f'%q for q in pts)+' Z')
    return ' '.join(d)
if __name__=='__main__':
    L,O=build(); minx,miny,maxx,maxy=L.bounds; W,H=maxx-minx,maxy-miny
    k=1000/W  # logo 1000 unidades de ancho
    open(os.path.join(HERE,'logo.svg'),'w').write(
      f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W*k:.0f} {H*k:.0f}"><path fill="currentColor" fill-rule="evenodd" d="{svg_path(L,minx,maxy,k)}"/></svg>')
    a,b,c,d=O.bounds; s=max(c-a,d-b)
    # marca (la O) centrada en un cuadrado
    pad=0; ox=(s-(c-a))/2; oy=(s-(d-b))/2
    open(os.path.join(HERE,'mark.svg'),'w').write(
      f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s:.0f} {s:.0f}"><path fill="currentColor" fill-rule="evenodd" transform="translate({ox:.1f} {oy:.1f})" d="{svg_path(O,a,d)}"/></svg>')
    # OpenSCAD: polígonos en mm para un ancho dado (se escala en el .scad)
    out=[]
    for p in polys(L):
        rings=[p.exterior]+list(p.interiors); pts=[]; paths=[]
        for r in rings:
            idx=list(range(len(pts),len(pts)+len(r.coords)-1)); pts+= [((x-minx)/W,(y-miny)/W) for x,y in list(r.coords)[:-1]]; paths.append(idx)
        out.append('polygon(points=%s, paths=%s);'%(json.dumps([[round(x,5),round(y,5)] for x,y in pts]),json.dumps(paths)))
    open(os.path.join(HERE,'..','caja','logo_knobeast.scad'),'w').write(
      '// Logo knobeast (Russo One cursiva, «O» de pomo). Ancho 1 x alto %.4f: usar scale(ancho).\nlogo_aspect = %.5f;\nmodule logo_knobeast_unit() {\n%s\n}\n'%(H/W,H/W,'\n'.join('    '+o for o in out)))
    print('logo', W, H, H/W)
