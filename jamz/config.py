from dataclasses import dataclass


@dataclass
class Config:
    path_template: str
    album_overrides: dict[str, str]
    template_overrides: dict[str, str]
