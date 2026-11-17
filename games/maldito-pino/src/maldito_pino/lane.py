"""Lane, pins and ball physics/visuals for Maldito Pino."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from panda3d.bullet import (
    BulletBoxShape,
    BulletConvexHullShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    NodePath,
    Point3,
    TransformState,
    Vec3,
    Vec4,
)

BALL_MASS = 7.0
BALL_RADIUS = 0.108
BALL_START_Y = 0.50
BALL_START_X = 0.15
PIN_MASS = 1.5
PIN_HEIGHT = 0.38
PIN_COM_Z = 0.15
PIN_SPACING = 0.3048
ROW_OFFSET = PIN_SPACING * math.sqrt(3.0) / 2.0
HEAD_PIN_Y = 18.29
POCKET_X = PIN_SPACING / 4.0
LANE_WIDTH = 1.05
LANE_LENGTH = 20.0
LANE_THICKNESS = 0.05
DT = 1.0 / 120.0
GRAVITY = Vec3(0.0, 0.0, -9.81)

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

PIN_POSITIONS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (-PIN_SPACING / 2.0, ROW_OFFSET),
    (PIN_SPACING / 2.0, ROW_OFFSET),
    (-PIN_SPACING, 2.0 * ROW_OFFSET),
    (0.0, 2.0 * ROW_OFFSET),
    (PIN_SPACING, 2.0 * ROW_OFFSET),
    (-1.5 * PIN_SPACING, 3.0 * ROW_OFFSET),
    (-PIN_SPACING / 2.0, 3.0 * ROW_OFFSET),
    (PIN_SPACING / 2.0, 3.0 * ROW_OFFSET),
    (1.5 * PIN_SPACING, 3.0 * ROW_OFFSET),
)


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
    shape.set_margin(0.001)
    return shape


def _pin_mesh(segments: int = 24) -> NodePath:
    fmt = GeomVertexFormat.get_v3n3()
    data = GeomVertexData("pin", fmt, Geom.UH_static)
    vertices = GeomVertexWriter(data, "vertex")
    normals = GeomVertexWriter(data, "normal")

    rings: list[list[int]] = []
    for index, (radius, height) in enumerate(PIN_PROFILE):
        z = height - PIN_COM_Z
        if radius <= 1e-6:
            point_row = data.get_num_rows()
            vertices.add_data3(0.0, 0.0, z)
            normals.add_data3(0.0, 0.0, -1.0 if index == 0 else 1.0)
            rings.append([point_row])
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
                    lower[0], upper[segment], upper[(segment + 1) % segments]
                )
        elif len(upper) == 1:
            for segment in range(segments):
                triangles.add_vertices(
                    lower[segment], upper[0], lower[(segment + 1) % segments]
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


class Lane:
    """One lane with a subset of the ten pins and a ball."""

    def __init__(self, base: Any, scene: NodePath) -> None:
        self.base = base
        self.scene = scene
        self.root = scene.attach_new_node("lane")
        self.world = BulletWorld()
        self.world.set_gravity(GRAVITY)
        self.world.set_force_update_all_aabbs(True)

        self.pin_bodies: list[BulletRigidBodyNode] = []
        self.pin_visuals: list[NodePath] = []
        self.pin_index: dict[int, int] = {}
        self.ball_body: BulletRigidBodyNode | None = None
        self.ball_visual: NodePath | None = None
        self.aim_node: NodePath | None = None
        self.standing: set[int] = set()

        self._build_static()
        self._build_static_visuals()

    def _static_box(
        self,
        name: str,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        *,
        friction: float,
        restitution: float = 0.0,
    ) -> None:
        body = BulletRigidBodyNode(name)
        body.set_mass(0.0)
        shape = BulletBoxShape(Vec3(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0))
        shape.set_margin(0.001)
        body.add_shape(shape)
        body.set_transform(TransformState.make_pos(Point3(*center)))
        body.set_friction(friction)
        body.set_restitution(restitution)
        self.world.attach_rigid_body(body)

    def _build_static(self) -> None:
        self._static_box(
            "lane",
            (0.0, LANE_LENGTH / 2.0, -LANE_THICKNESS / 2.0),
            (LANE_WIDTH, LANE_LENGTH, LANE_THICKNESS),
            friction=0.20,
        )
        self._static_box(
            "back-wall",
            (0.0, LANE_LENGTH + 0.05, 0.45),
            (LANE_WIDTH + 0.4, 0.1, 0.9),
            friction=0.5,
        )
        for side in (-1.0, 1.0):
            self._static_box(
                f"gutter-{side:+.0f}",
                (side * (LANE_WIDTH / 2.0 + 0.09), LANE_LENGTH / 2.0, -0.075),
                (0.18, LANE_LENGTH, 0.05),
                friction=0.1,
            )
            self._static_box(
                f"side-wall-{side:+.0f}",
                (side * (LANE_WIDTH / 2.0 + 0.40), LANE_LENGTH / 2.0, 0.25),
                (0.1, LANE_LENGTH, 0.5),
                friction=0.3,
            )
        self._static_box(
            "catch-floor",
            (0.0, 10.0, -1.05),
            (4.0, 22.0, 0.1),
            friction=0.4,
        )

    def _box_visual(
        self,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        color: Vec4,
    ) -> NodePath:
        model = self.base.loader.loadModel("models/box")
        model.set_texture_off(1)
        model.set_scale(*size)
        model.set_pos(
            center[0] - size[0] / 2.0,
            center[1] - size[1] / 2.0,
            center[2] - size[2] / 2.0,
        )
        model.set_color(color)
        model.reparent_to(self.root)
        return model

    def _build_static_visuals(self) -> None:
        self._box_visual(
            (0.0, LANE_LENGTH / 2.0, -LANE_THICKNESS / 2.0),
            (LANE_WIDTH, LANE_LENGTH, LANE_THICKNESS),
            Vec4(0.56, 0.39, 0.23, 1.0),
        )
        self._box_visual(
            (0.0, LANE_LENGTH + 0.05, 0.45),
            (LANE_WIDTH + 0.4, 0.1, 0.9),
            Vec4(0.08, 0.10, 0.14, 1.0),
        )
        for side in (-1.0, 1.0):
            self._box_visual(
                (side * (LANE_WIDTH / 2.0 + 0.09), LANE_LENGTH / 2.0, -0.075),
                (0.18, LANE_LENGTH, 0.05),
                Vec4(0.05, 0.06, 0.08, 1.0),
            )
            self._box_visual(
                (side * (LANE_WIDTH / 2.0 + 0.40), LANE_LENGTH / 2.0, 0.25),
                (0.1, LANE_LENGTH, 0.5),
                Vec4(0.06, 0.08, 0.11, 1.0),
            )
        self._box_visual(
            (0.0, 10.0, -1.05),
            (4.0, 22.0, 0.1),
            Vec4(0.04, 0.05, 0.07, 1.0),
        )
        self._box_visual(
            (0.0, 0.05, 0.002),
            (LANE_WIDTH, 0.025, 0.004),
            Vec4(0.92, 0.88, 0.76, 1.0),
        )

    def reset(self, standing: Iterable[int]) -> None:
        self.hide_aim()
        if self.ball_body is not None:
            self.world.remove_rigid_body(self.ball_body)
            self.ball_body = None
        if self.ball_visual is not None:
            self.ball_visual.remove_node()
            self.ball_visual = None
        for body in self.pin_bodies:
            self.world.remove_rigid_body(body)
        for visual in self.pin_visuals:
            visual.remove_node()
        self.pin_bodies = []
        self.pin_visuals = []
        self.pin_index = {}

        self.standing = set(standing)
        for index in sorted(self.standing):
            x_offset, y_offset = PIN_POSITIONS[index]
            body = BulletRigidBodyNode(f"pin-{index + 1}")
            body.set_mass(PIN_MASS)
            body.add_shape(_pin_hull_shape())
            body.set_friction(0.20)
            body.set_restitution(0.10)
            body.set_linear_damping(0.05)
            body.set_angular_damping(0.05)
            body.set_ccd_motion_threshold(0.005)
            body.set_ccd_swept_sphere_radius(0.03)
            body.set_transform(
                TransformState.make_pos(
                    Point3(x_offset, HEAD_PIN_Y + y_offset, PIN_COM_Z)
                )
            )
            self.world.attach_rigid_body(body)
            self.pin_bodies.append(body)
            self.pin_index[id(body)] = index

            visual = _pin_mesh()
            visual.reparent_to(self.root)
            visual.set_color(Vec4(0.95, 0.92, 0.84, 1.0))
            visual.set_transform(body.get_transform())
            self.pin_visuals.append(visual)

        self._make_ball()

    def _make_ball(self) -> None:
        body = BulletRigidBodyNode("ball")
        body.set_mass(BALL_MASS)
        shape = BulletSphereShape(BALL_RADIUS)
        shape.set_margin(0.001)
        body.add_shape(shape)
        body.set_friction(0.05)
        body.set_restitution(0.10)
        body.set_linear_damping(0.01)
        body.set_angular_damping(0.01)
        body.set_ccd_motion_threshold(0.005)
        body.set_ccd_swept_sphere_radius(BALL_RADIUS * 0.95)
        body.set_transform(
            TransformState.make_pos(
                Point3(BALL_START_X, BALL_START_Y, BALL_RADIUS)
            )
        )
        self.world.attach_rigid_body(body)
        self.ball_body = body

        visual = self.base.loader.loadModel("models/misc/sphere")
        visual.set_texture_off(1)
        visual.set_scale(BALL_RADIUS)
        visual.set_color(Vec4(0.69, 0.18, 0.26, 1.0))
        visual.reparent_to(self.root)
        visual.set_pos(body.get_transform().get_pos())
        self.ball_visual = visual

    def show_aim(self, target_x: float) -> None:
        self.hide_aim()
        segments = LineSegs("aim")
        segments.set_color(Vec4(0.89, 0.70, 0.25, 1.0))
        segments.set_thickness(2.0)
        segments.moveTo(BALL_START_X, BALL_START_Y, 0.02)
        segments.drawTo(target_x, HEAD_PIN_Y, 0.02)
        self.aim_node = self.root.attach_new_node(segments.create())

    def hide_aim(self) -> None:
        if self.aim_node is not None:
            self.aim_node.remove_node()
            self.aim_node = None

    def throw(self, speed: float, target_x: float, spin_y: float) -> None:
        if self.ball_body is None:
            raise RuntimeError("no hay bola")
        dx = target_x - BALL_START_X
        dy = HEAD_PIN_Y - BALL_START_Y
        length = math.hypot(dx, dy)
        self.ball_body.set_linear_velocity(Vec3(speed * dx / length, speed * dy / length, 0))
        self.ball_body.set_angular_velocity(
            Vec3(-speed / BALL_RADIUS, spin_y, 0.0)
        )
        self.ball_body.set_active(True)

    def step(self) -> None:
        self.world.do_physics(DT)
        self.sync_visuals()

    def sync_visuals(self) -> None:
        for body, visual in zip(self.pin_bodies, self.pin_visuals, strict=True):
            visual.set_transform(body.get_transform())
        if self.ball_body is not None and self.ball_visual is not None:
            self.ball_visual.set_pos(self.ball_body.get_transform().get_pos())

    def remaining(self) -> set[int]:
        remaining: set[int] = set()
        for body in self.pin_bodies:
            transform = body.get_transform()
            pos = transform.get_pos()
            up = transform.get_quat().xform(Vec3(0.0, 0.0, 1.0))
            tilt = math.degrees(math.acos(_clamp(up.z, -1.0, 1.0)))
            off_lane = abs(pos.x) > 0.62 or pos.y > 19.65
            fallen = tilt > 25.0 or pos.z < 0.10 or off_lane
            if not fallen:
                remaining.add(self.pin_index[id(body)])
        return remaining

    def ball_finished(self) -> bool:
        if self.ball_body is None:
            return True
        pos = self.ball_body.get_transform().get_pos()
        return pos.y > 19.8 or pos.z < -0.5 or abs(pos.x) > 1.2

    def ball_position(self) -> Vec3:
        if self.ball_body is None:
            return Vec3(0.0, 0.0, 0.0)
        return self.ball_body.get_transform().get_pos()

    def destroy(self) -> None:
        for body in self.pin_bodies:
            self.world.remove_rigid_body(body)
        if self.ball_body is not None:
            self.world.remove_rigid_body(self.ball_body)
        self.root.remove_node()
