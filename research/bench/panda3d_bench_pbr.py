"""1080p PBR benchmark for Panda3D + panda3d-simplepbr.

Loads a glTF/GLB model, frames it automatically, renders it offscreen at
1920x1080 with PBR, IBL, a 2048x2048 shadow map and tonemapping, and reports
GPU-complete frame time (glFinish after every frame).

Usage:
    uv run python research/bench/panda3d_bench_pbr.py --glb /path/to/model.glb

A good free test asset is Khronos' DamagedHelmet:
    curl -L -o /tmp/DamagedHelmet.glb \
      https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/DamagedHelmet/glTF-Binary/DamagedHelmet.glb

Measured on the ticket machine (Iris Xe, Mesa 26.2.5, panda3d 1.10.16,
simplepbr 0.13.1): 102-107 fps (9.4-9.8 ms/frame) with the helmet.
"""
import argparse
import ctypes
import math
import os
import sys

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Vec4,
    loadPrcFileData,
)

ap = argparse.ArgumentParser()
ap.add_argument("--glb", default=os.environ.get("GLB"),
                help="path to a .glb/.gltf model (or set GLB=...)")
ap.add_argument("--frames", type=int, default=150)
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
args = ap.parse_args()
if not args.glb or not os.path.exists(args.glb):
    raise SystemExit("Pass --glb /path/to/model.glb (or GLB=...)")

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", f"win-size {args.width} {args.height}")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "sync-video false")
loadPrcFileData("", "threading-model")
loadPrcFileData("", "notify-level-glgsg error")

from direct.showbase.ShowBase import ShowBase  # noqa: E402
import simplepbr  # noqa: E402

gl = ctypes.CDLL("libGL.so.1")  # for glFinish()

base = ShowBase(windowType="offscreen")
base.disableMouse()
simplepbr.init(enable_shadows=True, use_330=True, max_lights=4)

model = base.loader.loadModel(args.glb)
model.reparentTo(base.render)

# Frame the model from its bounding sphere.
lo, hi = model.getTightBounds()
center = (lo + hi) / 2
radius = max((hi - lo).length() / 2, 1e-3)
distance = radius * 3.2
base.cam.setPos(center + Vec4(0, -distance, radius * 0.35, 0).getXyz())
base.cam.lookAt(center)

amb = AmbientLight("amb")
amb.setColor(Vec4(0.5, 0.5, 0.6, 1))
base.render.setLight(base.render.attachNewNode(amb))
sun = DirectionalLight("sun")
sun.setColor(Vec4(2.2, 2.1, 2.0, 1))
sun_np = base.render.attachNewNode(sun)
sun_np.setHpr(40, -25, 0)
base.render.setLight(sun_np)
sun.setShadowCaster(True, 2048, 2048)

gsg = base.win.getGsg()
print(f"python {sys.version.split()[0]} | panda3d {__import__('panda3d').__version__}")
print(f"renderer: {gsg.getDriverRenderer()} | GL {gsg.getDriverVersion()}")
print(f"model: {args.glb} | bounds {lo} .. {hi}")
print(f"size: {base.win.getXSize()}x{base.win.getYSize()}")

# Warm-up frame (compiles PBR shaders, uploads textures).
base.taskMgr.step()
base.graphicsEngine.renderFrame()
base.graphicsEngine.syncFrame()
gl.glFinish()

import time  # noqa: E402

t0 = time.perf_counter()
for _ in range(args.frames):
    model.setH(model.getH() + 1.0)
    base.graphicsEngine.renderFrame()
    base.graphicsEngine.syncFrame()
    gl.glFinish()
elapsed = time.perf_counter() - t0

print(f"GPU-complete: {args.frames / elapsed:.1f} fps "
      f"({elapsed * 1000 / args.frames:.2f} ms/frame)")

# Save a frame so the result can be checked visually.
out = os.environ.get("SHOT", "/tmp/panda3d_pbr_frame.png")
base.win.saveScreenshot(out)
print(f"screenshot: {out}")
base.destroy()
