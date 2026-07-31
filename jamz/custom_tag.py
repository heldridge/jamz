from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import pathvalidate
from config import Config


class TagCreator(ABC):
    @abstractmethod
    def make_tag(
        self,
        filepath: Path,
        tags: dict[str, str],
        config: Config,
    ) -> str | None:
        pass


class Normalizer(TagCreator):
    def __init__(self, possible_tag_names: list[str]):
        self.possible_tag_names = possible_tag_names

    def make_tag(
        self,
        filepath: Path,
        tags: dict[str, str],
        config: Config,
    ) -> str | None:
        for ptn in self.possible_tag_names:
            if (val := tags.get(ptn)) is not None:
                return val


class Sanitizer(TagCreator):
    def __init__(self, target: str):
        self.target = target

    def make_tag(
        self,
        filepath: Path,
        tags: dict[str, str],
        config: Config,
    ) -> str | None:
        if (source_val := tags.get(self.target)) is not None:
            return pathvalidate.sanitize_filename(source_val)


class JamzPaddedTracknumber(TagCreator):
    @staticmethod
    def _get_tn(tags: dict[str, str]) -> str | None:
        if "TRCK" in tags:
            return str(tags["TRCK"]).split("/")[0]
        if "tracknumber" in tags:
            return tags["tracknumber"]
        if "trkn" in tags:
            return str(tags["trkn"][0])

    def make_tag(
        self,
        filepath: Path,
        tags: dict[str, str],
        config: Config,
    ) -> str | None:
        if (tn := self._get_tn(tags)) is not None:
            return tn.zfill(2)


class JamzOriginalSuffix(TagCreator):
    def make_tag(
        self,
        filepath: Path,
        tags: dict[str, str],
        config: Config,
    ) -> str:

        return filepath.suffix


class JamzAlbum(TagCreator):
    def __init__(self):
        self.fallback = Normalizer(["album", "TALB", "©alb"])

    def make_tag(
        self, filepath: Path, tags: dict[str, str], config: Config,
    ) -> str | None:
        if (albumid := tags.get("jamz_musicbrainz_albumid")) is not None:
            if (override_value := config.album_overrides.get(albumid)) is not None:
                return override_value
        return self.fallback.make_tag(filepath, tags, config)


class JamzDiscnumber(TagCreator):
    @staticmethod
    def _clean_disk_number(value: str) -> str | None:
        """Turn '3/12' or '3' into the int 3."""
        value = str(value)
        head = value.split("/")[0].strip()
        return head if head.isdigit() else None

    def make_tag(
        self, filepath: Path, tags: dict[str, str], config: Config,
    ) -> str | None:
        for ptn in ["TPOS", "discnumber"]:
            if (dirty_dn := tags.get(ptn)) is not None:
                if (clean_dn := self._clean_disk_number(dirty_dn)) is not None:
                    return clean_dn


@dataclass
class CustomTag:
    name: str
    creator: TagCreator


default_custom_tags: list[CustomTag] = [
    CustomTag("jamz_original_suffix", JamzOriginalSuffix()),
    CustomTag("jamz_albumartist", Normalizer(["albumartist", "TPE2", "aART"])),
    CustomTag("jamz_title", Normalizer(["title", "TIT2", "©nam"])),
    CustomTag(
        "jamz_musicbrainz_albumid",
        Normalizer(["musicbrainz_albumid", "TXXX:MusicBrainz Album Id"]),
    ),
    CustomTag("jamz_padded_tracknumber", JamzPaddedTracknumber()),
    CustomTag("jamz_album", JamzAlbum()),
    CustomTag("jamz_discnumber", JamzDiscnumber()),
] + [
    CustomTag(f"jamz_sanitized_{t}", Sanitizer(f"jamz_{t}"))
    for t in ["albumartist", "title", "album"]
]
