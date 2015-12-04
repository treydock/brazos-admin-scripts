from decimal import Decimal
import re

def slurm_duration_to_sec(t, debug=False):
    # Format can be DD-HH:MM:SS or HH:MM:SS or MM:SS
    m = re.search(r"(([\d]+)?-)?([\d]+)?:?([\d]{2})\:([\d\.]+)", t)
    if debug: print "SLURM duration -> sec: %s -> %s" % (t, m.groups())
    sec = Decimal('0.0')
    if not m:
        return sec
    # Days - optional
    if m.group(2):
        sec += Decimal('86400.0') * Decimal(m.group(2))
    # Hours - optional
    if m.group(3):
        sec += Decimal('3600.0') * Decimal(m.group(3))
    # Minutes
    sec += Decimal('60.0') * Decimal(m.group(4))
    # Seconds
    sec += Decimal(m.group(5))

    return int(round(sec, 0))
