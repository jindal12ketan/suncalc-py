"""
TODO: include suncalc.js' BSD-2-clause license
"""
import numpy as np

# shortcuts for easier to read formulas
PI = np.pi
sin = np.sin
cos = np.cos
tan = np.tan
asin = np.arcsin
atan = np.arctan2
acos = np.arccos
rad = PI / 180

# date/time constants and conversions
dayMs = 1000 * 60 * 60 * 24
J1970 = 2440588
J2000 = 2451545

# function toJulian(date) { return date.valueOf() / dayMs - 0.5 + J1970; }
# function fromJulian(j)  { return new Date((j + 0.5 - J1970) * dayMs); }
# function toDays(date)   { return toJulian(date) - J2000; }

# general calculations for position

# obliquity of the Earth
e = rad * 23.4397


def right_ascension(l, b):
    return atan(sin(l) * cos(e) - tan(b) * sin(e), cos(l))

def declination(l, b):
    return asin(sin(b) * cos(e) + cos(b) * sin(e) * sin(l))


def azimuth(H, phi, dec):
    return atan(sin(H), cos(H) * sin(phi) - tan(dec) * cos(phi))

def altitude(H, phi, dec):
    return asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(H))

def siderealTime(d, lw):
    return rad * (280.16 + 360.9856235 * d) - lw

def astro_refraction(h):
    # the following formula works for positive altitudes only.
    # if h = -0.08901179 a div/0 would occur.
    h = np.maximum(h, 0)

    # formula 16.4 of "Astronomical Algorithms" 2nd edition by Jean Meeus
    # (Willmann-Bell, Richmond) 1998. 1.02 / tan(h + 10.26 / (h + 5.10)) h in
    # degrees, result in arc minutes -> converted to rad:
    return 0.0002967 / np.tan(h + 0.00312536 / (h + 0.08901179))


# general sun calculations

def solar_mean_anomaly(d):
    return rad * (357.5291 + 0.98560028 * d)

def ecliptic_longitude(M):
    # equation of center
    C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M))

    # perihelion of the Earth
    P = rad * 102.9372

    return M + C + P + PI


def sun_coords(d):
    M = solar_mean_anomaly(d)
    L = ecliptic_longitude(M)

    return {
        'dec': declination(L, 0),
        'ra': right_ascension(L, 0)
    }


SunCalc = {}


def get_position(date, lat, lng):
    """Calculate sun position for a given date and latitude/longitude
    """

    lw  = rad * -lng
    phi = rad * lat
    d   = toDays(date)

    c  = sun_coords(d)
    H  = siderealTime(d, lw) - c['ra']

    return {
        'azimuth': azimuth(H, phi, c['dec']),
        'altitude': altitude(H, phi, c['dec'])
    }

# sun times configuration (angle, morning name, evening name)
times = [
    (-0.833, 'sunrise',       'sunset'      ),
    (  -0.3, 'sunriseEnd',    'sunsetStart' ),
    (    -6, 'dawn',          'dusk'        ),
    (   -12, 'nauticalDawn',  'nauticalDusk'),
    (   -18, 'nightEnd',      'night'       ),
    (     6, 'goldenHourEnd', 'goldenHour'  )
]

def add_time(angle, rise_name, set_name):
    """Add a custom time to the times config
    """
    times.append((angle, rise_name, set_name))


# calculations for sun times
J0 = 0.0009

def julian_cycle(d, lw):
    return np.round(d - J0 - lw / (2 * PI))

def approx_transit(Ht, lw, n):
    return J0 + (Ht + lw) / (2 * PI) + n

def solar_transit_j(ds, M, L):
    return J2000 + ds + 0.0053 * sin(M) - 0.0069 * sin(2 * L)

def hour_angle(h, phi, d):
    return acos((sin(h) - sin(phi) * sin(d)) / (cos(phi) * cos(d)))

def observer_angle(height):
    return -2.076 * np.sqrt(height) / 60


def get_set_j(h, lw, phi, dec, n, M, L):
    """Get set time for the given sun altitude
    """
    w = hour_angle(h, phi, dec)
    a = approx_transit(w, lw, n)
    return solar_transit_j(a, M, L)


def get_times(date, lat, lng, height=0):
    """Calculate sun times

    Calculate sun times for a given date, latitude/longitude, and, optionally,
    the observer height (in meters) relative to the horizon
    """
    lw = rad * -lng
    phi = rad * lat

    dh = observer_angle(height)

    d = toDays(date)
    n = julian_cycle(d, lw)
    ds = approx_transit(0, lw, n)

    M = solar_mean_anomaly(ds)
    L = ecliptic_longitude(M)
    dec = declination(L, 0)

    Jnoon = solar_transit_j(ds, M, L)

    result = {
        'solarNoon': fromJulian(Jnoon),
        'nadir': fromJulian(Jnoon - 0.5)
    }

    for i in range(len(times)):
        time = times[i]
        h0 = (time[0] + dh) * rad

        Jset = get_set_j(h0, lw, phi, dec, n, M, L)
        Jrise = Jnoon - (Jset - Jnoon)

        result[time[1]] = fromJulian(Jrise)
        result[time[2]] = fromJulian(Jset)


    return result



# moon calculations, based on http://aa.quae.nl/en/reken/hemelpositie.html
# formulas

def moonCoords(d):
    """Geocentric ecliptic coordinates of the moon
    """

    # ecliptic longitude
    L = rad * (218.316 + 13.176396 * d)
    # mean anomaly
    M = rad * (134.963 + 13.064993 * d)
    # mean distance
    F = rad * (93.272 + 13.229350 * d)

    # longitude
    l  = L + rad * 6.289 * sin(M)
    # latitude
    b  = rad * 5.128 * sin(F)
    # distance to the moon in km
    dt = 385001 - 20905 * cos(M)

    return {
        'ra': right_ascension(l, b),
        'dec': declination(l, b),
        'dist': dt
    }


def getMoonPosition(date, lat, lng):

    lw  = rad * -lng
    phi = rad * lat
    d   = toDays(date)

    c = moonCoords(d)
    H = siderealTime(d, lw) - c['ra']
    h = altitude(H, phi, c['dec'])

    # formula 14.1 of "Astronomical Algorithms" 2nd edition by Jean Meeus
    # (Willmann-Bell, Richmond) 1998.
    pa = atan(sin(H), tan(phi) * cos(c['dec']) - sin(c['dec']) * cos(H))

    # altitude correction for refraction
    h = h + astro_refraction(h)

    return {
        'azimuth': azimuth(H, phi, c['dec']),
        'altitude': h,
        'distance': c['dist'],
        'parallacticAngle': pa
    }



# calculations for illumination parameters of the moon, based on
# http://idlastro.gsfc.nasa.gov/ftp/pro/astro/mphase.pro formulas and Chapter 48
# of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell,
# Richmond) 1998.

def getMoonIllumination(date):

    d = toDays(date)
    s = sun_coords(d)
    m = moonCoords(d)

    # distance from Earth to Sun in km
    sdist = 149598000

    phi = acos(sin(s['dec']) * sin(m['dec']) + cos(s['dec']) * cos(m['dec']) * cos(s['ra'] - m['ra']))
    inc = atan(sdist * sin(phi), m.dist - sdist * cos(phi)),
    angle = atan(cos(s['dec']) * sin(s['ra'] - m['ra']), sin(s['dec']) * cos(m['dec']) -
            cos(s['dec']) * sin(m['dec']) * cos(s['ra'] - m['ra']));


    return {
        'fraction': (1 + cos(inc)) / 2,
        'phase': 0.5 + 0.5 * inc * np.sign(angle) / PI,
        'angle': angle
    }


