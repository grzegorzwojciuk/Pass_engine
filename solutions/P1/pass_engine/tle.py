import calendar
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import TleRecord

class TleError(ValueError):
    pass

def if_name(tested_line: str) -> bool:
    if len(tested_line.strip()) < 25:
        return True
    else:
        return False

def if_first(tested_line: str) -> bool:
    tested_line = tested_line.rstrip(" ")
    if len(tested_line) == 69 and tested_line.startswith("1 "):
        return True
    else:
        return False

def if_second(tested_line: str) -> bool:
    tested_line = tested_line.rstrip(" ")
    if len(tested_line) == 69 and tested_line.startswith("2 "):
        return True
    else:
        return False

def parse_tle(text: str) -> list[TleRecord]:
    lines = text.splitlines()

    line_numbers = []
    for i in range(len(lines)):
        line_numbers.append(i+1)

    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if line.startswith("#") or line.strip() == "":
            del lines[i]
            del line_numbers[i]

    '''SPRAWDZANIE'''

    if not lines:
        raise TleError("No TLE records found in the file.")

    if (if_name(lines[0]) == False and if_first(lines[0]) == False):
        raise TleError(f"Expected name line or first line in line {line_numbers[0]}.")

    if (if_second(lines[-1]) == False):
        raise TleError(f"Expected second line in line {line_numbers[-1]}.")

    for i in range(len(lines) - 1):
        line = lines[i]
        if (if_name(line)== True and if_first(lines[i+1]) == False):
            raise TleError(f"Expected first line after name line in line {line_numbers[i+1]}.")
        if (if_first(line)== True and if_second(lines[i+1]) == False):
            raise TleError(f"Expected second line after first line in line {line_numbers[i+1]}.")
        if (if_second(line)== True and (if_first(lines[i+1]) == False and if_name(lines[i+1]) == False)):
            raise TleError(f"Expected name line or first line after second line in line {line_numbers[i+1]}.")
        
    '''DZIELENIE TLE'''

    tle_list = []
    for i in range(len(lines)):
        if (if_second(lines[i]) == True):
            if (if_name(lines[i-2]) == True and lines[i-1][2:7] == lines[i][2:7]):
                tle_list.append([lines[i-2], lines[i-1], lines[i]])
            elif (if_name(lines[i-2]) == False and lines[i-1][2:7] == lines[i][2:7]):
                tle_list.append([None, lines[i-1], lines[i]])
            else:
                raise TleError(f"Satellite number mismatch between lines {line_numbers[i-1]} and {line_numbers[i]}.")

    '''SPRAWDZANIE TLE CHECKSUM I KONIECZNYCH SPACJI'''

    for i in range(len(tle_list)):
        for j in range(1, 3):
            line = tle_list[i][j].strip()
            if j == 1:
                for k in [8, 17, 32, 43, 52, 61, 63]:
                    if line[k] != " ":
                        raise TleError(f"Expected a space in column {k + 1} of line {j}, TLE {i + 1}.")
                bstar = line[53:61]
                if bstar.strip(" "):
                    if bstar[0] not in ["+", "-", " "]:
                        raise TleError(f"Invalid B* drag term in line {j} of TLE {i + 1}.")
                    elif any(c not in "0123456789" for c in bstar[1:6]):
                        raise TleError(f"Invalid B* drag term in line {j} of TLE {i + 1}.")
                    elif bstar[6] not in ["+", "-"]:
                        raise TleError(f"Invalid B* drag term in line {j} of TLE {i + 1}.")
                    elif bstar[7] not in "0123456789":
                        raise TleError(f"Invalid B* drag term in line {j} of TLE {i + 1}.")
            else:
                for k in [7, 16, 25, 33, 42, 51]:
                    if line[k] != " ":
                        raise TleError(f"Expected a space in column {k + 1} of line {j}, TLE {i + 1}.")
            calculated_checksum = sum(int(c) if c in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"] else 1 if c == "-" else 0 for c in line[:-1]) % 10

            if line[-1] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                checksum = int(line[-1])
            else:
                raise TleError(f"Invalid checksum in line {j} of TLE {i+1} (checksum is not a digit). Calculated checksum: {calculated_checksum}, got {line[-1]}.")
            if checksum != calculated_checksum:
                raise TleError(f"Checksum mismatch in line {j} of TLE {i+1}. Expected {calculated_checksum}, got {checksum}.")

    '''PRZYPISANIE WARTOŚCI PARAMETRÓW'''

    records = []

    for i in range(len(tle_list)):
        name = tle_list[i][0].strip() if tle_list[i][0] is not None else None
        line1 = tle_list[i][1].strip()
        line2 = tle_list[i][2].strip()
        check_satellite_number = line1[2:7]
        if(check_satellite_number.strip() != check_satellite_number.lstrip()):
            raise TleError(f"Satellite number in line 1 of TLE {i+1} ends with whitespace.")
        elif not check_satellite_number.lstrip(" "):
            raise TleError(f"Satellite number in line 1 of TLE {i+1} is empty.")
        elif any(c not in "0123456789" for c in check_satellite_number.lstrip(" ")):
            raise TleError(f"Satellite number in line 1 of TLE {i+1} contains non-digit characters.")
        else:
            satellite_number = int(line1[2:7])

        check_classification = line1[7]
        if(check_classification not in ["U", "C", "S"]):
            raise TleError(f"Classification in line 1 of TLE {i+1} is invalid.")
        else:
            classification = line1[7]

        check_epoch = line1[18:32]
        digits = check_epoch[:5] + check_epoch[6:]
        if any(c not in "0123456789" for c in digits):
            raise TleError(f"Epoch in line 1 of TLE {i+1} contains non-digit characters.")
        elif check_epoch[5] != ".":
            raise TleError(f"Epoch in line 1 of TLE {i+1} is missing decimal point.")
        else:
            year_short = int(line1[18:20])
            year = (1900 if year_short >= 57 else 2000) + year_short
            day_of_year = float(line1[20:32])
            max_day = 366 if calendar.isleap(year) else 365
        if int(check_epoch[2:5]) > max_day:
            raise TleError(f"Epoch in line 1 of TLE {i+1} has invalid day of year.")
        else:
            epoch = datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=day_of_year - 1)

        check_inclination_deg = line2[8:16]
        if check_inclination_deg[3] != "." or any(c not in "0123456789" for c in check_inclination_deg[:3].lstrip(" ") +check_inclination_deg[4:]) or not check_inclination_deg[:3].strip(" "):
            raise TleError(f"Inclination in line 2 of TLE {i+1} is invalid.")
        elif float(check_inclination_deg) < 0 or float(check_inclination_deg) > 180:
            raise TleError(f"Inclination in line 2 of TLE {i+1} is out of range.")
        else:
            inclination_deg = float(line2[8:16])


        check_raan_deg = line2[17:25]
        if check_raan_deg[3] != "." or any(c not in "0123456789" for c in check_raan_deg[:3].lstrip(" ") +check_raan_deg[4:]) or not check_raan_deg[:3].strip(" "):
            raise TleError(f"RAAN in line 2 of TLE {i+1} is invalid.")
        elif float(check_raan_deg) < 0 or float(check_raan_deg) > 360:
            raise TleError(f"RAAN in line 2 of TLE {i+1} is out of range.")
        else:
            raan_deg = float(line2[17:25])


        check_eccentricity = line2[26:33]
        if any(c not in "0123456789" for c in check_eccentricity):
            raise TleError(f"Eccentricity in line 2 of TLE {i+1} is invalid.")
        else:
            eccentricity = float("0." + line2[26:33])

        check_arg_perigee_deg = line2[34:42]
        if check_arg_perigee_deg[3] != "." or any(c not in "0123456789" for c in check_arg_perigee_deg[:3].lstrip(" ") +check_arg_perigee_deg[4:]) or not check_arg_perigee_deg[:3].strip(" "):
            raise TleError(f"Argument of perigee in line 2 of TLE {i+1} is invalid.")
        elif float(check_arg_perigee_deg) < 0 or float(check_arg_perigee_deg) > 360:
            raise TleError(f"Argument of perigee in line 2 of TLE {i+1} is out of range.")
        else:
            arg_perigee_deg = float(line2[34:42])

        check_mean_anomaly_deg = line2[43:51]
        if check_mean_anomaly_deg[3] != "." or any(c not in "0123456789" for c in check_mean_anomaly_deg[:3].lstrip(" ") +check_mean_anomaly_deg[4:]) or not check_mean_anomaly_deg[:3].strip(" "):
            raise TleError(f"Mean anomaly in line 2 of TLE {i+1} is invalid.")
        elif float(check_mean_anomaly_deg) < 0 or float(check_mean_anomaly_deg) > 360:
            raise TleError(f"Mean anomaly in line 2 of TLE {i+1} is out of range.")
        else:
            mean_anomaly_deg = float(line2[43:51])
        
        check_mean_motion_rev_per_day = line2[52:63]
        if check_mean_motion_rev_per_day[2] != "." or any(c not in "0123456789" for c in check_mean_motion_rev_per_day[:2].lstrip(" ") +check_mean_motion_rev_per_day[3:]) or not check_mean_motion_rev_per_day[:2].strip(" "):
            raise TleError(f"Mean motion in line 2 of TLE {i+1} is invalid.")
        elif float(check_mean_motion_rev_per_day) <= 0:
            raise TleError(f"Mean motion in line 2 of TLE {i+1} is out of range.")
        else:
            mean_motion_rev_per_day = float(line2[52:63])

        check_revolution_number = line2[63:68]
        if(check_revolution_number.strip() != check_revolution_number.lstrip()):
            raise TleError(f"Revolution number in line 2 of TLE {i+1} ends with whitespace.")
        elif not check_revolution_number.lstrip(" "):
            raise TleError(f"Revolution number in line 2 of TLE {i+1} is empty.")
        elif any(c not in "0123456789" for c in check_revolution_number.lstrip(" ")):
            raise TleError(f"Revolution number in line 2 of TLE {i+1} contains non-digit characters.")
        else:
            revolution_number = int(line2[63:68])

        record = TleRecord(
            name=name,
            line1=line1,
            line2=line2,
            epoch=epoch,
            satellite_number=satellite_number,
            classification=classification,
            inclination_deg=inclination_deg,
            raan_deg=raan_deg,
            eccentricity=eccentricity,
            arg_perigee_deg=arg_perigee_deg,
            mean_anomaly_deg=mean_anomaly_deg,
            mean_motion_rev_per_day=mean_motion_rev_per_day,
            revolution_number=revolution_number
        )
        records.append(record)
    return records

def load_tle(path: Path) -> list[TleRecord]:
    text = path.read_text(encoding="utf-8-sig")
    return parse_tle(text)