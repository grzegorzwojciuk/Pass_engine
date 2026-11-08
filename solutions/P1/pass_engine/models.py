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