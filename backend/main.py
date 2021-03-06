from math import sin, cos, sqrt, atan2, radians
import os, math, numpy

class hgtMap:
    """
    This class represent an combination of topological conditions and water flood level
    Note, the 'point' (x, y) is data[x][y].
    Diagram showing how to interpret (x, y) <--> (lat, long):

    Y
    Lat
    ^
    | [[1,2,3,4]
    |  [2,3,4,5]
    |  [6,7,8,9]
    |  [7,8,9,0]]
    L___________> Long X
    note, data[0][0] = 1
    
    """

    def __init__(self, hgtStartData):
        """
        hgtStartData is the source data from the NASA JPL topological data
        This data comes from: https://dds.cr.usgs.gov/srtm/version2_1/SRTM1/
        It needs to be processed and provided to init as a 2D array [[...], ...]
        """
        self.data = []
        for row in hgtStartData:
            toAdd = []
            for height in row:
                toAdd.append([height, 0])
            self.data.append(toAdd)
        self.maxX = len(hgtStartData[0]) - 1
        self.maxY = len(hgtStartData) - 1

        self.minFloodHeight = 0

    def pointToLatLong(self, x, y):
        # x,y are integers
        deltaX = x * 1.0 / 1201
        deltaY = y * 1.0 / 1201
        if y > 1: y = 1
        if x > 1: x = 1
        return [41 - deltaY, -(73 + deltaX)]

    def latLongToPointApprox(self, lat, long):
        y = (int)(-1201 * (lat - 41))
        x = (int)(-1201 * (long + 73))
        if y > 1200: y = 1200
        if x > 1200: x = 1200
        if y < 0: y = 0
        if x < 0: x = 0
        return [x, y]  # yes, I know its y,x not x,y. Yes, its correct. # future me, ignrore that

    def getHeight(self, x, y):
        """
        returns the topological height at (x, y)
        """
        if x > self.maxX or y > self.maxY or x < 0 or y < 0:
            return 10000000  # effectively infinity
        return self.data[y][x][0]

    def getWater(self, x, y):
        """
        returns the level of water at the point (x, y)
        """
        if x > self.maxX or y > self.maxY or x < 0 or y < 0:
            raise Exception("accessed an invalid position in method getWater")
        return self.data[y][x][1]

    def setWater(self, x, y, waterLevel):
        if x > self.maxX or y > self.maxY or x < 0 or y < 0:
            pass
        self.data[y][x][1] = waterLevel

    def getAllData(self):
        """
        This returns the raw internal state. Generally avoid using this if you can
        """
        return self.data


def latLongDist(lat1, long1, lat2, long2):
    # approximate radius of earth in km
    R = 6373.0
    lat1i = radians(lat1)
    lon1i = radians(long1)
    lat2i = radians(lat2)
    lon2i = radians(long2)
    dlon = lon2i - lon1i
    dlat = lat2i - lat1i
    a = sin(dlat / 2) ** 2 + cos(lat1i) * cos(lat2i) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def weight(delta):
    return 1.0 / (1 + 2.71828 ** (-1 * delta / 3))


def tick(floodMap):
    deltas = [[0] * (floodMap.maxX + 1)] * (floodMap.maxY + 1)
    for x in range(floodMap.maxX + 1):
        for y in range(floodMap.maxY + 1):
            if floodMap.getWater(x, y) < floodMap.minFloodHeight:
                pass
            else:
                # propagate water
                waterToSpread = floodMap.getWater(x, y)
                midHeight = floodMap.getHeight(x, y)
                weightSum = 0
                for i in range(x - 1, x + 2):
                    for j in range(y - 1, y + 2):
                        weightSum += weight(floodMap.getHeight(i, j) - midHeight)

                for i in range(x - 1, x + 2):
                    for j in range(y - 1, y + 2):
                        if (x == i) and (y == j):
                            deltas[j][i] = (waterToSpread * weight(0) / weightSum) - waterToSpread
                        else:
                            try:
                                deltas[j][i] = waterToSpread * weight(0) / weightSum
                            except:
                                pass
    for x in range(floodMap.maxX + 1):
        for y in range(floodMap.maxY + 1):
            floodMap.setWater(x, y, floodMap.getWater(x, y) + deltas[y][x])
    return floodMap

def main():
    import getPop, jsonify

    fn = './data/N40W074.hgt'
    siz = os.path.getsize(fn)
    dim = int(math.sqrt(siz / 2))
    assert dim * dim * 2 == siz, 'Invalid file size'
    data = numpy.fromfile(fn, numpy.dtype('>i2'), dim * dim).reshape((dim, dim))
    floodMap = hgtMap(data.tolist())


    floodStartLocation = floodMap.latLongToPointApprox(40.366, -73.88)
    userSelectedIntensity = 5  # provided by user (frontend)
    floodLitres = (10 ** 6) * (userSelectedIntensity ** 2)
    floodMap.minFloodHeight = 100
    floodMap.setWater(floodStartLocation[0], floodStartLocation[1], floodLitres)
    mins = 5
    tickInterations = mins
    for _ in range(tickInterations):
        floodMap = tick(floodMap)

    pmap = getPop.getPopulation(floodMap)
    totalPop = getPop.totalPop(pmap)
    jsonify.jsonify(floodMap, pmap, totalPop)

if __name__ == "__main__":
    main()