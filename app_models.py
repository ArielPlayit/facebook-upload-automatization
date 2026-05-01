from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GroupConfig:
    id: str
    message: str | None = None
    images: list[str] | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "GroupConfig":
        raw_images = data.get("images")
        parsed_images: list[str] | None = None
        if isinstance(raw_images, list):
            parsed_images = [str(path) for path in raw_images]

        return GroupConfig(
            id=str(data.get("id", "")).strip(),
            message=data.get("message"),
            images=parsed_images,
        )


@dataclass
class AccountConfig:
    name: str = "Cuenta principal"
    email: str | None = None
    password: str | None = None
    edge_profile_path: str | None = None
    default_message: str = ""
    limited_catalog_message: str | None = None
    default_images: list[str] = field(default_factory=list)
    randomize_images_order: bool = False
    groups: list[GroupConfig] = field(default_factory=list)
    debug_on_failure: bool = False
    force_close_edge_before_start: bool = True
    batch_size: int | None = None
    batch_delay_minutes: int | None = None
    limited_catalog_random_groups_count: int | None = None
    suspended: bool = False

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AccountConfig":
        return AccountConfig(
            name=str(data.get("name", "Cuenta principal")),
            email=data.get("email"),
            password=data.get("password"),
            edge_profile_path=data.get("edge_profile_path"),
            default_message=str(data.get("default_message", "")),
            limited_catalog_message=data.get("limited_catalog_message"),
            default_images=[str(path) for path in data.get("default_images", [])],
            randomize_images_order=bool(data.get("randomize_images_order", False)),
            groups=[GroupConfig.from_dict(item) for item in data.get("groups", [])],
            debug_on_failure=bool(data.get("debug_on_failure", False)),
            force_close_edge_before_start=bool(data.get("force_close_edge_before_start", True)),
            batch_size=data.get("batch_size"),
            batch_delay_minutes=data.get("batch_delay_minutes"),
            limited_catalog_random_groups_count=data.get("limited_catalog_random_groups_count"),
            suspended=bool(data.get("suspended", False)),
        )

    def to_legacy_dict(self) -> dict[str, Any]:
        legacy_groups: list[dict[str, Any]] = []

        for group in self.groups:
            group_id = str(group.id).strip()
            if not group_id:
                continue

            normalized: dict[str, Any] = {"id": group_id}
            if group.message is not None:
                normalized["message"] = group.message
            if group.images is not None:
                normalized["images"] = list(group.images)
            legacy_groups.append(normalized)

        return {
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "edge_profile_path": self.edge_profile_path,
            "default_message": self.default_message,
            "limited_catalog_message": self.limited_catalog_message,
            "default_images": list(self.default_images),
            "randomize_images_order": self.randomize_images_order,
            "groups": legacy_groups,
            "debug_on_failure": self.debug_on_failure,
            "force_close_edge_before_start": self.force_close_edge_before_start,
            "batch_size": self.batch_size,
            "batch_delay_minutes": self.batch_delay_minutes,
            "limited_catalog_random_groups_count": self.limited_catalog_random_groups_count,
            "suspended": self.suspended,
        }


@dataclass
class RuntimeConfig:
    accounts: list[AccountConfig]
