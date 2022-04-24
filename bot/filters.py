# filters.py | Macaulay Library filter representation functions
# Copyright (C) 2019-2021  EraserBird, person_v1.32, hmmm

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum
from typing import Any, Optional, Union, Dict, Tuple
from collections.abc import Iterable

# Macaulay Library URLs
CATALOG_URL = "https://search.macaulaylibrary.org/api/v2/search?sort=rating_rank_desc"


class MediaType(Enum):
    """Enum for media types."""

    IMAGE = "photo"
    SONG = "audio"

    def name(self):
        if self is MediaType.IMAGE:
            return "images"
        if self is MediaType.SONG:
            return "songs"
        return "INVALID"

    def types(self):
        valid_types = {
            "images": {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif"},
            "songs": {"audio/mpeg": "mp3", "audio/mpeg3": "mp3", "audio/wav": "wav"},
        }

        if self is MediaType.IMAGE:
            return valid_types["images"]
        if self is MediaType.SONG:
            return valid_types["songs"]
        return {}

    @classmethod
    def content_type_lookup(cls, content_type: str) -> Optional[str]:
        for media in cls:
            for content, ext in media.types().items():
                if content_type == content:
                    return ext
        return None


class Filter:
    _boolean_options = ("large", "bw", "vc")
    _default_options: Dict[str, Any] = {}

    def __init__(
        self,
        age: Union[str, Iterable] = (),
        sex: Union[str, Iterable] = (),
        behavior: Union[str, Iterable] = (),
        sounds: Union[str, Iterable] = (),
        tags: Union[str, Iterable] = (),
        captive: Union[str, Iterable] = (),
        quality: Union[str, Iterable] = (),
        large: bool = False,
        bw: bool = False,
        vc: bool = False,
    ):
        """Represents Macaulay Library media filters.

        Valid filters:
        - Age:
            - adult, immature, juvenile, unknown
        - Sex:
            - male, female, unknown
        - Behavior:
            - carrying_fecal_sac, carrying_food, courtship_display_or_copulation,
            - feeding_young, flying_flight, foraging_eating, molting
            - nest_building, preening, vocalizing
        - Sounds:
            - song, call, non_vocal, dawn_song, flight_song
            - flight_call, duet, environmental, people
        - Photo Tags:
            - multiple_species, in_hand, nest, egg, habitat
            - watermark, back_of_camera, dead
            - field_notes_sketch, non_bird
        - Captive (animals in captivity):
            - incl (including), only
        - Quality:
            - 0 (unrated), 1 (worst) - 5 (best)
        - Large:
            - True (uses previewUrl), False (uses mediaUrl)
        - Black & White:
            - True (black and white), False (color)
        - Voice Channel:
            - True (send songs in voice), False (send songs as files)
        """
        self.age = age
        self.sex = sex
        self.behavior = behavior
        self.sounds = sounds
        self.tags = tags
        self.captive = captive
        self.quality = quality
        self.large = large
        self.bw = bw
        self.vc = vc

        for item in self.__dict__.items():
            if isinstance(item[1], str):
                cleaned = set(item[1].split(" "))
                cleaned.discard("")
                self.__dict__[item[0]] = cleaned
            elif isinstance(item[1], Iterable):
                cleaned = set(item[1])
                cleaned.discard("")
                self.__dict__[item[0]] = cleaned
        self._validate()

    def __repr__(self):
        return self.__dict__.__repr__()

    def _clear(self):
        """Clear all filters."""
        self.__dict__ = {
            k: (False if k in self._boolean_options else set())
            for k in self.__dict__.keys()
        }

    def _validate(self) -> bool:
        """Check the validity of Filter values.

        Return True if Filter values are valid.
        Raises a ValueError if Filter values are invalid.
        Raises a TypeError if values are not iterables.
        """
        valid_values = {
            "age": {"adult", "immature", "juvenile", "unknown"},
            "sex": {"male", "female", "unknown"},
            "sounds": {
                "song",
                "call",
                "non_vocal",
                "flight_call",
                "flight_song",
                "dawn_song",
                "duet",
                "environmental",
                "people",
            },
            "behavior": {
                "carrying_fecal_sac",
                "carrying_food",
                "courtship_display_or_copulation",
                "feeding_young",
                "flying_flight",
                "foraging_eating",
                "molting",
                "nest_building",
                "preening",
                "vocalizing",
            },
            "tags": {
                "back_of_camera",
                "dead",
                "egg",
                "field_notes_sketch",
                "habitat",
                "in_hand",
                "multiple_species",
                "nest",
                "non_bird",
                "watermark",
            },
            "captive": {"incl", "only"},
            "quality": {"0", "1", "2", "3", "4", "5"},
        }
        for item in self.__dict__.items():
            if item[0] in self._boolean_options:
                if not isinstance(item[1], bool):
                    raise TypeError(f"{item[0]} is not a boolean.")
                continue
            if not isinstance(item[1], Iterable):
                raise TypeError(f"{item[0]} is not an iterable.")
            if not set(item[1]).issubset(valid_values[item[0]]):
                raise ValueError(f"{item[1]} contains invalid {item[0]} values.")
        return True

    def url(
        self, taxon_code: str, media_type: MediaType, count: int, cursor: str = ""
    ) -> str:
        """Generate the search url based on the filters.

        `media_type` is photo, audio, video
        """
        self._validate()
        url_parameter_names = {
            "age": "&age={}",
            "sex": "&sex={}",
            "sounds": "&tag={}",
            "behavior": "&tag={}",
            "tags": "&tag={}",
            "captive": "&captive={}",
            "quality": "&quality={}",
        }
        url = [CATALOG_URL]
        url.append(
            f"&taxonCode={taxon_code}&mediaType={media_type.value}&count={count}&initialCursorMark={cursor}"
        )

        for item in self.__dict__.items():
            if (
                (item[0] == "sounds" and media_type is MediaType.IMAGE)
                or (item[0] == "tags" and media_type is MediaType.SONG)
                or item[0] in self._boolean_options
            ):
                # disable invalid filters on certain media types
                continue
            for value in item[1]:
                url.append(url_parameter_names[item[0]].format(value))
        return "".join(url)

    def to_int(self):
        """Convert filters into an integer representation.

        This is calculated with a 48 digit binary number representing the 48 filter options.
        """
        out = ["0"] * 48
        indexes = self.aliases(num=True)
        for title, filters in self.__dict__.items():
            if title in self._boolean_options:
                if filters:
                    out[indexes[title][filters] - 1] = "1"
                continue
            for name in filters:
                out[indexes[title][name] - 1] = "1"
        return int("".join(reversed(out)), 2)

    @classmethod
    def from_int(cls, number: int):
        """Convert an int to a filter object."""
        if number >= 2 ** 48 or number < 0:
            raise ValueError("Input number out of bounds.")
        me = cls()

        me._clear()  # reset existing filters to empty
        binary = reversed("{0:0>48b}".format(number))
        lookup = me.aliases(lookup=True)
        for index, value in enumerate(binary):
            if int(value):
                key = lookup[str(index + 1)]
                if key[0] in me._boolean_options:
                    me.__dict__[key[0]] = key[1]
                    continue
                me.__dict__[key[0]].add(key[1])
        return me

    def __xor__(self, other):
        return self.xor(other)

    def xor(self, other):
        """Combine/toggle filters by xor-ing the integer representations."""
        if isinstance(other, self.__class__):
            other = other.to_int()
        if other >= 2 ** 48 or other < 0:
            raise ValueError("Input number out of bounds.")
        return self.from_int(other ^ self.to_int())

    @classmethod
    def parse(cls, args: str, defaults: bool = True, use_numbers: bool = True):
        """Parse an argument string as Macaulay Library media filters."""
        me = cls()
        me._clear()  # reset existing filters to empty
        lookup = me.aliases(lookup=True)
        if not use_numbers:
            lookup = {k: i for k, i in lookup.items() if not k.isdecimal()}
        args = args.lower().strip()
        if "," in args:
            inputs = map(lambda x: x.strip(), args.split(","))
        else:
            inputs = map(lambda x: x.strip(), args.split(" "))

        for arg in inputs:
            key = lookup.get(arg)
            if key is not None:
                if key[0] in me._boolean_options:
                    me.__dict__[key[0]] = key[1]
                    continue
                me.__dict__[key[0]].add(key[1])
        if defaults:
            for key in me._default_options:
                if not me.__dict__[key]:
                    me.__dict__[key] = me._default_options[key]
                elif me.__dict__[key] == me._default_options[key]:
                    me ^= me.__class__()
        return me

    def display(self):
        """Return a list describing the filters."""
        output = []
        display = self.aliases(display_lookup=True)
        for title, values in self.__dict__.items():
            if title in self._boolean_options:
                if values:
                    output.append(f"{title}: {display[title][1][values]}")
                continue
            for name in values:
                output.append(f"{title}: {display[title][1][name]}")
        if not output:
            output.append("None")
        return output

    @staticmethod
    def aliases(lookup: bool = False, num: bool = False, display_lookup: bool = False):
        """Generate filter alises.

        If lookup, returns a dict mapping aliases to filter names,
        elif num, returns a dict mapping filter names to numbers,
        elif display_lookup, returns a dict mapping internal names to display names,
        else returns a display text.
        """
        # the keys of this dict are in the form ("display text", "internal key")
        # the first alias should be a number
        aliases: Dict[
            Tuple[str, str], Dict[Tuple[str, Union[str, bool]], Tuple[str, ...]]
        ] = {
            ("age", "age"): {
                ("adult", "adult"): ("1", "adult", "a"),
                ("immature", "immature"): ("2", "immature", "im"),
                ("juvenile", "juvenile"): ("3", "juvenile", "j"),
                ("unknown", "unknown"): ("4", "age:unknown", "unknown age"),
            },
            ("sex", "sex"): {
                ("male", "male"): ("5", "male", "m"),
                ("female", "female"): ("6", "female", "f"),
                ("unknown", "unknown"): ("7", "sex:unknown", "unknown sex"),
            },
            ("behavior", "behavior"): {
                ("eating/foraging", "foraging_eating"): (
                    "8",
                    "eating",
                    "foraging",
                    "e",
                    "ef",
                ),
                ("flying", "flying_flight"): ("9", "flying", "fly"),
                ("preening", "preening"): ("10", "preening", "p"),
                ("vocalizing", "vocalizing"): ("11", "vocalizing", "vo"),
                ("molting", "molting"): ("12", "molting", "mo"),
                (
                    "courtship, display, or copulation",
                    "courtship_display_or_copulation",
                ): (
                    "13",
                    "courtship",
                    "display",
                    "copulation",
                    "cdc",
                ),
                ("feeding young", "feeding_young"): (
                    "14",
                    "feeding",
                    "feeding young",
                    "fy",
                ),
                ("carrying food", "carrying_food"): (
                    "15",
                    "food",
                    "carrying food",
                    "cf",
                ),
                ("carrying fecal sac", "carrying_fecal_sac"): (
                    "16",
                    "fecal",
                    "carrying fecal sac",
                    "fecal sac",
                    "cfs",
                ),
                ("nest building", "nest_building"): (
                    "17",
                    "nest",
                    "building",
                    "nest building",
                    "nb",
                ),
            },
            ("sounds", "sounds"): {
                ("song", "song"): ("18", "song", "so"),
                ("call", "call"): ("19", "call", "c"),
                ("non-vocal", "non_vocal"): ("20", "non-vocal", "non vocal", "nv"),
                ("dawn song", "dawn_song"): ("21", "dawn", "dawn song", "ds"),
                ("flight song", "flight_song"): ("22", "flight song", "fs"),
                ("flight call", "flight_call"): ("23", "flight call", "fc"),
                ("duet", "duet"): ("24", "duet", "dt"),
                ("environmental", "environmental"): ("25", "environmental", "env"),
                ("people", "people"): ("26", "people", "peo"),
            },
            ("photo tags", "tags"): {
                ("multiple species", "multiple_species"): (
                    "27",
                    "multiple",
                    "species",
                    "multiple species",
                    "mul",
                ),
                ("in-hand", "in_hand"): ("28", "in-hand", "in hand", "in"),
                ("nest", "nest"): ("29", "nest", "nes"),
                ("eggs", "egg"): ("30", "egg", "eggs"),
                ("habitat", "habitat"): ("31", "habitat", "hab"),
                ("watermark", "watermark"): ("32", "watermark", "wat"),
                ("back of camera", "back_of_camera"): (
                    "33",
                    "back of camera",
                    "camera",
                    "back",
                    "bac",
                ),
                ("dead", "dead"): ("34", "dead", "dea"),
                ("field notes/sketch", "field_notes_sketch"): (
                    "35",
                    "field",
                    "field notes",
                    "sketch",
                ),
                ("no bird", "non_bird"): ("36", "none", "no bird", "non"),
            },
            ("captive (animals in captivity)", "captive"): {
                ("all", "incl"): ("37", "captive:all"),
                ("yes", "only"): ("38", "captive"),
                # ("no", "no"): ("39", "captive:no", "not captive"),
            },
            ("quality", "quality"): {
                ("no rating", "0"): ("40", "no rating", "q0"),
                ("terrible", "1"): ("41", "terrible", "q1"),
                ("poor", "2"): ("42", "poor", "q2"),
                ("average", "3"): ("43", "average", "avg", "q3"),
                ("good", "4"): ("44", "good", "q4"),
                ("excellent", "5"): ("45", "excellent", "best", "q5"),
            },
            ("larger images (defaults to no)", "large"): {
                ("yes", True): ("46", "large", "larger images"),
            },
            ("black & white (defaults to no)", "bw"): {
                ("yes", True): ("47", "bw", "b&w"),
            },
            ("voice channel (defaults to no) (RACES ONLY)", "vc"): {
                ("yes", True): ("48", "vc", "voice", "voice channel"),
            },
        }
        if lookup:
            return {
                alias: (title[1], name[1])
                for title, subdict in aliases.items()
                for name, alias_tuple in subdict.items()
                for alias in alias_tuple
            }
        if num:
            return {
                title[1]: {name[1]: int(alias[0]) for name, alias in subdict.items()}
                for title, subdict in aliases.items()
            }
        if display_lookup:
            return {
                title[1]: (title[0], {key[1]: key[0] for key in subdict.keys()})
                for title, subdict in aliases.items()
            }

        return {
            title[0]: {name[0]: alias for name, alias in subdict.items()}
            for title, subdict in aliases.items()
        }
