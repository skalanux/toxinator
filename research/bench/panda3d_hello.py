"""Panda3D hello world: a window with a spinning lit box.

Run:  uv run python research/bench/panda3d_hello.py
Quit: Esc, or close the window.
"""
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, ClockObject, DirectionalLight, Vec4

base = ShowBase()
base.disableMouse()
base.setBackgroundColor(0.08, 0.09, 0.12)

# Camera
base.cam.setPos(0, -6, 2.5)
base.cam.lookAt(0, 0, 0)

# Lights
amb = AmbientLight("amb")
amb.setColor(Vec4(0.35, 0.35, 0.4, 1))
base.render.setLight(base.render.attachNewNode(amb))

sun = DirectionalLight("sun")
sun.setColor(Vec4(0.95, 0.9, 0.85, 1))
sun_np = base.render.attachNewNode(sun)
sun_np.setHpr(35, -35, 0)
base.render.setLight(sun_np)

# Model (models/box ships with the panda3d wheel)
box = base.loader.loadModel("models/box")
box.reparentTo(base.render)
box.setScale(1.5)


def spin(task):
    box.setH(box.getH() + 45 * ClockObject.getGlobalClock().getDt())
    return task.cont


base.taskMgr.add(spin, "spin")
base.run()
