"""Machine configuration (configs/machine.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

Vec2 = tuple[float, float]


class Canvas(BaseModel):
    width: float
    height: float
    origin: Vec2 = (0.0, 0.0)
    surface_z: float = 0.0


class Motion(BaseModel):
    travel_z: float = 15.0
    hover_z: float = 3.0
    travel_speed: float = 150.0
    z_speed: float = 20.0
    paint_speed: float = 60.0
    # Machine travel limits (soft limits checked by the G-code simulator).
    x_range: Vec2 = (0.0, 600.0)
    y_range: Vec2 = (0.0, 400.0)
    z_range: Vec2 = (-25.0, 50.0)
    a_limit: float = 200.0  # |A| in degrees; the brush rotation axis has a cable, so it must not wind up


class Palette(BaseModel):
    origin: Vec2
    pitch: Vec2
    columns: int = 2
    slots: int = Field(gt=0)
    slot_capacity: float = 100.0
    refill_threshold: float = 15.0

    def slot_position(self, slot: int) -> Vec2:
        if not 0 <= slot < self.slots:
            raise ValueError(f"palette slot {slot} out of range (0..{self.slots - 1})")
        col, row = slot % self.columns, slot // self.columns
        return (self.origin[0] + col * self.pitch[0], self.origin[1] + row * self.pitch[1])


class Wash(BaseModel):
    position: Vec2
    radius: float = 25.0
    depth_z: float = -20.0
    circles: int = 6


class Wipe(BaseModel):
    position: Vec2
    length: float = 60.0
    passes: int = 3


class BrushRack(BaseModel):
    origin: Vec2
    pitch: float = 30.0


class Camera(BaseModel):
    """Overhead camera that photographs the canvas between layers (closed loop)."""

    resolution: tuple[int, int] = (1600, 1200)
    # Canvas corners in the camera image (px): top-left, top-right, bottom-right, bottom-left.
    # Measure them on the machine (or detect markers at the canvas corners).
    canvas_corners: list[Vec2] = [(250, 160), (1370, 140), (1450, 1070), (170, 1090)]
    park: Vec2 = (560, 390)  # head position while the photo is taken (out of the camera view)
    capture_s: float = 5.0  # park + settle + take the photo


class Brush(BaseModel):
    id: str
    kind: Literal["flat", "round"]
    width: float = Field(gt=0)
    press_depth: float = Field(gt=0)
    capacity: float = Field(gt=0)
    paint_per_dip: float = Field(gt=0)


class MachineConfig(BaseModel):
    canvas: Canvas
    motion: Motion = Motion()
    palette: Palette
    wash: Wash
    wipe: Wipe
    brush_rack: BrushRack
    brushes: list[Brush]
    camera: Camera = Camera()

    @model_validator(mode="after")
    def _unique_brushes(self) -> "MachineConfig":
        ids = [b.id for b in self.brushes]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate brush ids: {ids}")
        if not ids:
            raise ValueError("at least one brush is required")
        return self

    def brush(self, brush_id: str) -> Brush:
        for b in self.brushes:
            if b.id == brush_id:
                return b
        raise KeyError(brush_id)

    def rack_position(self, brush_id: str) -> Vec2:
        idx = [b.id for b in self.brushes].index(brush_id)
        return (self.brush_rack.origin[0], self.brush_rack.origin[1] + idx * self.brush_rack.pitch)

    def canvas_to_machine(self, x: float, y: float) -> Vec2:
        return (self.canvas.origin[0] + x, self.canvas.origin[1] + y)


def load_config(path: str | Path) -> MachineConfig:
    with open(path, encoding="utf-8") as f:
        return MachineConfig.model_validate(yaml.safe_load(f))
