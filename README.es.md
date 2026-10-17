<p align="center">
  <img src="docs/img/logo.png" alt="knobeast" width="420">
</p>

<p align="center"><strong>Un mando de volumen físico para Sonos.</strong><br>
Gira para cambiar el volumen. Pulsa para pausar. Sin móvil, sin tablet, sin app.</p>

<p align="center">
  <a href="https://knobeast.com/">Web oficial</a> ·
  <a href="https://knobeast.com/#comprar">Cómpralo montado (149 €)</a> ·
  <a href="docs/guia-montaje.md">Móntatelo tú</a> ·
  <a href="README.md">English</a>
</p>

![knobeast sobre un aparador junto a un tocadiscos](docs/img/render_salon.jpg)

## ¿Qué es knobeast?

knobeast es una cajita con una **rueda grande** y una **pequeña pantalla** que controla el volumen de tus altavoces **Sonos** por la wifi de casa.

- **Gira** la rueda para cambiar el volumen, de 1 en 1.
- **Pulsa** para pausar o reanudar.
- **Mantén pulsado** para abrir el menú.
- **La pantalla** muestra la habitación, el volumen y lo que suena.

Es una forma **minimalista y física de controlar la música**, sin depender del móvil ni de una tablet. **Cualquiera de la familia** puede usarlo, también los niños, los abuelos o los invitados: nadie necesita la app, ni una cuenta, ni contraseñas.

## ¿Para quién es?

knobeast funciona con **cualquier sistema Sonos**. Donde más sentido tiene es en los montajes **sin un control de volumen a mano**:

| Tu equipo | Por qué te sirve knobeast |
|---|---|
| **Sonos Port + tocadiscos, CD u otras fuentes analógicas** | El Port no tiene botones de volumen. Cuando parte de tu equipo es analógico, knobeast le devuelve una rueda de verdad. |
| **Sonos Port + altavoces que no son Sonos** (Bang & Olufsen Beolab, Genelec, KEF, Dynaudio… o un amplificador) | Con la salida de línea del Port en *Variable*, knobeast se convierte en el mando de volumen de tus altavoces. |
| **Sonos Amp + altavoces de techo o empotrados** | Los altavoces empotrados no tienen controles. Pon un knobeast en la pared, junto al interruptor de la luz. |
| **Altavoces Sonos que ya tienes** | Un segundo punto de control en otra estancia, o simplemente un objeto bonito en tu casa. |

Puede controlar una habitación, varias a la vez o un grupo de Sonos. Se eligen en el propio mando.

<p align="center">
  <img src="docs/img/render_pared.jpg" alt="knobeast en la pared" width="32%">
  <img src="docs/img/render_detalle.jpg" alt="Detalle de la rueda y la pantalla" width="32%">
  <img src="docs/img/render_colores.jpg" alt="knobeast en muchos colores" width="32%">
</p>

## Funciones

- **Local y privado:** habla directamente con tus Sonos en tu red (UPnP/SOAP, puerto 1400). Sin nube, sin cuenta, sin telemetría.
- **Multihabitación:**
  - altavoces sueltos, varias habitaciones a la vez o un grupo de Sonos completo;
  - distingue por modelo los altavoces que se llaman igual;
  - detecta las salidas de línea fijas y no las toca.
- **Configuración fácil:**
  - al arrancar por primera vez, la pantalla muestra una red de configuración WPA2 con contraseña única de cada aparato y un código QR;
  - lo escaneas con el móvil o entras desde el ordenador, y eliges tu wifi.
- **Actualizaciones:**
  - esta edición comunidad no se conecta a ningún servidor: la actualizas tú cuando quieras, por USB o sin cables desde su página de ajustes;
  - si una versión nueva no arranca, vuelve sola a la anterior;
  - los montados de knobeast.com reciben actualizaciones automáticas firmadas.
  - También puedes montar tu propio servidor de actualizaciones firmadas (Ed25519, HTTPS, anti-rollback).
- **A tu gusto:**
  - volumen máximo;
  - paso de volumen de 1, 2, 3 o 5;
  - tiempos para atenuar y apagar la pantalla.
- **Seis idiomas:** español, inglés, francés, alemán, italiano y portugués.
- **Mesa o pared:**
  - sobre la mesa la caja queda inclinada 13°;
  - con el soporte de pared, que compensa esa inclinación, queda recta, sujeta con imanes;
  - el cable USB-C queda escondido por debajo.
- **Batería opcional:** funciona con cualquier cargador USB-C y puede llevar una LiPo interna.

![Pantallas](docs/img/screens_es.png)

## Cómo conseguirlo

| | |
|---|---|
| **Montado** | Listo para usar: montado, programado y probado, impreso en los colores que elijas, con el soporte de pared y actualizaciones automáticas. **149 €, IVA incluido**, en **[knobeast.com](https://knobeast.com/#comprar)**. |
| **Móntatelo tú** | Todo está en este repositorio. Las piezas son baratas y fáciles de encontrar. Sigue la **[guía de montaje](docs/guia-montaje.md)**. |

## Móntatelo tú: resumen

**Piezas**

- Raspberry Pi Pico 2 W;
- encoder rotativo KY-040;
- pantalla OLED SH1106 de 1,3" por I²C;
- opcional: cargador TP4056 USB-C, batería LiPo 802540 e interruptor KCD11;
- una caja impresa en 3D.

**Cableado**

![Cableado](docs/img/wiring_es.png)

**Caja:** en `caja/` está el diseño editable en OpenSCAD y los STL listos para imprimir:
- `knobeast_1_carcasa`;
- `knobeast_2_tapa_inferior`;
- `knobeast_3_pomo`;
- `knobeast_4_soporte_pared`.

PLA, capa de 0,2 mm, sin soportes.

![Medidas](docs/img/dimensions_es.png)

**Programa:** MicroPython. Se instala con `bash instalar_mac.sh` (macOS; usa `mpremote`, que también funciona en Linux y Windows). Graba MicroPython y copia `pico/`. Las novedades se publican aquí, en GitHub. Para actualizar, descarga la versión nueva y cópiala por USB o desde la página de ajustes del mando; mira [Actualizaciones](docs/guia-montaje.md#7-actualizaciones).

**[→ Guía de montaje completa](docs/guia-montaje.md)**

## Código abierto, y lo que puede llegar a ser

Hoy knobeast controla el volumen de Sonos. La rueda y la pantalla dan para mucho más, y las aportaciones son bienvenidas:
- emisoras y listas favoritas;
- escenas de Home Assistant;
- otros sistemas de audio multihabitación;
- diseños de caja nuevos;
- más idiomas.

Mira [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencias

| Parte | Licencia |
|---|---|
| Programa y scripts (`pico/`, `*.py`, `*.sh`, `render3d/`) | [GNU GPL v3.0](LICENSE) |
| Diseño de hardware (`caja/`, planos de cableado y medidas) | [CERN Open Hardware Licence v2 – Strongly Reciprocal](LICENSES/CERN-OHL-S-2.0.txt) |
| Documentación e imágenes (`docs/`, `README*`) | [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt) |
| Nombre y logo «knobeast» (`marca/`) | Marca, **no** incluida en las licencias anteriores: ver [TRADEMARK.md](TRADEMARK.md) |

Puedes fabricar, modificar, compartir e incluso vender aparatos basados en este proyecto con estas licencias. Solo te pedimos que no los llames «knobeast» ni uses su logo.

## Contacto

- Preguntas, empresas, prensa: **contact@knobeast.com**
- Fallos de seguridad: **security@knobeast.com**. Lee antes [SECURITY.md](SECURITY.md) y no abras una incidencia pública.
- Errores e ideas: [incidencias de GitHub](https://github.com/knobeast/knobeast/issues)

Los knobeast montados los vende en [knobeast.com](https://knobeast.com) DSM Beauty, S.L. (Málaga, España).

---

<sub>Sonos, Sonos Port y Sonos Amp son marcas de Sonos, Inc. Bang & Olufsen y Beolab son marcas de Bang & Olufsen A/S. Las demás marcas pertenecen a sus propietarios y se citan solo para indicar compatibilidad. knobeast es un proyecto independiente, no afiliado ni respaldado por Sonos ni por Bang & Olufsen.</sub>
