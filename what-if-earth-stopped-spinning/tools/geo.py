"""Land polygons (Natural Earth 1:110m, public domain) + ~380 city-light points."""
import json, random, shapefile, sys
from shapely.geometry import shape, Point
from shapely.ops import unary_union
G = sys.argv[1]
r = shapefile.Reader(f'{G}/naturalearth_lowres/naturalearth_lowres.shp')
geoms = [shape(s.__geo_interface__) for s in r.shapes()]
land = unary_union(geoms).simplify(0.25)
polys = []
for g in (land.geoms if hasattr(land, 'geoms') else [land]):
    if g.area < 0.6: continue
    polys.append([[round(x, 1), round(y, 1)] for x, y in g.exterior.coords])
print('polygons', len(polys), 'points', sum(map(len, polys)))
# city lights: Natural Earth populated places as seeds + seeded jitter clusters, kept on land
c = shapefile.Reader(f'{G}/naturalearth_cities/naturalearth_cities.shp')
seeds = [s.points[0] for s in c.shapes()]
dense = [(-74, 40.7, 40), (-87.6, 41.9, 14), (-118, 34, 14), (-80, 26, 6), (-46.6, -23.5, 16), (-43, -22.9, 8),
         (2.3, 48.9, 22), (8, 50, 30), (-0.1, 51.5, 18), (12.5, 45, 14), (37.6, 55.7, 12), (77, 28.6, 26),
         (78, 22, 22), (88.4, 22.6, 12), (72.9, 19, 12), (121.5, 31.2, 26), (116.4, 39.9, 18), (113.3, 23.1, 16),
         (139.7, 35.7, 22), (127, 37.5, 10), (31.2, 30, 10), (3.4, 6.5, 8), (106.8, -6.2, 10), (100.5, 13.8, 8),
         (-99.1, 19.4, 10), (151.2, -33.9, 5), (28, -26.2, 6), (67, 24.9, 6)]
rnd = random.Random(20261125)
landP = land.buffer(0)
pts = []
def add(x, y, n, sp):
    for _ in range(n * 6):
        if n <= 0: break
        px, py = x + rnd.gauss(0, sp), y + rnd.gauss(0, sp * .7)
        if landP.contains(Point(px, py)) and abs(py) < 70:
            pts.append([round(px, 2), round(py, 2), round(rnd.uniform(.45, 1), 2)]); n -= 1
for x, y, n in dense: add(x, y, n, 2.2)
for x, y in seeds:
    if len(pts) >= 380: break
    add(x, y, 1, .3)
pts = pts[:380]
print('lights', len(pts))
json.dump({'land': polys, 'lights': pts}, open('build/geo.json', 'w'), separators=(',', ':'))
