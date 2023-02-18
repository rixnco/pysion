from __future__ import annotations
from dataclasses import dataclass
from .input import Input, Polyline
from .user_controls import UserControl
from typing import Literal
from .flow import fusion_coords
from .color import RGBA
from .named_table import NamedTable, UnnamedTable


@dataclass
class Tool:
    """Represents a Fusion Tool. Outputs a NamedTable, with the tool ID being the name."""

    id: str
    name: str
    position: tuple[int, int] | None = (0, 0)
    inputs: UnnamedTable[str, Input] | None = None
    output: str = "Output"
    user_controls: UnnamedTable[str, UserControl] | None = None

    # Renderers
    def render(self) -> NamedTable:
        inputs, user_controls = None, None

        if self.inputs:
            inputs = UnnamedTable()
            for name, inp in self.inputs.items():
                if isinstance(inp, NamedTable):
                    inputs[name] = inp

                if isinstance(inp, Input):
                    inputs[name] = inp.nt

        if self.user_controls:
            user_controls: UnnamedTable[str, NamedTable] = UnnamedTable(
                {name: control.nt for name, control in self.user_controls.items()}
            )

        return NamedTable(
            self.id,
            Inputs=inputs,
            ViewInfo=self.position_nt,
            UserControls=user_controls,
            force_indent=True,
        )

    def __repr__(self) -> str:
        return repr(self.render())

    def _render_position(self) -> NamedTable | None:
        if self.position is None:
            return None
        return NamedTable("OperatorInfo", Pos=fusion_coords(self.position))

    @property
    def position_nt(self) -> NamedTable | None:
        return self._render_position()

    def _render_output(self) -> NamedTable:
        return NamedTable("InstanceOutput", SourceOp=self.name, Source=self.output)

    # Inputs
    def add_input(self, input: Input) -> Tool:
        if self.inputs is None:
            self.inputs = UnnamedTable(force_indent=True)

        self.inputs[input.name] = input

        return self

    def add_inputs(self, *inputs, **names_and_values) -> Tool:
        """Add Inputs as a batch. Takes Input() types as positional args, and/or
        key/value pairs as keyword args that map to Input(Key, value=Value)"""

        if inputs:
            for input in inputs:
                self.add_input(input)

        if names_and_values:
            for k, v in names_and_values.items():
                self.add_input(Input(k, v))

        return self

    def add_source_input(self, name: str, source_operator: str, source: str) -> Tool:
        self.add_input(Input(name, source_operator=source_operator, source=source))

        return self

    def add_expression_input(
        self, name: str, expression: str, value: int | float | str | None = None
    ) -> Tool:
        self.add_input(Input(name, value, expression))

        return self

    def add_published_polyline(self, points: list[tuple[float, float]]) -> Tool:
        poly = Polyline(points).inputs

        for input in poly:
            self.inputs[input.name] = input

        return self

    def add_color_input(self, color: RGBA | None, prefix: str = "", suffix: str = ""):
        """Adds color input from RGBA. Different Prefixes and Suffixes are added to color inputs in Fusion.
        Backgrounds usually default to TopLeft[Color] for solid fills.
        Text+ nodes have [Color]1, [Color]2 etc for different layers.
        """
        if not color:
            return self

        self.add_inputs(
            **{
                f"{prefix}Red{suffix}": color.red,
                f"{prefix}Green{suffix}": color.green,
                f"{prefix}Blue{suffix}": color.blue,
                f"{prefix}Alpha{suffix}": color.alpha,
            }
        )

        return self

    def add_mask(self, mask: Tool) -> Tool:
        self.inputs["EffectMask"] = Input(
            "EffectMask", source_operator=mask.name, source=mask.output
        )

        return self

    # Alternate Constructors
    @classmethod
    def mask(
        cls,
        name: str,
        type: Literal["Rectangle", "Ellipse", "Polyline", "BSpline"] = "Rectangle",
        position: tuple[int, int] = (0, 0),
    ) -> Tool:
        """Creates a Mask tool and automatically sets the correct output name for a mask."""

        return Tool(id=f"{type}Mask", name=name, position=position, output="Mask")

    @classmethod
    def background(
        cls,
        name: str,
        top_left: RGBA | None = None,
        top_right: RGBA | None = None,
        bottom_left: RGBA | None = None,
        bottom_right: RGBA | None = None,
        resolution: tuple[int, int] | Literal["auto"] = "auto",
        position: tuple[int, int] = (0, 0),
    ) -> Tool:
        """Creates a Background tool and automatically sets color and resolution inputs."""

        bg = (
            Tool("Background", name, position)
            .add_color_input(top_left, "TopLeft")
            .add_color_input(top_right, "TopRight")
            .add_color_input(bottom_left, "BottomLeft")
            .add_color_input(bottom_right, "BottomRight")
        )

        if resolution == "auto":
            return bg.add_inputs(UseFrameFormatSettings=1)

        return bg.add_inputs(
            UseFrameFormatSettings=0, Width=resolution[0], Height=resolution[1]
        )

    # Deprecated...
    @classmethod
    def merge(
        cls,
        name: str,
        background: Tool | None,
        foreground: Tool | None,
        position: tuple[int, int],
    ) -> Tool:
        mrg = Tool("Merge", name, position)

        if background is not None:
            try:
                background.output
                bg_out = background.output
            except AttributeError:
                bg_out = "Output"

            background = Input(
                "Background", source_operator=background.name, source=bg_out
            )
            mrg.add_input(background)

        if foreground is not None:
            try:
                foreground.output
                fg_out = foreground.output
            except AttributeError:
                fg_out = "Output"

            foreground = Input(
                "Foreground", source_operator=foreground.name, source=fg_out
            )
            mrg.add_input(foreground)

        return mrg
