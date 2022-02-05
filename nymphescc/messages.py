# ~\~ language=Python filename=nymphescc/messages.py
# ~\~ begin <<README.md|nymphescc/messages.py>>[0]
from __future__ import annotations
from importlib import resources
import dhall
from pathlib import Path
from dataclasses import dataclass, is_dataclass
import typing
from typing import Optional, Union
import types


class ConfigError(Exception):
    pass


@dataclass
class ConfigValueError(ConfigError):
    setting: Setting
    what: str


@dataclass
class ConfigParserError(ConfigError):
    input_str: str
    what: str


@dataclass
class Bounds:
    lower: int
    upper: int


@dataclass
class Tic:
    value: int
    label: str


@dataclass
class Setting:
    """Setting class.

    Attributes:
        name: name of the setting.
        long: human readable name.
        cc: MIDI CC code
        mod: MIDI CC code of modulator setting
        bounds: lower (inclusive) and upper (exclusive) bounds
        tics: list of known values with description
        labels: list of aliases for settings, should have same length
            as bounds interval.
        flags: list of related settings.
    """
    name: str
    long: str
    cc: int
    bounds: Bounds
    description: Optional[str]
    mod: Optional[int]
    tics: Optional[list[Tic]]
    labels: Optional[list[str]]

    def validate(self):
        if not (self.bounds.lower < self.bounds.upper):
            raise ConfigValueError(self, "illegal bounds")
        if self.labels is not None \
        and len(self.labels) != (self.bounds.upper - self.bounds.lower + 1):
            raise ConfigValueError(self, "wrong number of labels")

    def is_scale(self):
        return self.bounds.lower == 0 and self.bounds.upper == 127

    def is_enum(self):
        return self.labels is not None


@dataclass
class Group:
    name: str
    long: str
    description: Optional[str]
    content: list[Setting]

    @property
    def scales(self):
        return list(filter(Setting.is_scale, self.content))

    @property
    def enums(self):
        return list(filter(Setting.is_enum, self.content))


def isgeneric(annot):
    return hasattr(annot, "__origin__") \
        and hasattr(annot, "__args__")


def construct(annot, json):
    """Construct an object from a given type from a JSON stream.

    The `annot` type should be one of: str, int, list[T], Optional[T],
    or a dataclass, and the JSON data should match exactly the given
    definitions in the dataclass hierarchy.
    """
    if annot is str:
        assert isinstance(json, str)
        return json
    if annot is int:
        assert isinstance(json, int)
        return json
    if isgeneric(annot) and typing.get_origin(annot) is list:
        assert isinstance(json, list)
        return [construct(typing.get_args(annot)[0], item) for item in json]
    if isgeneric(annot) and typing.get_origin(annot) is Union \
        and typing.get_args(annot)[1] is types.NoneType:
        if json is None:
            return None
        else:
            return construct(typing.get_args(annot)[0], json)
    if is_dataclass(annot):
        assert isinstance(json, dict)
        arg_annot = typing.get_type_hints(annot)
        assert all(k in json for k in arg_annot)
        args = { k: construct(v, json[k])
                 for k, v in arg_annot.items() }
        return annot(**args)


def read_settings():
    with resources.open_text(__package__, "messages.dhall") as inp:
        raw_data = dhall.load(inp)
    group_lst = construct(list[Group], raw_data)
    return { grp.name: grp for grp in group_lst }


def modulators(settings):
    labels = settings["modulators"].content[0].labels
    return ["Baseline"] + labels


if __name__ == "__main__":
    print(read_settings())
# ~\~ end
