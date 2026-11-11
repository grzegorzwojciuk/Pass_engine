from pathlib import Path
from pass_engine.tle import load_tle
from pass_engine.orbit import position_teme

record = load_tle(Path("../../fixtures/satellite_synthetic.tle"))[0]
print(position_teme(record, record.epoch))