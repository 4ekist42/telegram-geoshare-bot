from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set


@dataclass
class ZoneNotifications:
    override: bool = False
    notify_on_enter: bool = False
    notify_on_exit: bool = False


@dataclass
class Zone:
    id: int
    type: str
    name: Optional[str]
    center_lat: float
    center_lng: float
    radius_m: float
    notifications: ZoneNotifications


@dataclass
class GlobalZoneConfig:
    secure_notify_exit: bool = True
    secure_notify_enter: bool = True
    danger_notify_exit: bool = True
    danger_notify_enter: bool = True


@dataclass
class TelegramGlobal:
    notify_location_start: bool = True
    notify_location_stop: bool = True
    notify_absent_enabled: bool = False
    notify_absent_minutes: int = 10
    send_current_location_with_alert: bool = False


@dataclass
class TelegramAdmin:
    id: int
    name: Optional[str]
    override: bool = False
    notify_location_start: bool = True
    notify_location_stop: bool = True
    notify_absent_enabled: bool = False
    notify_absent_minutes: int = 10
    send_current_location_with_alert: bool = False
    zones: List[int] = field(default_factory=list)


@dataclass
class TelegramAcceptFromUser:
    id: int
    name: Optional[str]


@dataclass
class TelegramAcceptFrom:
    mode: str = "any"
    users: List[TelegramAcceptFromUser] = field(default_factory=list)


@dataclass
class TelegramShowSender:
    show_name: bool = True
    show_id: bool = True


@dataclass
class TelegramConfig:
    global_cfg: TelegramGlobal
    admins: List[TelegramAdmin]
    accept_from: TelegramAcceptFrom
    show_sender: TelegramShowSender


@dataclass
class Config:
    zone_global: GlobalZoneConfig
    zones: List[Zone]
    zones_by_id: Dict[int, Zone]
    telegram: TelegramConfig


@dataclass
class UserState:
    last_lat: float
    last_lng: float
    last_time: datetime
    current_zone_ids: Set[int] = field(default_factory=set)