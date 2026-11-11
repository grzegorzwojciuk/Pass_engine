from sgp4.api import Satrec, jday
import numpy as np
from math import tau, atan2
from datetime import datetime
from .models import TleRecord
from .models import Observer


def position_satellite_teme(record: TleRecord, t: datetime) -> tuple[float, float, float]:
    satellite = Satrec.twoline2rv(record.line1, record.line2)
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
    e, r, v = satellite.sgp4(jd, fr)
    if e != 0:
        raise RuntimeError(f"SGP4 propagation failed for satellite {record.satellite_number} at {t} (SGP4 code {e}).")
    return r

def position_observer_ecef(observer: Observer) -> tuple[float, float, float]:
    lat_deg = observer.lat_deg
    lon_deg = observer.lon_deg
    alt_m = observer.alt_m
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    a = 6378137.0
    f = 1/298.257223563
    e2 = f * (2 - f)
    n = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
    x = (n + alt_m) * np.cos(lat_rad) * np.cos(lon_rad)
    y = (n + alt_m) * np.cos(lat_rad) * np.sin(lon_rad)
    z = (n * (1 - e2) + alt_m) * np.sin(lat_rad)
    return x, y, z


def gmst_from_utc(t: datetime) -> float:
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
    days_utc = (jd - 2451545.0) + fr
    T = days_utc / 36525.0

    sidereal_seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * T
        + 0.093104 * T**2
        - 6.2e-6 * T**3
    )
    return tau * (sidereal_seconds % 86400.0) / 86400.0
    

def position_observer_teme(observer: Observer, t: datetime) -> np.ndarray:
    x_ecef, y_ecef, z_ecef = position_observer_ecef(observer)
    r_obs_ecef = np.array([x_ecef/1000.0,
                           y_ecef/1000.0,
                           z_ecef/1000.0])
    theta = gmst_from_utc(t)
    revolving_earth = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    return revolving_earth @  r_obs_ecef 

def position_satellite_teme_shifted_normalized(record: TleRecord, t: datetime, observer: Observer) -> np.ndarray:
    r_satellite_teme = np.array(position_satellite_teme(record, t))
    r_satellite_teme_shifted = r_satellite_teme - position_observer_teme(observer, t)
    return r_satellite_teme_shifted / np.linalg.norm(r_satellite_teme_shifted)

def zenith_vector_teme(observer: Observer, t: datetime) -> np.ndarray:
    lat_deg = observer.lat_deg
    lon_deg = observer.lon_deg
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    into_teme = gmst_from_utc(t)
    return np.array([np.cos(lat_rad) * np.cos(lon_rad + into_teme),
                     np.cos(lat_rad) * np.sin(lon_rad + into_teme),
                     np.sin(lat_rad)])

def elevation(record: TleRecord, t: datetime, observer: Observer) -> float:
    sin_elev = np.dot(zenith_vector_teme(observer, t), position_satellite_teme_shifted_normalized(record, t, observer))
    sin_elev = np.clip(sin_elev, -1.0, 1.0)
    return np.degrees(np.arcsin(sin_elev))

def north_teme(t: datetime, observer: Observer) -> np.ndarray:
    lat_deg = observer.lat_deg
    lon_deg = observer.lon_deg
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    into_teme = gmst_from_utc(t)
    return np.array([-np.sin(lat_rad) * np.cos(lon_rad + into_teme),
                     -np.sin(lat_rad) * np.sin(lon_rad + into_teme),
                     np.cos(lat_rad)])

def east_teme(t: datetime, observer: Observer) -> np.ndarray:
    lon_deg = observer.lon_deg
    lon_rad = np.radians(lon_deg)
    into_teme = gmst_from_utc(t)
    return np.array([-np.sin(lon_rad + into_teme),
                     np.cos(lon_rad + into_teme),
                     0])

def azimuth(record: TleRecord, t: datetime, observer: Observer) -> float:
    satellite = position_satellite_teme_shifted_normalized(record, t, observer)
    n = np.dot(north_teme(t, observer), satellite)
    e = np.dot(east_teme(t, observer), satellite)
    az_deg = np.degrees(atan2(e, n)) % 360.0
    return 0.0 if az_deg == 360.00 else az_deg
