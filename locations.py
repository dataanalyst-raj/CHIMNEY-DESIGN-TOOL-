"""
Location-based auto-fill data: basic wind speed (IS 875 Part 3:2015
Annex A) and seismic zone factor (IS 1893 Part 1:2016 Table 3) by city.

SOURCE & VERIFICATION STATUS (updated 15 Jul 2026):

  WIND SPEED (Vb) - all 79 cities below are transcribed directly from
  the user's own physical copy of IS 875 (Part 3):2015, Annex A
  ("Basic Wind Speed at 10m Height for Some Important Cities/Towns").
  This is the PRIMARY SOURCE, not a third-party aggregator - the
  highest confidence level this table has had.

  This replaced an earlier version sourced from third-party web
  aggregators, which contained real, confirmed errors:
    - Almora: was 39, correct is 47
    - Amritsar: was 50, correct is 47
    - Bahraich: was 50, correct is 47
    - Bareilly: was 50, correct is 47
    - Bhilai: was 44, correct is 39
    - Bhopal: was 39 (original), briefly "corrected" to 47 based on a
      web source that turned out to be WRONG - the book confirms the
      original 39 was correct all along. Reverted.
    - Chandigarh: was 39, correct is 47
    - Dehradun: was 39, correct is 47
    - Jaipur: was 39, correct is 47
    - Jodhpur: was 39, correct is 47
  This is a good illustration of why this whole table needed a primary
  source rather than aggregator cross-referencing - 10 of ~48 entries
  were wrong, a ~20% error rate, before this correction.

  SEISMIC ZONE (Z) - still sourced separately from a third-party
  reference (standard IS 1893 Table 3 scale: II=0.10, III=0.16,
  IV=0.24, V=0.36), NOT yet verified against a primary IS 1893 source.
  Only cities that were already in the tool before this update have
  seismic data; the ~40 newly-added cities show zone/z = None (wind
  speed auto-fills, seismic needs manual entry) until seismic data
  gets the same primary-source treatment wind speed just got.

  NOTE: the standard Z values above do NOT match the Kurkumbh
  reference design's own printed Z=0.20 for "Seismic Zone 3" - that
  specific discrepancy remains UNRESOLVED. Kurkumbh isn't in this
  city list, so it doesn't conflict with anything already validated,
  but verify against a primary IS 1893 source for any real design.

Only Vb and Z are auto-filled (the two location-dependent values that
actually feed live calculations). Terrain category is NOT auto-set
from city choice - it depends on the specific site's surroundings,
not just which city it's in, and needs engineering judgement either way.
"""

LOCATIONS = {
    "Agra":             {"vb": 47.0, "zone": None, "z": None},
    "Ahmedabad":        {"vb": 39.0, "zone": "III", "z": 0.16},
    "Ajmer":            {"vb": 47.0, "zone": None, "z": None},
    "Almora":           {"vb": 47.0, "zone": None, "z": None},
    "Amritsar":         {"vb": 47.0, "zone": None, "z": None},
    "Asansol":          {"vb": 47.0, "zone": None, "z": None},
    "Aurangabad":       {"vb": 39.0, "zone": None, "z": None},
    "Bahraich":         {"vb": 47.0, "zone": None, "z": None},
    "Barauni":          {"vb": 47.0, "zone": None, "z": None},
    "Bareilly":         {"vb": 47.0, "zone": None, "z": None},
    "Bengaluru":        {"vb": 33.0, "zone": "II",  "z": 0.10},
    "Bhatinda":         {"vb": 47.0, "zone": None, "z": None},
    "Bhilai":           {"vb": 39.0, "zone": None, "z": None},
    "Bhopal":           {"vb": 39.0, "zone": "II",  "z": 0.10},
    "Bhubaneshwar":     {"vb": 50.0, "zone": "III", "z": 0.16},
    "Bhuj":             {"vb": 50.0, "zone": None, "z": None},
    "Bikaner":          {"vb": 47.0, "zone": None, "z": None},
    "Bokaro":           {"vb": 47.0, "zone": None, "z": None},
    "Chandigarh":       {"vb": 47.0, "zone": "IV",  "z": 0.24},
    "Chennai":          {"vb": 50.0, "zone": "III", "z": 0.16},
    "Coimbatore":       {"vb": 39.0, "zone": "III", "z": 0.16},
    "Cuttack":          {"vb": 50.0, "zone": None, "z": None},
    "Darbhanga":        {"vb": 55.0, "zone": None, "z": None},
    "Darjeeling":       {"vb": 47.0, "zone": None, "z": None},
    "Dehradun":         {"vb": 47.0, "zone": "IV",  "z": 0.24},
    "Delhi":            {"vb": 47.0, "zone": "IV",  "z": 0.24},
    "Durgapur":         {"vb": 47.0, "zone": None, "z": None},
    "Gangtok":          {"vb": 47.0, "zone": None, "z": None},
    "Gaya":             {"vb": 39.0, "zone": None, "z": None},
    "Gorakhpur":        {"vb": 47.0, "zone": None, "z": None},
    "Guwahati":         {"vb": 50.0, "zone": "V",   "z": 0.36},
    "Hyderabad":        {"vb": 44.0, "zone": "II",  "z": 0.10},
    "Imphal":           {"vb": 47.0, "zone": None, "z": None},
    "Indore":           {"vb": 39.0, "zone": "III", "z": 0.16},
    "Jabalpur":         {"vb": 47.0, "zone": None, "z": None},
    "Jaipur":           {"vb": 47.0, "zone": "II",  "z": 0.10},
    "Jamshedpur":       {"vb": 47.0, "zone": "III", "z": 0.16},
    "Jhansi":           {"vb": 47.0, "zone": None, "z": None},
    "Jodhpur":          {"vb": 47.0, "zone": "III", "z": 0.16},
    "Kanpur":           {"vb": 47.0, "zone": "III", "z": 0.16},
    "Kochi / Cochin":   {"vb": 39.0, "zone": "III", "z": 0.16},
    "Kohima":           {"vb": 44.0, "zone": None, "z": None},
    "Kolkata":          {"vb": 50.0, "zone": "III", "z": 0.16},
    "Kozhikode":        {"vb": 39.0, "zone": None, "z": None},
    "Kurnool":          {"vb": 39.0, "zone": None, "z": None},
    "Lakshadweep":      {"vb": 39.0, "zone": None, "z": None},
    "Lucknow":          {"vb": 47.0, "zone": "III", "z": 0.16},
    "Ludhiana":         {"vb": 47.0, "zone": None, "z": None},
    "Madurai":          {"vb": 39.0, "zone": "III", "z": 0.16},
    "Mandi":            {"vb": 39.0, "zone": None, "z": None},
    "Mangalore":        {"vb": 39.0, "zone": "III", "z": 0.16},
    "Moradabad":        {"vb": 47.0, "zone": None, "z": None},
    "Mumbai":           {"vb": 44.0, "zone": "III", "z": 0.16},
    "Mysore":           {"vb": 33.0, "zone": None, "z": None},
    "Nagpur":           {"vb": 44.0, "zone": "II",  "z": 0.10},
    "Nainital":         {"vb": 47.0, "zone": None, "z": None},
    "Nasik":            {"vb": 39.0, "zone": "III", "z": 0.16},
    "Nellore":          {"vb": 50.0, "zone": None, "z": None},
    "Panjim":           {"vb": 39.0, "zone": "III", "z": 0.16},
    "Patiala":          {"vb": 47.0, "zone": None, "z": None},
    "Patna":            {"vb": 47.0, "zone": "IV",  "z": 0.24},
    "Port Blair":       {"vb": 44.0, "zone": "III", "z": 0.16},
    "Puducherry":       {"vb": 50.0, "zone": None, "z": None},
    "Pune":             {"vb": 39.0, "zone": "III", "z": 0.16},
    "Raipur":           {"vb": 39.0, "zone": "II",  "z": 0.10},
    "Rajkot":           {"vb": 39.0, "zone": None, "z": None},
    "Ranchi":           {"vb": 39.0, "zone": "II",  "z": 0.10},
    "Roorkee":          {"vb": 39.0, "zone": None, "z": None},
    "Rourkela":         {"vb": 39.0, "zone": None, "z": None},
    "Shimla":           {"vb": 39.0, "zone": "IV",  "z": 0.24},
    "Srinagar":         {"vb": 39.0, "zone": "V",   "z": 0.36},
    "Surat":            {"vb": 44.0, "zone": "III", "z": 0.16},
    "Tiruchirappalli":  {"vb": 47.0, "zone": None, "z": None},
    "Trivandrum":       {"vb": 39.0, "zone": "III", "z": 0.16},
    "Udaipur":          {"vb": 47.0, "zone": None, "z": None},
    "Vadodara":         {"vb": 44.0, "zone": "III", "z": 0.16},
    "Varanasi":         {"vb": 47.0, "zone": "III", "z": 0.16},
    "Vijayawada":       {"vb": 50.0, "zone": "II",  "z": 0.10},
    "Vishakapatnam":    {"vb": 50.0, "zone": "II",  "z": 0.10},
}

MANUAL_ENTRY = "-- Manual entry (city not listed) --"
