# Prototype: phone-first bowling throw

Este es el prototipo de **#15**: valida el esquema de tiro con el celular Android
antes de meter el juego completo. No es la consola final.

## Qué hace

- Sirve una PWA de controlador desde `controller-web/`.
- Levanta un servidor HTTP/WebSocket en `127.0.0.1:8443`.
- Muestra un QR y una escena 3D mínima: una paleta que se inclina con el teléfono.
- Mantenés **THROW**, hacés el swing y al soltar calcula velocidad, dirección y efecto.
- Graba las muestras crudas en `~/.local/share/toxinator/traces/phone-*.jsonl`.

## Probar con Android por USB (recomendado para el primer intento)

Requisitos: `adb` con el teléfono autorizado, Chrome Android, `uv`.

```bash
uv sync
adb reverse tcp:8443 tcp:8443
uv run toxinator dev phone
```

1. Escaneá el QR de la ventana, o abrí la URL que imprime la consola.
2. Tocá **Empezar** y aceptá el permiso de movimiento si aparece.
3. Mové el teléfono: la paleta debería inclinarse.
4. Mantené **THROW**, hacé el swing y soltá. La consola muestra `speed`, `spin` y `conf`.

`localhost` es un contexto seguro, así que los sensores funcionan por `adb reverse`
sin certificados.

## Probar por LAN (HTTPS, sin adb)

Los sensores necesitan un contexto seguro. Servir por `http://192.168.x.x` no alcanza.
El camino recomendado es un CA local con `mkcert`, instalado una vez en Android.

1. Averiguá la IP LAN de la PC:

```bash
ip -4 -o addr show scope global
```

2. Generá el certificado para esa IP (reemplazá `192.168.0.141`):

```bash
mkdir -p ~/.config/toxinator/certs
mkcert \
  -cert-file ~/.config/toxinator/certs/cert.pem \
  -key-file ~/.config/toxinator/certs/key.pem \
  192.168.0.141 localhost 127.0.0.1
cp "$(mkcert -CAROOT)/rootCA.pem" ~/.config/toxinator/certs/toxinator-ca.crt
```

3. Pasá **solo** el CA al teléfono e instalalo como certificado de CA. Una forma
   simple es servirlo por HTTP temporalmente:

```bash
mkdir -p /tmp/toxinator-ca-share
cp ~/.config/toxinator/certs/toxinator-ca.crt /tmp/toxinator-ca-share/
cd /tmp/toxinator-ca-share
python3 -m http.server 8000 --bind 0.0.0.0
```

En el teléfono abrí `http://192.168.0.141:8000/toxinator-ca.crt`, descargalo e
instalalo desde **Ajustes → Seguridad → Instalar un certificado → Certificado de CA**.
El CA es público; la clave privada nunca se sirve. Pará el servidor HTTP después.

4. Abrí los puertos en el firewall (si UFW está activo):

```bash
sudo ufw allow from 192.168.0.0/24 to any port 8443 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 8000 proto tcp
```

5. Arrancá el prototipo con TLS:

```bash
uv run toxinator dev phone \
  --host 0.0.0.0 \
  --port 8443 \
  --url https://192.168.0.141:8443 \
  --tls-cert ~/.config/toxinator/certs/cert.pem \
  --tls-key ~/.config/toxinator/certs/key.pem
```

6. Escaneá el QR desde el teléfono. Chrome debería aceptar el certificado sin
   advertencia; los sensores funcionan porque el origen es HTTPS.

Si la IP cambia, regenerá el certificado con la IP nueva. Si Chrome sigue
mostrando advertencia, el CA no quedó instalado como CA de usuario; no sigas
haciendo click en “continuar”, porque el contexto seguro no es confiable.

## Qué mirar

- ¿La paleta sigue el tilt sin saltos?
- ¿La dirección del `throw` coincide con el swing?
- ¿La potencia distingue un swing suave de uno fuerte?
- ¿El efecto (`spin`) tiene sentido o está dominado por ruido?
- ¿Hay latencia noticeable entre el movimiento y la paleta?

Anotá 10–20 tiros con cada variante y adjuntá el `.jsonl` o un clip al ticket #15.

## Limitaciones

- Todavía no hay adaptador de Wiimote; el primer corte es phone-only.
- El token es una protección mínima, no autenticación fuerte.
- No hay TLS automático ni PWA instalable completa.
- El detector de `throw` es deliberadamente simple; los umbrales se ajustan después.
