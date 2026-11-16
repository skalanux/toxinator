"""1080p offscreen benchmark for Panda3D on Linux.

Renders N lit cubes (one Geom/draw call each, unless --flatten) at 1920x1080,
optionally with a 2048x2048 shadow map, and reports GPU-complete frame time
(glFinish after every frame).

Examples:
    uv run python research/bench/panda3d_bench_1080p.py --cubes 300
    uv run python research/bench/panda3d_bench_1080p.py --cubes 2000 --shadow
    uv run python research/bench/panda3d_bench_1080p.py --cubes 2000 --shadow --flatten

Measured on the ticket machine (i5-11320H, Iris Xe, Mesa 26.2.5, Python 3.14.10,
panda3d 1.10.16):
    300 cubes, no shadow .......... 427-446 fps (2.24-2.34 ms)
    300 cubes, 2048 shadow map .... 233-236 fps (4.24-4.29 ms)
    2000 cubes, 2048 shadow map ... 111-113 fps (8.82-8.98 ms)
    2000 cubes flattened + shadow . 132-148 fps (6.74-7.59 ms)
See research/python-3d-engine.md for the full table and caveats.
"""
import argparse
import ctypes
import math
import sys
import time

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Vec4,
    loadPrcFileData,
)

ap = argparse.ArgumentParser()
ap.add_argument("--cubes", type=int, default=300)
ap.add_argument("--frames", type=int, default=150)
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
ap.add_argument("--shadow", action="store_true")
ap.add_argument("--flatten", action="store_true")
args = ap.parse_args()

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", f"win-size {args.width} {args.height}")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "sync-video false")
loadPrcFileData("", "threading-model")  # single-threaded render pipeline

from direct.showbase.ShowBase import ShowBase  # noqa: E402

gl = ctypes.CDLL("libGL.so.1")  # for glFinish()

base = ShowBase(windowType="offscreen")
base.setFrameRateMeter(False)
base.disableMouse()

base.cam.setPos(0, -110, 45)
base.cam.lookAt(0, 0, 10)

amb = AmbientLight("amb")
amb.setColor(Vec4(0.3, 0.3, 0.35, 1))
base.render.setLight(base.render.attachNewNode(amb))
sun = DirectionalLight("sun")
sun.setColor(Vec4(0.9, 0.85, 0.8, 1))
sun_np = base.render.attachNewNode(sun)
sun_np.setHpr(45, -45, 0)
base.render.setLight(sun_np)
if args.shadow:
    sun.setShadowCaster(True, 2048, 2048)
    base.render.setShaderAuto()

template = base.loader.loadModel("models/box")
template.setScale(1.4)
cubes = []
for i in range(args.cubes):
    c = template.copyTo(base.render)
    a = i * 2.39996
    r = 8 + (i % 40) * 6.0
    c.setPos(math.cos(a) * r, math.sin(a) * r, 1.0 + (i // 40) * 3.0)
    cubes.append(c)
if args.flatten:
    base.render.flattenStrong()

gsg = base.win.getGsg()
print(f"python {sys.version.split()[0]} | panda3d {__import__('panda3d').__version__}")
print(f"renderer: {gsg.getDriverRenderer()} | GL {gsg.getDriverVersion()}")
print(f"pipe: {base.win.getPipe().getType().getName()}")
print(f"size: {base.win.getXSize()}x{base.win.getYSize()} cubes: {args.cubes} "
      f"shadow: {args.shadow} flatten: {args.flatten}")

# Warm-up frame: compiles shaders, uploads geometry.
base.graphicsEngine.renderFrame()
base.graphicsEngine.syncFrame()
gl.glFinish()

t0 = time.perf_counter()
for _ in range(args.frames):
    for c in cubes:
        c.setH(c.getH() + 1.0)
    base.graphicsEngine.renderFrame()
    base.graphicsEngine.syncFrame()
    gl.glFinish()
elapsed = time.perf_counter() - t0

print(f"GPU-complete: {args.frames / elapsed:.1f} fps "
      f"({elapsed * 1000 / args.frames:.2f} ms/frame)")
base.destroy()
