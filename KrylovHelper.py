from math import radians, pi, cos, sin, asin, sqrt, atan2, tan, atan, exp, log

# conversion from (lat,lon) to meters
# "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:4326"
def LatLonToMeters( lat, lon ):
    originShift = 2 * pi * 6378137 / 2.0
    mx = lon * originShift / 180.0
    #this log is throwing an error
    print(lat)
    print((tan((90 + lat) * pi / 360.0 )))
    my = log( abs(tan((90 + lat) * pi / 360.0 ))) / (pi / 180.0)
    my = my * originShift / 180.0
    return mx, my

# conversion from meters to (lat,lon)
def MetersToLatLon( mx, my ):
    "Converts XY point from Spherical Mercator EPSG:4326 to lat/lon in WGS84 Datum"
    originShift = 2 * pi * 6378137 / 2.0
    lon = (mx / originShift) * 180.0
    lat = (my / originShift) * 180.0
    lat = 180 / pi * (2 * atan(exp(lat * pi / 180.0)) - pi / 2.0)
    return lat, lon


# haversine distance formula between two points specified by their GPS coordinates
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    m = 6367000. * c
    return m
