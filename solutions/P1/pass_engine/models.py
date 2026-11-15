from dataclasses import dataclass
from datetime import datetime

@dataclass
class TleRecord:
    name: str | None
    line1: str
    line2: str
    satellite_number: int
    classification: str
    epoch: datetime
    inclination_deg: float
    raan_deg: float
    eccentricity: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    mean_motion_rev_per_day: float
    revolution_number: int

@dataclass(frozen=True)
class Observer:
    lat_deg: float
    lon_deg: float
    alt_m: float = 0.0
    min_elev_deg: float = 10.0

@dataclass(frozen=True)
class Pass:
    satellite: str
    aos: datetime          # aware UTC
    los: datetime          # aware UTC
    max_elev_deg: float
    max_elev_time: datetime
    az_aos_deg: float
    az_los_deg: float
    duration_s: float