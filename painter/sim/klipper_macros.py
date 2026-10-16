"""Minimal Klipper `[gcode_macro]` expander, so the simulator runs the same macros the printer would.

Follows Klipper's semantics where they matter here:
- Templates are Jinja2 with `{ }` for expressions (Klipper's delimiters, not `{{ }}`).
- `variable_*` options are parsed with `ast.literal_eval` and exposed as `printer["gcode_macro NAME"].var`.
- A macro's template is rendered once when it is called (variables are a snapshot at that moment);
  SET_GCODE_VARIABLE takes effect for macros called afterwards.
- Command parameters are upper case: `params.BRUSH`.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import jinja2


@dataclass
class Macro:
    name: str  # upper case, as used to call it
    section: str  # name as written in the config
    template: jinja2.Template
    variables: dict = field(default_factory=dict)


def _strip_comment(line: str) -> str:
    s = line.strip()
    if s.startswith("#") or s.startswith(";"):
        return ""
    # Klipper (configparser) inline comments need whitespace before the prefix.
    return re.split(r"\s[#;]", line, maxsplit=1)[0].rstrip()


def parse_macros(path: str | Path) -> dict[str, Macro]:
    env = jinja2.Environment("{%", "%}", "{", "}")
    macros: dict[str, Macro] = {}
    section = None
    options: dict[str, list[str]] = {}
    key = None

    def flush():
        if section is None:
            return
        name = section.upper()
        variables = {}
        for k, v in options.items():
            if k.startswith("variable_"):
                variables[k[len("variable_"):]] = ast.literal_eval("\n".join(v).strip())
        gcode = "\n".join(options.get("gcode", []))
        macros[name] = Macro(name, section, env.from_string(gcode), variables)

    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        m = re.match(r"^\[(.+)\]\s*$", raw.strip()) if not raw[0].isspace() else None
        if m:
            flush()
            head = m.group(1).split()
            section = head[1] if head[0] == "gcode_macro" and len(head) > 1 else None
            options, key = {}, None
            continue
        if section is None:
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if not raw[0].isspace():
            k, _, v = line.partition(":")
            key = k.strip().lower()
            options[key] = [v.strip()] if v.strip() else []
        elif key is not None:
            options[key].append(line.strip())
    flush()
    return macros


def parse_params(args: str) -> dict[str, str]:
    """`BRUSH=2 SLOT=3` -> {"BRUSH": "2", "SLOT": "3"}."""
    out = {}
    for tok in args.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.upper()] = v
    return out


class MacroEngine:
    def __init__(self, macros: dict[str, Macro]):
        self.macros = macros

    def printer(self) -> dict:
        out = {}
        for m in self.macros.values():
            for key in {m.section, m.section.lower(), m.name}:
                out[f"gcode_macro {key}"] = dict(m.variables)
        return out

    def is_macro(self, command: str) -> bool:
        return command.upper() in self.macros

    def render(self, command: str, params: dict[str, str]) -> list[str]:
        macro = self.macros[command.upper()]
        text = macro.template.render(params=params, printer=self.printer(), rawparams="")
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    def set_variable(self, params: dict[str, str]) -> None:
        macro = self.macros[params["MACRO"].upper()]
        var = params["VARIABLE"].lower()
        if var not in macro.variables:
            raise KeyError(f"SET_GCODE_VARIABLE: {macro.name} has no variable {var}")
        macro.variables[var] = ast.literal_eval(params["VALUE"])
