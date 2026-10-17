# Seguridad de Knobeast / Knobeast security

## Cómo reportar un fallo de seguridad

Escribe a **security@knobeast.com** (para todo lo demás: contact@knobeast.com) con una descripción, la versión (menú → Sistema → Información) y, si puedes, los pasos para reproducirlo. Por favor, no lo publiques hasta que haya una versión corregida.

- Acuse de recibo: en 5 días laborables.
- Primera valoración: en 15 días.
- Corrección: según gravedad. Los fallos que ya se estén explotando se comunican a ENISA según la Ley de Ciberresiliencia (Reglamento (UE) 2024/2847).

## Periodo de soporte

Cada knobeast vendido montado (edición oficial) recibe actualizaciones de seguridad automáticas durante **al menos 5 años** desde que se vende la última unidad de su modelo.

La **edición comunidad** de GitHub no se actualiza por internet. Los fallos de seguridad se corrigen publicando una versión nueva en GitHub, con su aviso de seguridad, y cada uno la instala a mano. La fecha concreta de fin de soporte se publica en https://knobeast.com/security.

## Cómo se protege el mando

- **Red de configuración:** usa WPA2 con una contraseña aleatoria y única por mando, mostrada en su pantalla y en una pegatina. Solo está activa mientras se configura y se apaga sola a los 15 minutos.
- **Actualizaciones:** van firmadas con Ed25519. El mando solo lleva la clave pública. Antes de instalar comprueba:
  - la firma;
  - el sha256 de cada archivo;
  - que no sea una versión más antigua que la instalada (anti-rollback).
- **Conexión:** HTTPS con el certificado del servidor verificado.
- **Si una versión falla:** el mando vuelve solo a la versión anterior.
- **Actualizaciones automáticas (edición oficial):** activadas por defecto, con una búsqueda diaria, y se pueden desactivar en Sistema. La edición comunidad no se conecta a ningún servidor.
- **Datos:** el mando no envía datos personales a ningún servidor. Solo descarga el manifiesto y los archivos de actualización. La contraseña de tu wifi se guarda únicamente en el mando, y **Sistema → Restablecer** la borra.
- **Componentes:** cada versión publica su lista de componentes, `sbom.cdx.json`, junto a los archivos.

## Report a vulnerability (English)

Email **security@knobeast.com** (anything else: contact@knobeast.com) with a description, the firmware version (menu → System → Info) and steps to reproduce. Please allow us to ship a fix before disclosure. Ready-made units (official edition) receive automatic security updates for at least 5 years after the last unit of a model is sold. The community edition on GitHub has no internet updates: security fixes are published here as new releases with a security advisory.
