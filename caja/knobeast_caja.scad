// =====================================================================
//  KNOBEAST — caja v2: cuadrada y fina, pantalla arriba y pomo grande abajo
//  Raspberry Pi Pico 2 W · OLED 1,3" SH1106 · encoder KY-040 · (opcional) TP4056 USB-C + LiPo 802540
// ---------------------------------------------------------------------
//  · Sobre la mesa: la cara queda inclinada (theta).
//  · En la pared: la caja encaja en el soporte (una cuña con el ángulo contrario) y queda recta.
//  · USB-C escondido en la base: el conector se mete por debajo y se desliza hacia dentro.
//    Sin soporte, el cable sale por detrás por un canal; con soporte, entra en el soporte
//    y baja por detrás pegado a la pared (o se mete en la pared por el agujero).
//
//  Abrir en OpenSCAD (openscad.org). Cambia "part" y pulsa F6 (render) y F7 (exportar STL).
//  Piezas:  "shell"   carcasa            (imprimir con la cara sobre la cama)
//           "bottom"  tapa inferior      (plana, como sale)
//           "knob"    pomo Ø42           (imprimir con la cara de arriba sobre la cama)
//           "wall"    soporte de pared   (imprimir con la cara de la pared sobre la cama)
//           "assembly" / "on_wall" / "cutaway"   vistas
//  Medidas en mm.
// =====================================================================

part = "assembly";
$fn = 72;

// ---------- Cuerpo ----------
theta  = 13;             // inclinación de la cara sobre la mesa (grados)
W      = 86;             // fondo interior (Y, delante -> detrás)
L      = 88;             // ancho interior (X) — con W/cos(theta) la cara sale cuadrada
Hf     = 15;             // altura interior delante
Hb     = Hf + W * tan(theta);   // altura interior detrás (~34)
wall   = 2.4;
top_t  = 3.2;            // grosor de la cara
floor_t= 2.4;            // tapa inferior
r_out  = 8;              // radio de las esquinas
edge_c = 1.2;            // chaflán del borde de la cara

// ---------- Pomo y encoder KY-040 (abajo, centrado) ----------
knob_x = L / 2;
knob_s = 23;             // centro del eje, a lo largo de la cara desde el borde de abajo
enc_hole = 7.4;          // casquillo M7
knob_d = 42;  knob_h = 12;   // fino, para que no tape la pantalla al mirarlo de lado
knob_gap = 1.5;          // separación pomo-cara (el pulsador baja ~0,5 mm)
shaft  = "D";            // "D" eje con plano · "round" eje moleteado
knob_top = 2;            // grosor de la tapa del pomo sobre el eje
shaft_depth = knob_h - knob_top - 3.5;   // el eje no debe sobresalir más de 11,5 mm de la cara: córtalo
nut_recess = [15, 3.5];  // hueco para tuerca y arandela del encoder (Ø, alto)

// ---------- Pantalla OLED 1,3" (arriba, centrada) ----------
oled_w = 35.9;  oled_h = 33.9;
oled_cx = L / 2;
s_c   = W / cos(theta) - 19.5;   // centro del módulo, pegado al borde de arriba (~15 mm entre pomo y ventana)
win_w = 31;  win_h = 17;  win_off = 1.0;
frame_h = 4.0;
oled_hole_dx = 30.5;  oled_hole_dy = 28.5;   // ¡mide los tuyos!
oled_glass = 1.6;  oled_post_d = 4.6;  oled_pilot = 1.6;   // tornillos M2 x 5

// ---------- Raspberry Pi Pico 2 W (51 x 21), detrás a la izquierda ----------
pico_l = 51;  pico_w = 21;
pico_x = 8;   pico_y = 54;  pico_h = 3;
pico_holes = [[2, 4.8], [49, 4.8], [2, 16.2], [49, 16.2]];

// ---------- Batería LiPo 802540 (8 x 25 x 40), delante a la izquierda ----------
bat_l = 40;  bat_w = 25;  bat_t = 8;
bat_x = 10;  bat_y = 5;

// ---------- Cargador TP4056 USB-C (17 x 26) a la derecha, USB-C mirando hacia atrás ----------
chg_w = 17;  chg_l = 26;
usb_x = 68;                      // centro del conector
chg_x = usb_x - chg_w / 2;
chg_h = 1;                       // altura de la placa sobre la tapa
port_y = W - 34;                 // boca del conector USB-C
chg_y = port_y - chg_l;
usb_z = chg_h + 1.6 + 1.6;       // centro del conector sobre la tapa
plug_slot = [13.6, 32];          // hueco para el conector del cable (ancho, largo)
plug_top  = usb_z + 4.6;         // techo del hueco
cable_ch  = 5.6;                 // canal del cable hasta la trasera
hood_t    = 1.6;

// ---------- Interruptor KCD11 en la trasera (arriba cuando está en la pared) ----------
sw_x = 16;  sw_z = 22;
sw_cut = [8.8, 13.2];

// ---------- Rótulo opcional en la cara (vacío = sin rótulo) ----------
label = [];               // ejemplo: [["Sandrita", 4.5, 82]]  -> [texto, tamaño, posición a lo largo de la cara]
label_font = "DejaVu Sans:style=Bold";
label_depth= 0.6;

// ---------- Logo knobeast en el lateral izquierdo ----------
logo_on    = true;
logo_w     = 36;          // ancho (mm)
logo_y     = 9;           // desde el frente
logo_z     = 4.5;         // línea base sobre el fondo interior
logo_depth = 0.6;

// ---------- Tornillos de la tapa (M3) ----------
boss_d = 7.5;  boss_in = 4.2;  pilot_d = 2.6;

// ---------- Imanes Ø10 x 3 de neodimio (tapa y soporte, mismas posiciones) ----------
mag_d = 10.2;  mag_h = 3.2;
mag_pos = [[12, 42], [46, 45], [74, 12], [pico_x + 25.5, pico_y + 10.5]];

// ---------- Soporte de pared ----------
wall_min = 5;             // grosor en el extremo fino (arriba)
rim_t    = 2.4;           // borde que abraza la caja por abajo y los lados
rim_h    = 5;             // altura del borde
fit      = 0.3;           // holgura caja-soporte
wall_screw = 4.5;         // tornillos de pared Ø4 con cabeza Ø8 rebajada
wall_screws = [[24, 50], [46, 58]];   // posiciones (x, y de la caja)

// ---------------------------------------------------------------------
function ztop(y) = Hf + y * tan(theta);
nrm = [0, -sin(theta), cos(theta)];
module rrect(l, w, r) { translate([r, r]) offset(r = r) square([l - 2*r, w - 2*r]); }
module on_face() translate([0, 0, Hf]) rotate([theta, 0, 0]) children();
module profile_solid(pts, x0, len) translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(len) polygon(pts);

module body_at(extra, inset) intersection() {
    profile_solid([[-wall, -floor_t], [W + wall, -floor_t],
                   [W + wall, ztop(W + wall) + extra], [-wall, ztop(-wall) + extra]], -wall, L + 2*wall);
    translate([-wall, -wall, -floor_t - 1]) linear_extrude(200)
        offset(delta = -inset) rrect(L + 2*wall, W + 2*wall, r_out);
}
module outer_body() {
    t = top_t / cos(theta);
    hull() { body_at(t - edge_c, 0); body_at(t, edge_c); }
}
module cavity() intersection() {
    profile_solid([[0, -50], [W, -50], [W, ztop(W)], [0, ztop(0)]], 0, L);
    translate([0, 0, -60]) linear_extrude(260) rrect(L, W, r_out - wall);
}

boss_pos = [[boss_in, boss_in], [L - boss_in, boss_in], [boss_in, W - boss_in], [L - boss_in, W - boss_in]];

// --- logo knobeast (Russo One en cursiva con la «O» de pomo), en logo_knobeast.scad
include <logo_knobeast.scad>
module logo2d(width) scale(width) logo_knobeast_unit();

module shell() {
    difference() {
        union() {
            difference() { outer_body(); cavity(); }
            intersection() {
                cavity();
                for (p = boss_pos) translate([p[0], p[1], 0]) cylinder(d = boss_d, h = 100);
            }
            // marco de la pantalla
            on_face() translate([oled_cx, s_c, 0]) difference() {
                translate([0, 0, -frame_h / 2 + 0.3]) cube([oled_w + 0.6 + 3.2, oled_h + 0.6 + 3.2, frame_h], center = true);
                translate([0, 0, -frame_h / 2 - 0.5]) cube([oled_w + 0.6, oled_h + 0.6, frame_h + 1], center = true);
                translate([0, (oled_h + 2) / 2, -frame_h / 2 - 0.5]) cube([16, 4, frame_h + 1], center = true);
            }
            // pivotes de los tornillos de la pantalla
            on_face() translate([oled_cx, s_c, 0])
                for (sx = [-1, 1], sy = [-1, 1])
                    translate([sx * oled_hole_dx / 2, sy * oled_hole_dy / 2, -oled_glass])
                        cylinder(d = oled_post_d, h = oled_glass + 0.02);
        }
        for (p = boss_pos) translate([p[0], p[1], -1]) cylinder(d = pilot_d, h = 13);

        // ventana de la pantalla con chaflán
        on_face() translate([oled_cx, s_c - win_off, 0]) hull() {
            translate([0, 0, (top_t - 1.1) / 2 - 0.5]) cube([win_w, win_h, top_t - 1.1 + 1], center = true);
            translate([0, 0, top_t + 0.3]) cube([win_w + 2.6, win_h + 2.6, 0.2], center = true);
        }
        on_face() translate([oled_cx - 7.5, s_c - oled_h / 2 - 0.3, -0.01]) cube([15, 5.8, top_t - 1.4]);
        on_face() translate([oled_cx, s_c, 0])
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx * oled_hole_dx / 2, sy * oled_hole_dy / 2, -oled_glass - 0.5])
                    cylinder(d = oled_pilot, h = oled_glass + 0.5 + top_t - 0.8, $fn = 20);

        for (ln = label)
            on_face() translate([L / 2, ln[2], top_t - label_depth]) linear_extrude(label_depth + 1)
                text(ln[0], size = ln[1], font = label_font, halign = "center", valign = "center", spacing = 1.08);

        // encoder
        on_face() translate([knob_x, knob_s, -1]) cylinder(d = enc_hole, h = top_t + 2);

        // logo
        if (logo_on)
            translate([-wall + logo_depth, logo_y + logo_w, logo_z]) rotate([90, 0, -90])
                linear_extrude(logo_depth + 0.01) logo2d(logo_w);

        // salida del cable por la trasera (a ras del suelo)
        translate([usb_x - cable_ch / 2, W - 1, -floor_t - 0.01]) cube([cable_ch, wall + 2, usb_z + 2.8 + floor_t - cable_ch / 2]);
        translate([usb_x, W - 1, usb_z + 2.8 - cable_ch / 2]) rotate([-90, 0, 0]) cylinder(d = cable_ch, h = wall + 2);

        // interruptor en la trasera + rebaje interior
        translate([sw_x - sw_cut[0] / 2, W - 1, sw_z - sw_cut[1] / 2]) cube([sw_cut[0], wall + 2, sw_cut[1]]);
        translate([sw_x - 7.5, W - 0.01, sw_z - 9]) cube([15, wall - 1.6 + 0.01, 18]);
    }
}

module countersink() {
    translate([0, 0, -floor_t - 1]) cylinder(d = 3.4, h = floor_t + 2);
    translate([0, 0, -floor_t - 0.01]) cylinder(d1 = 6.6, d2 = 3.4, h = 1.6);
}

// túnel del USB-C: abierto por abajo, el conector entra desde abajo y se desliza hacia el cargador
module hood_outer() translate([usb_x - plug_slot[0] / 2 - hood_t, port_y - 0.01, 0])
    cube([plug_slot[0] + 2*hood_t, W - 0.3 - port_y, plug_top + hood_t]);
module hood_inner() {
    translate([usb_x - plug_slot[0] / 2, port_y - 0.5, -floor_t - 1]) cube([plug_slot[0], plug_slot[1] + 0.5, plug_top + floor_t + 1]);
    translate([usb_x - cable_ch / 2, port_y, -floor_t - 1]) cube([cable_ch, W - port_y + 5, usb_z + 2.8 + floor_t + 1]);
}

module bottom() {
    g = 0.4;
    difference() {
        union() {
            translate([0, 0, -floor_t]) linear_extrude(floor_t) offset(delta = -0.3) rrect(L, W, r_out - wall);
            for (h = pico_holes) translate([pico_x + h[0], pico_y + h[1], 0]) {
                cylinder(d = 4.5, h = pico_h);
                cylinder(d = 1.8, h = pico_h + 1.4, $fn = 24);
            }
            // cargador: apoyos, guías laterales y tope delantero (el conector empuja hacia delante)
            for (y = [chg_y + 3, chg_y + chg_l - 6]) translate([chg_x + 1, y, 0]) cube([chg_w - 2, 3, chg_h]);
            for (x = [chg_x - g - 1.6, chg_x + chg_w + g]) translate([x, chg_y + 4, 0]) cube([1.6, 14, chg_h + 3]);
            translate([chg_x + 2, chg_y - g - 1.6, 0]) cube([chg_w - 4, 1.6, chg_h + 3]);
            hood_outer();
            // bandeja de la batería
            difference() {
                translate([bat_x - g - 1.6, bat_y - g - 1.6, 0]) cube([bat_l + 2*g + 3.2, bat_w + 2*g + 3.2, 4]);
                translate([bat_x - g, bat_y - g, -1]) cube([bat_l + 2*g, bat_w + 2*g, 6]);
                translate([bat_x + bat_l - 1, bat_y + 8, -1]) cube([6, 10, 6]);
            }
            for (p = mag_pos) translate([p[0], p[1], 0]) cylinder(d = mag_d + 3.2, h = 2.2);
        }
        hood_inner();
        for (p = boss_pos) translate([p[0], p[1], 0]) countersink();
        for (p = [[12, 10], [L - 12, 10], [12, W - 10], [L - 6.5, W - 16]])
            translate([p[0], p[1], -floor_t - 0.01]) cylinder(d = 10.5, h = 0.5);
        for (p = mag_pos) translate([p[0], p[1], -floor_t - 0.01]) cylinder(d = mag_d, h = mag_h);
    }
}

module knob() {
    difference() {
        union() {
            cylinder(d = knob_d - 2, h = 1);
            translate([0, 0, 1]) cylinder(d = knob_d, h = knob_h - 2.5);
            translate([0, 0, knob_h - 1.5]) cylinder(d1 = knob_d, d2 = knob_d - 3, h = 1.5);
        }
        for (i = [0:59]) rotate(i * 6) translate([knob_d / 2 + 0.35, 0, 2.5])
            cylinder(d = 1.6, h = knob_h - 5.5, $fn = 12);
        translate([0, 0, -0.01]) cylinder(d = nut_recess[0], h = nut_recess[1]);
        translate([0, 0, nut_recess[1] - 0.02]) linear_extrude(shaft_depth + 0.02)
            if (shaft == "D") intersection() { circle(d = 6.15); translate([-3.2, -3.2]) square([6.4, 4.6 + 0.05]); }
            else circle(d = 5.9);
        translate([-1, 9, knob_h - 0.8]) linear_extrude(1) square([2, knob_d / 2 - 1.5 - 9 - 1.5]);
    }
}

// ---------- soporte de pared ----------
// Plano de la pared: paralelo a la cara, a wall_min por debajo del canto trasero inferior de la caja.
// Marco en ese plano: z hacia la caja; -y hacia abajo (el frente de la caja).
module on_wall_plane()
    translate([0, W + wall, -floor_t]) rotate([theta, 0, 0]) translate([0, 0, -wall_min]) children();
function wall_v(y) = (y - W - wall) * cos(theta);    // coordenada a lo largo de la pared de un punto del fondo

module wall_bracket() {
    e = wall + fit + rim_t;
    difference() {
        intersection() {
            translate([-e, -e, -100]) linear_extrude(100 - floor_t + rim_h)
                rrect(L + 2*e, W + wall + e, r_out + fit + rim_t);
            on_wall_plane() translate([-200, -200, 0]) cube([400, 400, 200]);
        }
        // hueco donde encaja la caja (abierto por arriba = trasera de la caja)
        translate([-wall - fit, -wall - fit, -floor_t]) linear_extrude(100)
            rrect(L + 2*wall + 2*fit, W + 2*wall + 2*fit + 20, r_out + fit);
        // imanes
        for (p = mag_pos) translate([p[0], p[1], -floor_t - mag_h + 0.01]) cylinder(d = mag_d, h = mag_h);
        // paso del cable: ventana bajo el túnel que atraviesa hasta la pared...
        hull() for (k = [0, 60]) translate(-nrm * k)
            translate([usb_x - 7, port_y + 3, -floor_t - 0.5]) cube([14, plug_slot[1] - 5, 1]);
        // ...y canal por detrás que baja hasta el borde inferior del soporte
        on_wall_plane() translate([usb_x - 3.5, -200, -1]) cube([7, 200 + wall_v(port_y + 18), 1 + 6]);
        // tornillos de pared, con la cabeza rebajada
        for (p = wall_screws) on_wall_plane() translate([p[0], wall_v(p[1]), -1]) {
            cylinder(d = wall_screw, h = 200);
            translate([0, 0, 6]) cylinder(d = 9, h = 200);
        }
    }
}

// ---------- fantasmas ----------
module ghost_pico() {
    translate([pico_x, pico_y, pico_h]) cube([pico_l, pico_w, 1]);
    translate([pico_x + 3, pico_y + 3, pico_h + 1]) cube([pico_l - 6, pico_w - 6, 3]);
    translate([pico_x - 1.3, pico_y + 7, pico_h + 1]) cube([5.3, 7.5, 2.7]);
    for (y = [pico_y + 1.6, pico_y + pico_w - 1.6]) translate([pico_x, y - 2, pico_h + 1]) cube([pico_l, 4, 7]);
}
module ghost_charger() {
    translate([chg_x, chg_y, chg_h]) cube([chg_w, chg_l, 1.6]);
    translate([usb_x - 4.5, port_y - 7.3, chg_h + 1.6]) cube([9, 7.3, 3.2]);
    translate([chg_x + 3, chg_y + 8, chg_h + 1.6]) cube([chg_w - 6, 8, 1.5]);
    translate([chg_x, chg_y, chg_h + 1.6]) cube([chg_w, 4, 3]);      // cables soldados
}
module ghost_plug(cable = true) {
    translate([usb_x - 4.2, port_y - 6.6, usb_z - 1.3]) cube([8.4, 6.6, 2.6]);
    translate([usb_x - 6, port_y, usb_z - 3.2]) cube([12, 20, 6.4]);
    if (cable) translate([usb_x, port_y + 20, usb_z]) rotate([-90, 0, 0]) cylinder(d = 4, h = W - port_y - 20 + 25);
}
module ghost_battery() translate([bat_x, bat_y, 0]) cube([bat_l, bat_w, bat_t]);
module ghost_switch() translate([sw_x - 7.5, W - 15, sw_z - 5]) cube([15, 15, 10]);
module ghost_oled() on_face() translate([oled_cx, s_c, 0]) {
    translate([0, 0, -1.6 / 2]) cube([oled_w - 1, 23, 1.6], center = true);
    translate([0, 0, -1.6 - 1.6 / 2]) cube([oled_w, oled_h, 1.6], center = true);
    translate([0, 0, -3.2 - 1]) cube([oled_w - 6, oled_h - 8, 2], center = true);
    translate([0, -oled_h / 2 + 2.5, -3.2 - 6]) cube([10.5, 2.6, 12], center = true);   // pines + cables
}
// KY-040 girado: los pines hacia la derecha
module ghost_encoder() on_face() translate([knob_x, knob_s, 0]) {
    translate([0, 0, top_t]) cylinder(d = 7, h = 7 - top_t);
    translate([0, 0, top_t]) cylinder(d = 11, h = 2, $fn = 6);
    translate([-6.2, -6.2, -6.5]) cube([12.4, 12.4, 6.5]);
    rotate(-90) {
        translate([-9.5, -20, -6.5 - 1.6]) cube([19, 32, 1.6]);
        translate([-6.5, 12, -6.5 - 1.6 - 2.6]) cube([13, 20, 2.6]);
    }
}
module placed_knob() on_face() translate([knob_x, knob_s, top_t + knob_gap]) knob();

module everything(cable = true) {
    color("white") shell();
    color("dimgray") bottom();
    color("green") ghost_pico();
    color("blue") ghost_charger();
    color("gold") ghost_battery();
    color("red") ghost_switch();
    color("deepskyblue") ghost_oled();
    color("orange") ghost_encoder();
    color("silver") placed_knob();
    color("black") ghost_plug(cable);
}

if (part == "shell")        shell();
else if (part == "bottom")  bottom();
else if (part == "knob")    knob();
else if (part == "wall")    wall_bracket();
else if (part == "placed_knob")   placed_knob();
else if (part == "ghost_oled")    ghost_oled();
else if (part == "ghost_encoder") ghost_encoder();
else if (part == "ghost_pico")    ghost_pico();
else if (part == "ghost_charger") ghost_charger();
else if (part == "ghost_battery") ghost_battery();
else if (part == "ghost_switch")  ghost_switch();
else if (part == "ghost_plug")    ghost_plug();
else if (part == "assembly") everything();
else if (part == "on_wall") { everything(); color("tan") wall_bracket(); }
else if (part == "wall_scene") rotate([90, 0, 0])
    translate([0, 0, wall_min]) rotate([-theta, 0, 0]) translate([0, -(W + wall), floor_t]) {
        everything(false); color("tan") wall_bracket();
        // el cable entra en el soporte y baja por detrás
        color("black") hull() for (k = [8, 14]) translate(-nrm * k + [usb_x, port_y + 22, usb_z]) sphere(d = 4);
        color("black") on_wall_plane() translate([usb_x, -150, 2.5]) rotate([-90, 0, 0])
            cylinder(d = 4, h = 150 + wall_v(port_y + 14));
        // la pared
        on_wall_plane() color("gainsboro") translate([-30, -150, -3]) cube([L + 60, 230, 3]);
    }
else if (part == "cutaway") difference() { everything(); translate([usb_x, -20, -60]) cube([L, W + 60, 160]); }
