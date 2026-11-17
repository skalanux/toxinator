#!/usr/bin/env python3
"""Bowling physics prototype for Toxinator #16.

Standalone Panda3D/Bullet scene: one lane, ten pins and a ball. It runs
batched throws, a small parameter sweep, rest-jitter and FPS measurements,
and optionally renders a clip of a representative shot.

Run with:

    uv run --with panda3d==1.10.16 python prototype/bowling-physics/sim.py all

No game code, no UI, no runtime dependencies beyond Panda3D.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
import subprocess
import tempfile
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from panda3d.bullet import (
    BulletBoxShape,
    BulletConvexHullShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Point3,
    TransformState,
    Vec3,
    Vec4,
    loadPrcFileData,
)

# ---------------------------------------------------------------------------
# Dimensions (SI, meters)
# ---------------------------------------------------------------------------

BALL_RADIUS = 0.108  # ~21.6 cm diameter
BALL_START_Y = 0.50
PIN_HEIGHT = 0.38
PIN_COM_Z = 0.15
PIN_SPACING = 0.3048  # 12 in
ROW_OFFSET = PIN_SPACING * math.sqrt(3.0) / 2.0
HEAD_PIN_Y = 18.29  # foul line to head pin
POCKET_X = PIN_SPACING / 4.0  # between the 1 and 3 pins
LANE_WIDTH = 1.05
LANE_LENGTH = 20.0
LANE_THICKNESS = 0.05
DT = 1.0 / 120.0
GRAVITY = Vec3(0.0, 0.0, -9.81)

# Profile is (radius, height above the pin base), bottom to top.
PIN_PROFILE: tuple[tuple[float, float], ...] = (
    (0.000, 0.000),
    (0.028, 0.000),
    (0.045, 0.012),
    (0.056, 0.035),
    (0.060, 0.090),
    (0.055, 0.150),
    (0.045, 0.200),
    (0.035, 0.240),
    (0.028, 0.270),
    (0.030, 0.300),
    (0.036, 0.330),
    (0.034, 0.355),
    (0.022, 0.372),
    (0.000, 0.380),
)

# (x, y offset from the head pin), standard 10-pin triangle.
PIN_POSITIONS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),  # 1
    (-PIN_SPACING / 2.0, ROW_OFFSET),  # 2
    (PIN_SPACING / 2.0, ROW_OFFSET),  # 3
    (-PIN_SPACING, 2.0 * ROW_OFFSET),  # 4
    (0.0, 2.0 * ROW_OFFSET),  # 5
    (PIN_SPACING, 2.0 * ROW_OFFSET),  # 6
    (-1.5 * PIN_SPACING, 3.0 * ROW_OFFSET),  # 7
    (-PIN_SPACING / 2.0, 3.0 * ROW_OFFSET),  # 8
    (PIN_SPACING / 2.0, 3.0 * ROW_OFFSET),  # 9
    (1.5 * PIN_SPACING, 3.0 * ROW_OFFSET),  # 10
)


# ---------------------------------------------------------------------------
# Configuration and data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    name: str = "baseline"
    ball_mass: float = 7.0
    ball_radius: float = BALL_RADIUS
    ball_friction: float = 0.05
    ball_restitution: float = 0.10
    ball_linear_damping: float = 0.01
    ball_angular_damping: float = 0.01
    ball_ccd: bool = True
    pin_mass: float = 1.5
    pin_friction: float = 0.20
    pin_restitution: float = 0.10
    pin_linear_damping: float = 0.05
    pin_angular_damping: float = 0.05
    pin_ccd: bool = True
    lane_friction: float = 0.20
    lane_restitution: float = 0.0


@dataclass(frozen=True)
class ThrowSpec:
    id: int
    kind: str = "normal"
    speed: float = 8.0
    start_x: float = 0.0
    target_x: float = POCKET_X
    spin_y: float = 0.0
    spin_ratio: float = 1.0
    max_time: float = 5.0


@dataclass
class ThrowResult:
    id: int
    kind: str
    speed: float
    start_x: float
    target_x: float
    spin_y: float
    fallen: int
    strike: bool
    fallen_ids: list[int]
    standing_ids: list[int]
    ball_contacts: int
    pin_contacts: int
    pin_pin_contacts: int
    max_ball_speed: float
    ball_end: list[float]
    min_pin_distance: float
    tunnel_flag: bool
    duration: float
    sim_steps: int


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pin_hull_shape() -> BulletConvexHullShape:
    shape = BulletConvexHullShape()
    segments = 12
    for radius, height in PIN_PROFILE:
        z = height - PIN_COM_Z
        if radius <= 1e-6:
            shape.addPoint(Point3(0.0, 0.0, z))
            continue
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            shape.addPoint(
                Point3(radius * math.cos(angle), radius * math.sin(angle), z)
            )
    shape.setMargin(0.001)
    return shape


def _pin_mesh(segments: int = 24) -> NodePath:
    """Lathe a pin profile into a simple lit mesh in body coordinates."""
    fmt = GeomVertexFormat.get_v3n3()
    data = GeomVertexData("pin", fmt, Geom.UH_static)
    vertices = GeomVertexWriter(data, "vertex")
    normals = GeomVertexWriter(data, "normal")

    rings: list[list[int]] = []
    for index, (radius, height) in enumerate(PIN_PROFILE):
        z = height - PIN_COM_Z
        if radius <= 1e-6:
            row = data.get_num_rows()
            vertices.add_data3(0.0, 0.0, z)
            normals.add_data3(0.0, 0.0, -1.0 if index == 0 else 1.0)
            rings.append([row])
            continue

        prev_radius, prev_height = PIN_PROFILE[max(0, index - 1)]
        next_radius, next_height = PIN_PROFILE[min(len(PIN_PROFILE) - 1, index + 1)]
        dr = next_radius - prev_radius
        dz = next_height - prev_height
        normal_r = dz
        normal_z = -dr
        length = math.hypot(normal_r, normal_z) or 1.0
        normal_r /= length
        normal_z /= length

        row: list[int] = []
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            row.append(data.get_num_rows())
            vertices.add_data3(radius * cos_a, radius * sin_a, z)
            normals.add_data3(normal_r * cos_a, normal_r * sin_a, normal_z)
        rings.append(row)

    triangles = GeomTriangles(Geom.UH_static)
    for index in range(len(rings) - 1):
        lower = rings[index]
        upper = rings[index + 1]
        if len(lower) == 1:
            for segment in range(segments):
                triangles.add_vertices(
                    lower[0],
                    upper[segment],
                    upper[(segment + 1) % segments],
                )
        elif len(upper) == 1:
            for segment in range(segments):
                triangles.add_vertices(
                    lower[segment],
                    upper[0],
                    lower[(segment + 1) % segments],
                )
        else:
            for segment in range(segments):
                nxt = (segment + 1) % segments
                triangles.add_vertices(lower[segment], upper[segment], upper[nxt])
                triangles.add_vertices(lower[segment], upper[nxt], lower[nxt])
    triangles.close_primitive()

    geom = Geom(data)
    geom.add_primitive(triangles)
    node = GeomNode("pin-mesh")
    node.add_geom(geom)
    path = NodePath(node)
    path.set_two_sided(True)
    return path


class BowlingWorld:
    def __init__(
        self,
        config: Config,
        *,
        visuals: bool = False,
        base: Any | None = None,
    ) -> None:
        self.config = config
        self.visuals = visuals
        self.base = base
        self.world = BulletWorld()
        self.world.set_gravity(GRAVITY)
        self.world.set_force_update_all_aabbs(True)

        self.pin_bodies: list[BulletRigidBodyNode] = []
        self.pin_visuals: list[NodePath] = []
        self.ball_body: BulletRigidBodyNode | None = None
        self.ball_visual: NodePath | None = None
        self._pin_index = {}
        self._pin_initial: list[Point3] = []

        self._build_lane()
        if visuals:
            if base is None:
                raise ValueError("visuals=True requires a ShowBase")
            self._build_visual_scene()

    # -- world construction -------------------------------------------------

    def _build_lane(self) -> None:
        lane = BulletRigidBodyNode("lane")
        lane.set_mass(0.0)
        lane.add_shape(
            BulletBoxShape(
                Vec3(LANE_WIDTH / 2.0, LANE_LENGTH / 2.0, LANE_THICKNESS / 2.0)
            )
        )
        lane.set_transform(
            TransformState.make_pos(
                Point3(0.0, LANE_LENGTH / 2.0, -LANE_THICKNESS / 2.0)
            )
        )
        lane.set_friction(self.config.lane_friction)
        lane.set_restitution(self.config.lane_restitution)
        self.world.attach_rigid_body(lane)
        self.lane_body = lane

        back_wall = BulletRigidBodyNode("back-wall")
        back_wall.set_mass(0.0)
        back_wall.add_shape(BulletBoxShape(Vec3(LANE_WIDTH / 2.0, 0.05, 0.45)))
        back_wall.set_transform(
            TransformState.make_pos(Point3(0.0, LANE_LENGTH + 0.05, 0.45))
        )
        back_wall.set_friction(0.5)
        back_wall.set_restitution(0.0)
        self.world.attach_rigid_body(back_wall)

        for side in (-1.0, 1.0):
            gutter = BulletRigidBodyNode(f"gutter-{side:+.0f}")
            gutter.set_mass(0.0)
            gutter.add_shape(BulletBoxShape(Vec3(0.09, LANE_LENGTH / 2.0, 0.025)))
            gutter.set_transform(
                TransformState.make_pos(
                    Point3(
                        side * (LANE_WIDTH / 2.0 + 0.09),
                        LANE_LENGTH / 2.0,
                        -0.065,
                    )
                )
            )
            gutter.set_friction(0.1)
            gutter.set_restitution(0.0)
            self.world.attach_rigid_body(gutter)

        catch_floor = BulletRigidBodyNode("catch-floor")
        catch_floor.set_mass(0.0)
        catch_floor.add_shape(BulletBoxShape(Vec3(12.0, 15.0, 2.0)))
        catch_floor.set_transform(
            TransformState.make_pos(Point3(0.0, 10.0, -3.0))
        )
        catch_floor.set_friction(0.4)
        catch_floor.set_restitution(0.0)
        self.world.attach_rigid_body(catch_floor)

    def _build_visual_scene(self) -> None:
        render = self.base.render
        ambient = AmbientLight("ambient")
        ambient.set_color(Vec4(0.55, 0.55, 0.58, 1.0))
        render.set_light(render.attach_new_node(ambient))

        directional = DirectionalLight("key")
        directional.set_color(Vec4(1.0, 0.94, 0.82, 1.0))
        key = render.attach_new_node(directional)
        key.set_hpr(35.0, -52.0, 0.0)
        render.set_light(key)

        lane = self.base.loader.loadModel("models/box")
        lane.set_texture_off(1)
        lane.set_scale(LANE_WIDTH, LANE_LENGTH, LANE_THICKNESS)
        lane.set_pos(0.0, LANE_LENGTH / 2.0, -LANE_THICKNESS / 2.0)
        lane.set_color(Vec4(0.56, 0.39, 0.23, 1.0))
        lane.reparent_to(render)

        for side in (-1.0, 1.0):
            gutter = self.base.loader.loadModel("models/box")
            gutter.set_texture_off(1)
            gutter.set_scale(0.16, LANE_LENGTH, 0.05)
            gutter.set_pos(
                side * (LANE_WIDTH / 2.0 + 0.09),
                LANE_LENGTH / 2.0,
                -0.07,
            )
            gutter.set_color(Vec4(0.07, 0.08, 0.10, 1.0))
            gutter.reparent_to(render)

        wall = self.base.loader.loadModel("models/box")
        wall.set_texture_off(1)
        wall.set_scale(LANE_WIDTH + 0.4, 0.1, 0.9)
        wall.set_pos(0.0, LANE_LENGTH + 0.05, 0.45)
        wall.set_color(Vec4(0.08, 0.10, 0.14, 1.0))
        wall.reparent_to(render)

        foul = self.base.loader.loadModel("models/box")
        foul.set_texture_off(1)
        foul.set_scale(LANE_WIDTH, 0.025, 0.004)
        foul.set_pos(0.0, 0.05, 0.002)
        foul.set_color(Vec4(0.92, 0.88, 0.76, 1.0))
        foul.reparent_to(render)

        pit = self.base.loader.loadModel("models/box")
        pit.set_texture_off(1)
        pit.set_scale(3.2, 2.2, 0.1)
        pit.set_pos(0.0, 20.2, -1.05)
        pit.set_color(Vec4(0.045, 0.055, 0.075, 1.0))
        pit.reparent_to(render)

        self.base.cam.set_pos(3.4, 13.8, 2.1)
        self.base.cam.look_at(0.0, 18.2, 0.25)
        self.base.camLens.set_fov(60.0)
        self.base.setBackgroundColor(0.025, 0.04, 0.07, 1.0)

    # -- bodies -------------------------------------------------------------

    def reset(self) -> None:
        if self.ball_body is not None:
            self.world.remove_rigid_body(self.ball_body)
            self.ball_body = None
        if self.ball_visual is not None:
            self.ball_visual.remove_node()
            self.ball_visual = None

        for body in self.pin_bodies:
            self.world.remove_rigid_body(body)
        self.pin_bodies.clear()
        self._pin_index.clear()
        self._pin_initial.clear()
        if self.visuals:
            for visual in self.pin_visuals:
                visual.remove_node()
        self.pin_visuals.clear()

        for index, (x_offset, y_offset) in enumerate(PIN_POSITIONS):
            body = BulletRigidBodyNode(f"pin-{index + 1}")
            body.set_mass(self.config.pin_mass)
            body.add_shape(_pin_hull_shape())
            body.set_friction(self.config.pin_friction)
            body.set_restitution(self.config.pin_restitution)
            body.set_linear_damping(self.config.pin_linear_damping)
            body.set_angular_damping(self.config.pin_angular_damping)
            if self.config.pin_ccd:
                body.set_ccd_motion_threshold(0.005)
                body.set_ccd_swept_sphere_radius(0.03)
            body.set_transform(
                TransformState.make_pos(
                    Point3(x_offset, HEAD_PIN_Y + y_offset, PIN_COM_Z)
                )
            )
            self.world.attach_rigid_body(body)
            self.pin_bodies.append(body)
            self._pin_index[id(body)] = index
            self._pin_initial.append(
                body.get_transform().get_pos()
            )

            if self.visuals:
                visual = _pin_mesh()
                visual.reparent_to(self.base.render)
                visual.set_color(Vec4(0.95, 0.92, 0.84, 1.0))
                visual.set_transform(body.get_transform())
                self.pin_visuals.append(visual)

    def _make_ball(self, start_x: float) -> None:
        body = BulletRigidBodyNode("ball")
        body.set_mass(self.config.ball_mass)
        shape = BulletSphereShape(self.config.ball_radius)
        shape.set_margin(0.001)
        body.add_shape(shape)
        body.set_friction(self.config.ball_friction)
        body.set_restitution(self.config.ball_restitution)
        body.set_linear_damping(self.config.ball_linear_damping)
        body.set_angular_damping(self.config.ball_angular_damping)
        if self.config.ball_ccd:
            body.set_ccd_motion_threshold(0.005)
            body.set_ccd_swept_sphere_radius(self.config.ball_radius * 0.95)
        body.set_transform(
            TransformState.make_pos(
                Point3(start_x, BALL_START_Y, self.config.ball_radius)
            )
        )
        self.world.attach_rigid_body(body)
        self.ball_body = body

        if self.visuals:
            visual = self.base.loader.loadModel("models/misc/sphere")
            visual.set_texture_off(1)
            visual.set_scale(self.config.ball_radius)
            visual.set_color(Vec4(0.69, 0.18, 0.26, 1.0))
            visual.reparent_to(self.base.render)
            visual.set_pos(body.get_transform().get_pos())
            self.ball_visual = visual

    # -- throws -------------------------------------------------------------

    def prepare_throw(self, spec: ThrowSpec) -> None:
        self.reset()
        self._make_ball(spec.start_x)
        assert self.ball_body is not None

        dx = spec.target_x - spec.start_x
        dy = HEAD_PIN_Y - BALL_START_Y
        length = math.hypot(dx, dy)
        vx = spec.speed * dx / length
        vy = spec.speed * dy / length
        self.ball_body.set_linear_velocity(Vec3(vx, vy, 0.0))
        self.ball_body.set_angular_velocity(
            Vec3(
                -spec.speed / self.config.ball_radius * spec.spin_ratio,
                spec.spin_y,
                0.0,
            )
        )
        self.ball_body.set_active(True)
        if self.visuals:
            self.sync_visuals()

    def step(self) -> None:
        self.world.do_physics(DT)

    def sync_visuals(self) -> None:
        for body, visual in zip(self.pin_bodies, self.pin_visuals):
            visual.set_transform(body.get_transform())
        if self.ball_body is not None and self.ball_visual is not None:
            self.ball_visual.set_pos(self.ball_body.get_transform().get_pos())

    def pin_state(self) -> tuple[list[int], list[int]]:
        fallen: list[int] = []
        standing: list[int] = []
        for index, body in enumerate(self.pin_bodies):
            transform = body.get_transform()
            pos = transform.get_pos()
            quat = transform.get_quat()
            up = quat.xform(Vec3(0.0, 0.0, 1.0))
            tilt = math.degrees(math.acos(_clamp(up.z, -1.0, 1.0)))
            off_lane = abs(pos.x) > 0.62 or pos.y > 19.65
            is_fallen = tilt > 25.0 or pos.z < 0.10 or off_lane
            (fallen if is_fallen else standing).append(index + 1)
        return fallen, standing

    def run_throw(self, spec: ThrowSpec) -> ThrowResult:
        self.prepare_throw(spec)
        assert self.ball_body is not None

        pin_by_name = {body.get_name(): index for index, body in enumerate(self.pin_bodies)}
        contacted: set[int] = set()
        ball_contacts = 0
        pin_pin_contacts = 0
        max_ball_speed = 0.0
        min_pin_distance = math.inf

        steps = int(spec.max_time / DT)
        elapsed = 0.0
        for step_index in range(steps):
            self.world.do_physics(DT)
            elapsed = (step_index + 1) * DT

            for manifold in self.world.get_manifolds():
                points = manifold.get_num_manifold_points()
                if points <= 0:
                    continue
                node0 = manifold.get_node0()
                node1 = manifold.get_node1()
                name0 = node0.get_name()
                name1 = node1.get_name()
                if name0 == "ball" or name1 == "ball":
                    ball_contacts += points
                    other_name = name1 if name0 == "ball" else name0
                    pin_index = pin_by_name.get(other_name)
                    if pin_index is not None:
                        contacted.add(pin_index)
                elif name0 in pin_by_name and name1 in pin_by_name:
                    pin_pin_contacts += points

            ball_pos = self.ball_body.get_transform().get_pos()
            max_ball_speed = max(
                max_ball_speed, self.ball_body.get_linear_velocity().length()
            )
            for initial in self._pin_initial:
                distance = math.hypot(
                    ball_pos.x - initial.x, ball_pos.y - initial.y
                )
                min_pin_distance = min(min_pin_distance, distance)

            if elapsed > 2.0:
                moving = self.ball_body.is_active() or any(
                    body.is_active() for body in self.pin_bodies
                )
                if not moving:
                    break

        fallen, standing = self.pin_state()
        ball_end = self.ball_body.get_transform().get_pos()
        tunnel_flag = (
            spec.kind == "tunnel"
            and not contacted
            and min_pin_distance < 0.15
        )

        return ThrowResult(
            id=spec.id,
            kind=spec.kind,
            speed=spec.speed,
            start_x=spec.start_x,
            target_x=spec.target_x,
            spin_y=spec.spin_y,
            fallen=len(fallen),
            strike=len(fallen) == 10,
            fallen_ids=fallen,
            standing_ids=standing,
            ball_contacts=ball_contacts,
            pin_contacts=len(contacted),
            pin_pin_contacts=pin_pin_contacts,
            max_ball_speed=max_ball_speed,
            ball_end=[ball_end.x, ball_end.y, ball_end.z],
            min_pin_distance=min_pin_distance,
            tunnel_flag=tunnel_flag,
            duration=elapsed,
            sim_steps=step_index + 1,
        )


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------


def normal_specs() -> list[ThrowSpec]:
    speeds = [6.0, 6.5, 7.0, 7.5, 8.0, 9.0, 10.0]
    starts = [-0.05, 0.0, 0.08, 0.10]
    spins = [-3.0, 0.0, 3.0]
    specs: list[ThrowSpec] = []
    index = 1
    for speed_index, speed in enumerate(speeds):
        for start_index, start_x in enumerate(starts):
            specs.append(
                ThrowSpec(
                    id=index,
                    speed=speed,
                    start_x=start_x,
                    target_x=POCKET_X,
                    spin_y=spins[(speed_index + start_index) % len(spins)],
                )
            )
            index += 1
    for speed in (12.0, 14.0, 16.0):
        specs.append(
            ThrowSpec(
                id=index,
                kind="tunnel",
                speed=speed,
                start_x=0.0,
                target_x=0.0,
                spin_y=0.0,
            )
        )
        index += 1
    return specs


def sweep_specs() -> list[ThrowSpec]:
    specs: list[ThrowSpec] = []
    index = 1
    for speed in (7.0, 7.5, 8.0, 8.5):
        for start_x in (0.0, 0.08):
            for spin_y in (-3.0, 3.0):
                specs.append(
                    ThrowSpec(
                        id=index,
                        speed=speed,
                        start_x=start_x,
                        target_x=POCKET_X,
                        spin_y=spin_y,
                    )
                )
                index += 1
    return specs


def aggregate(results: Iterable[ThrowResult]) -> dict[str, Any]:
    results = list(results)
    if not results:
        return {}
    fallen = [result.fallen for result in results]
    normal = [result for result in results if result.kind == "normal"]
    tunnel = [result for result in results if result.kind == "tunnel"]
    histogram: dict[int, int] = {}
    for result in results:
        histogram[result.fallen] = histogram.get(result.fallen, 0) + 1
    return {
        "throws": len(results),
        "strikes": sum(1 for result in results if result.strike),
        "strike_rate": sum(1 for result in results if result.strike) / len(results),
        "avg_fallen": statistics.mean(fallen),
        "median_fallen": statistics.median(fallen),
        "min_fallen": min(fallen),
        "max_fallen": max(fallen),
        "histogram": {str(key): value for key, value in sorted(histogram.items())},
        "normal": aggregate_simple(normal),
        "tunnel": aggregate_simple(tunnel),
        "tunnel_flags": [result.id for result in results if result.tunnel_flag],
    }


def aggregate_simple(results: list[ThrowResult]) -> dict[str, Any]:
    if not results:
        return {}
    fallen = [result.fallen for result in results]
    return {
        "throws": len(results),
        "strikes": sum(1 for result in results if result.strike),
        "strike_rate": sum(1 for result in results if result.strike) / len(results),
        "avg_fallen": statistics.mean(fallen),
        "median_fallen": statistics.median(fallen),
        "min_fallen": min(fallen),
        "max_fallen": max(fallen),
    }


def run_batch(config: Config, specs: list[ThrowSpec]) -> tuple[list[ThrowResult], dict[str, Any]]:
    world = BowlingWorld(config)
    results = [world.run_throw(spec) for spec in specs]
    return results, aggregate(results)


def run_sweep(base_config: Config) -> dict[str, Any]:
    configs = [
        base_config,
        replace(base_config, name="pin_friction_0.10", pin_friction=0.10),
        replace(base_config, name="pin_restitution_0.25", pin_restitution=0.25),
        replace(base_config, name="ball_friction_0.10", ball_friction=0.10),
        replace(base_config, name="pin_mass_1.3", pin_mass=1.3),
    ]
    specs = sweep_specs()
    output: dict[str, Any] = {}
    for config in configs:
        _, summary = run_batch(config, specs)
        output[config.name] = {
            "config": asdict(config),
            "summary": summary,
        }
    return output


def measure_jitter(config: Config, seconds: float = 5.0) -> dict[str, Any]:
    world = BowlingWorld(config)
    world.reset()
    initial = [body.get_transform().get_pos() for body in world.pin_bodies]
    settle_steps = int(0.5 / DT)
    steps = int(seconds / DT)
    max_displacement = 0.0
    max_tilt = 0.0
    max_angular_speed = 0.0
    settled_positions: list[Point3] | None = None
    drift_after_settle = 0.0

    for step in range(steps):
        world.world.do_physics(DT)
        for index, body in enumerate(world.pin_bodies):
            pos = body.get_transform().get_pos()
            displacement = (pos - initial[index]).length()
            max_displacement = max(max_displacement, displacement)
            angular_speed = body.get_angular_velocity().length()
            max_angular_speed = max(max_angular_speed, angular_speed)
            up = body.get_transform().get_quat().xform(Vec3(0.0, 0.0, 1.0))
            max_tilt = max(
                max_tilt,
                math.degrees(math.acos(_clamp(up.z, -1.0, 1.0))),
            )
        if step + 1 == settle_steps:
            settled_positions = [
                body.get_transform().get_pos() for body in world.pin_bodies
            ]
        if settled_positions is not None:
            for index, body in enumerate(world.pin_bodies):
                drift_after_settle = max(
                    drift_after_settle,
                    (body.get_transform().get_pos() - settled_positions[index]).length(),
                )

    fallen, _ = world.pin_state()
    return {
        "seconds": seconds,
        "settle_seconds": 0.5,
        "max_displacement": max_displacement,
        "drift_after_settle": drift_after_settle,
        "max_tilt_degrees": max_tilt,
        "max_angular_speed": max_angular_speed,
        "fallen_after_rest": len(fallen),
    }


def measure_fps(config: Config, frames: int = 300, width: int = 1280, height: int = 720) -> dict[str, Any]:
    loadPrcFileData(
        "",
        f"audio-library-name null\n"
        f"win-size {width} {height}\n"
        f"sync-video false\n"
        f"notify-level-display error\n"
        f"notify-level-glgsg error\n",
    )
    from direct.showbase.ShowBase import ShowBase

    base = ShowBase(windowType="offscreen")
    try:
        world = BowlingWorld(config, visuals=True, base=base)
        world.prepare_throw(
            ThrowSpec(id=0, speed=7.0, start_x=0.08, target_x=POCKET_X, spin_y=0.0)
        )
        timings: list[float] = []
        for _ in range(frames):
            start = time.perf_counter()
            world.step()
            world.step()
            world.sync_visuals()
            base.graphicsEngine.renderFrame()
            timings.append(time.perf_counter() - start)
        average = statistics.mean(timings)
        ordered = sorted(timings)
        return {
            "frames": frames,
            "width": width,
            "height": height,
            "avg_ms": average * 1000.0,
            "fps": 1.0 / average if average else 0.0,
            "p50_ms": ordered[len(ordered) // 2] * 1000.0,
            "p95_ms": ordered[int(len(ordered) * 0.95)] * 1000.0,
            "max_ms": max(timings) * 1000.0,
        }
    finally:
        base.destroy()


def render_video(
    config: Config,
    output: Path,
    *,
    width: int = 1280,
    height: int = 720,
    fps: int = 60,
    start_time: float = 1.15,
    duration: float = 3.4,
) -> dict[str, Any]:
    loadPrcFileData(
        "",
        f"audio-library-name null\n"
        f"win-size {width} {height}\n"
        f"sync-video false\n"
        f"notify-level-display error\n"
        f"notify-level-glgsg error\n",
    )
    from direct.showbase.ShowBase import ShowBase

    output.parent.mkdir(parents=True, exist_ok=True)
    stills_dir = output.parent
    frame_dir = Path(tempfile.mkdtemp(prefix="bowling-frames-"))
    base = ShowBase(windowType="offscreen")
    try:
        world = BowlingWorld(config, visuals=True, base=base)
        spec = ThrowSpec(
            id=0,
            speed=7.0,
            start_x=0.08,
            target_x=POCKET_X,
            spin_y=0.0,
        )
        world.prepare_throw(spec)
        skip_steps = int(start_time / DT)
        for _ in range(skip_steps):
            world.step()

        frame_count = int(duration * fps)
        steps_per_frame = max(1, round((1.0 / fps) / DT))
        still_indices = {0, frame_count // 3, 2 * frame_count // 3, frame_count - 1}
        for frame in range(frame_count):
            for _ in range(steps_per_frame):
                world.step()
            world.sync_visuals()
            base.graphicsEngine.renderFrame()
            frame_path = frame_dir / f"frame_{frame:04d}.png"
            base.win.saveScreenshot(Filename.from_os_specific(str(frame_path)))
            if frame in still_indices:
                shutil.copyfile(
                    frame_path,
                    stills_dir / f"still-{frame:04d}.png",
                )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(fps),
                "-i",
                str(frame_dir / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "20",
                str(output),
            ],
            check=True,
        )
        return {
            "output": str(output),
            "frames": frame_count,
            "fps": fps,
            "start_time": start_time,
            "duration": duration,
        }
    finally:
        base.destroy()
        shutil.rmtree(frame_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def write_results(
    out_dir: Path,
    *,
    results: list[ThrowResult],
    summary: dict[str, Any],
    sweep: dict[str, Any],
    jitter: dict[str, Any],
    fps: dict[str, Any],
    video: dict[str, Any] | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "baseline": summary,
                "jitter": jitter,
                "fps": fps,
                "video": video,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "sweep.json").write_text(
        json.dumps(sweep, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "jitter.json").write_text(
        json.dumps(jitter, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "fps.json").write_text(
        json.dumps(fps, indent=2) + "\n", encoding="utf-8"
    )

    fields = list(asdict(results[0]).keys())
    with (out_dir / "throws.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            row["fallen_ids"] = " ".join(str(value) for value in row["fallen_ids"])
            row["standing_ids"] = " ".join(str(value) for value in row["standing_ids"])
            row["ball_end"] = " ".join(f"{value:.4f}" for value in row["ball_end"])
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("batch", "sweep", "jitter", "fps", "video", "all"),
    )
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--video", type=Path, default=Path("media/bowling-physics.mp4"))
    parser.add_argument("--frames", type=int, default=300)
    args = parser.parse_args()

    config = Config()

    if args.command in ("batch", "all"):
        print("running 30 baseline throws...")
        results, summary = run_batch(config, normal_specs())
        print(json.dumps(summary, indent=2))
    else:
        results, summary = [], {}

    if args.command in ("sweep", "all"):
        print("running parameter sweep...")
        sweep = run_sweep(config)
    else:
        sweep = {}

    if args.command in ("jitter", "all"):
        print("measuring rest jitter...")
        jitter = measure_jitter(config)
        print(json.dumps(jitter, indent=2))
    else:
        jitter = {}

    if args.command in ("fps", "all"):
        print("measuring render FPS...")
        fps = measure_fps(config, frames=args.frames)
        print(json.dumps(fps, indent=2))
    else:
        fps = {}

    if args.command in ("video", "all"):
        print("rendering clip...")
        video = render_video(config, args.video)
        print(json.dumps(video, indent=2))
    else:
        video = None

    if args.command == "all":
        write_results(
            args.out,
            results=results,
            summary=summary,
            sweep=sweep,
            jitter=jitter,
            fps=fps,
            video=video,
        )
        print(f"wrote {args.out}")
    elif args.command == "batch":
        write_results(
            args.out,
            results=results,
            summary=summary,
            sweep={},
            jitter={},
            fps={},
            video=None,
        )
    elif args.command == "sweep":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "sweep.json").write_text(
            json.dumps(sweep, indent=2) + "\n", encoding="utf-8"
        )
    elif args.command == "jitter":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "jitter.json").write_text(
            json.dumps(jitter, indent=2) + "\n", encoding="utf-8"
        )
    elif args.command == "fps":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "fps.json").write_text(
            json.dumps(fps, indent=2) + "\n", encoding="utf-8"
        )
    elif args.command == "video":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "video.json").write_text(
            json.dumps(video, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
