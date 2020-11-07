# coding=utf-8
import utm
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
import overpy


def rgb(r, g, b):
    return r/255, g/255, b/255


def generate_plot_skeleton():
    fig = plt.figure()
    ax = fig.add_subplot()

    fig.patch.set_facecolor(outer_gap_color)
    fig.subplots_adjust(left=outer_gap_size, bottom=outer_gap_size,
                        right=1-outer_gap_size, top=1-(outer_gap_size + print_title * title_space))

    return fig, ax


def get_bounding_box(address, km_distance):
    print('\tGet Bounding Box for "%s"...' % address, end='',  flush=True)
    geo_locator = Nominatim(user_agent="City Location Maps")
    wgs84_center = geo_locator.geocode(address)
    center = (wgs84_center.latitude, wgs84_center.longitude)
    utm_center = utm.from_latlon(wgs84_center.latitude, wgs84_center.longitude)
    utm_top_right = (utm_center[0] + 1000*km_distance/2, utm_center[1] + 1000*km_distance/2, utm_center[2], utm_center[3])
    utm_bottom_left = (utm_center[0] - 1000*km_distance/2, utm_center[1] - 1000*km_distance/2, utm_center[2], utm_center[3])
    wgs84_top_right = utm.to_latlon(utm_top_right[0] + 1000, utm_top_right[1] + 1000, utm_top_right[2], utm_top_right[3])
    wgs84_bottom_left = utm.to_latlon(utm_bottom_left[0] - 1000, utm_bottom_left[1] - 1000, utm_bottom_left[2], utm_bottom_left[3])

    # bbox = [south,west,north,east]
    bbox_wgs84 = [wgs84_bottom_left[0], wgs84_bottom_left[1], wgs84_top_right[0], wgs84_top_right[1]]
    bbox_utm = [utm_bottom_left[0], utm_bottom_left[1], utm_top_right[0], utm_top_right[1]]
    print('\tdone')
    return bbox_wgs84, bbox_utm


def get_roads_from_overpass(bbox):
    print('\tLoad Roads from Overpass...', end='',  flush=True)

    # For OSM relations see: https://gist.github.com/4gus71n/26589a508d8deca333bb05928fd4beb0
    # https://overpass-turbo.eu/#
    api = overpy.Overpass()
    data = api.query("""
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
    ['highway']
    ['highway' !~ 'steps']
    ['highway' !~ 'path']
    ['highway' !~ 'track']
    ['highway' !~ 'raceway']
    ['highway' !~ 'road']
    ['highway' !~ 'bridleway']
    ['highway' !~ 'proposed']
    ['highway' !~ 'construction']
    ['highway' !~ 'corridor']
    ['highway' !~ 'elevator']
    ['highway' !~ 'passing_place']
    ['highway' !~ 'bus_guideway']
    ['highway' !~ 'footway']
    ['highway' !~ 'rest_area']
    ['highway' !~ 'service']
    ['highway' !~ 'bus_stop']
    ['highway' !~ 'platform'];
);
(._;>;);
out;""".format(*bbox))
    print('\t data received...', end='', flush=True)

    roads = {}
    for way in data.ways:
        norths = []
        easts = []
        for node in way.nodes:
            utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
            easts.append(utm_cord[0])
            norths.append(utm_cord[1])
        roads[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['highway']}
    print('\tdone')
    return roads



def get_rails_from_overpass(bbox):
    print('\tLoad Rails from Overpass...', end='',  flush=True)

    # For OSM relations see: https://gist.github.com/4gus71n/26589a508d8deca333bb05928fd4beb0
    # https://overpass-turbo.eu/#
    api = overpy.Overpass()
    data = api.query("""
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
    ['railway']
    ['railway' !~ 'station'];
);
(._;>;);
out;""".format(*bbox))
    # ['railway' !~ 'subway']
    print('\t data received...', end='', flush=True)

    rails = {}
    for way in data.ways:
        norths = []
        easts = []
        for node in way.nodes:
            utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
            easts.append(utm_cord[0])
            norths.append(utm_cord[1])
        rails[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['railway']}
    print('\tdone')
    return rails


def get_water_from_overpass(bbox):
    print('\tLoad Water from Overpass...', end='',  flush=True)

    # https://overpass-turbo.eu/#
    api = overpy.Overpass()
    data = api.query("""
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
  ['natural' = 'water']
  ['amenity' !~ 'fountain'];
  way
  ['water'];
  relation
  ['natural' = 'water']
  ['amenity' !~ 'fountain'];
  relation
  ['water'];
  way
  ['waterway' = 'riverbank']
  ['tunnel' !~ 'yes'];
  relation
  ['waterway' = 'riverbank']
  ['tunnel' !~ 'yes'];
  way
  ['waterway' = 'river']
  ['tunnel' !~ 'yes']
  ['width'];
  way
  ['natural' = 'coastline'];

);
(._;>;);
out;""".format(*bbox))
    print('\t data received...', end='', flush=True)
    water = {}
    added = set()

    for relation in data.relations:
        norths = []
        easts = []
        order = []
        for member in relation.members:


            if member.role == 'outer':
                first = None
                last = None
                for way in data.ways:
                    if way.id == member.ref:
                        first = way.nodes[0].id
                        last = way.nodes[-1].id
                order.append({'id': member.ref, 'first': first, 'last': last, 'used': False})

        order_new = []
        next_id = 0
        cnt = len(order) * 3
        # This loop tries to sort the ways of an relation so that they are connected in the right order
        # However, if they have no common start/end Points the sorting fails or is incomplete.
        # This rare cases this might result in wrong water plotting.
        while len(order_new) < len(order) and cnt > 0:
            cnt -= 1
            if len(order_new) == 0:
                order[0]['used'] = True
                order_new.append((order[0]['id'], 1))
                next_id = order[0]['last']
            else:
                for el in order:
                    if el['used']:
                        continue
                    else:
                        if el['first'] == next_id:
                            order_new.append((el['id'], 1))
                            next_id = el['last']
                            el['used'] = True
                        elif el['last'] == next_id:
                            order_new.append((el['id'], -1))
                            next_id = el['first']
                            el['used'] = True
                        elif el['last'] == el['first']:
                            order_new.append((el['id'], 1))
                            next_id = el['last']
                            el['used'] = True

        for el in order_new:
            for member in relation.members:
                if member.ref == el[0]:
                    for way in data.ways:
                        if way.id == member.ref:
                            added.add(member.ref)
                            for node in way.nodes[::el[1]]:
                                utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
                                easts.append(utm_cord[0])
                                norths.append(utm_cord[1])
        water[int(relation.id) + len(water)] = {'e': easts, 'n': norths, 'w': 0}

    for way in data.ways:
        norths = []
        easts = []
        width = 0
        if way.id in added:
            continue
        if 'width' in way.tags.keys():
            width = float(way.tags['width'])
        elif 'natural' in way.tags.keys() and way.tags['natural'] == 'coastline':
            width = 4
        for node in way.nodes:
            utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
            easts.append(utm_cord[0])
            norths.append(utm_cord[1])
        water[int(way.id)] = {'e': easts, 'n': norths, 'w': width}
    print('\tdone', flush=True)
    return water


def plot_map_data():
    print('\tPlotting...', end='', flush=True)

    for k, v in water.items():
        if v['w'] == 0:
            ax.fill(v['e'], v['n'], color=color_water)
        else:
            ax.plot(v['e'], v['n'], color=color_water, linewidth=v['w'] * water_width_factor)
    for k, v in roads.items():
        if v['type'] in road_width.keys():
            ax.plot(v['e'], v['n'], color=color_roads, linewidth=road_width[v['type']])
    for k, v in rails.items():
        if v['type'] in rail_width.keys():
            ax.plot(v['e'], v['n'], color=color_rails, linewidth=rail_width[v['type']])
            # ax.plot(v['e'], v['n'], color=color_bg, linewidth=.6*rail_width[v['type']])

    print('\tdone', flush=True)


def style_plot():
    print('\tStyling...', end='', flush=True)
    if print_title:
        ax.set_title(location['name'], fontsize=title_size, fontname=title_font, pad=title_pad, color=color_title)

    ax.axes.get_xaxis().set_ticks([])
    ax.axes.get_yaxis().set_ticks([])
    ax.axes.yaxis.set_ticklabels([])
    ax.patch.set_facecolor(plot_bg_color)

    for axis in ['top', 'bottom', 'left', 'right']:
        ax.spines[axis].set_linewidth(frame_size)
        ax.spines[axis].set_color(frame_color)

    ax.axis('square')
    ax.plot([bbox_utm[0], bbox_utm[0], bbox_utm[2], bbox_utm[2], bbox_utm[0]],
            [bbox_utm[1], bbox_utm[3], bbox_utm[3], bbox_utm[1], bbox_utm[1]],
            linewidth=inner_gap_size, color=inner_gap_color)
    ax.set(xlim=(bbox_utm[0], bbox_utm[2]), ylim=(bbox_utm[1], bbox_utm[3]))
    print('\tdone', flush=True)


def save_plot():
    print('\tSaving...', end='', flush=True)
    fig.set_size_inches(image_width_cm / 2.54, image_height_cm / 2.54)
    plt.savefig('{}.png'.format(location['name']), dpi=600)
    #plt.show()
    print('\t{}.png saved!\n'.format(location['name']), flush=True)


if __name__ == '__main__':

    locations = [{'name': 'Trump', 'address': 'Oval Office, Washington'},
                 {'name': 'Home', 'address': 'Onslow Sq 21, London, England', 'distance': 5}]

    default_distance = 8

    # Define Style
    image_width_cm = 20
    image_height_cm = 20

    color_fg = rgb(30, 30, 30)
    color_bg = rgb(255, 255, 255)

    outer_gap_size = 0.02  # percentage
    outer_gap_color = color_bg

    frame_size = 1  # line width
    frame_color = color_fg

    inner_gap_size = 15  # line width
    inner_gap_color = color_bg

    plot_bg_color = color_bg
    color_water = rgb(120, 120, 255)
    color_roads = color_fg
    color_rails = rgb(120, 120, 120)

    water_width_factor = 0.1
    road_width_max = 1.5  # line width
    road_width = {'motorway': road_width_max, 'motorway_link': road_width_max * 0.9,
                  'trunk': road_width_max * 0.9, 'trunk_link': road_width_max * 0.8,
                  'primary': road_width_max * 0.8, 'primary_link': road_width_max * 0.7,
                  'secondary': road_width_max * 0.75, 'secondary_link': road_width_max * 0.65,
                  'tertiary': road_width_max * 0.75, 'tertiary_link': road_width_max * 0.65,
                  'unclassified': road_width_max * 0.4,
                  'residential': road_width_max * 0.4,
                  'pedestrian': road_width_max * 0.35,
                  'living_street': road_width_max * 0.3,
                  'cycleway': road_width_max * 0.15}

    rail_width_max = 2.5  # line width
    rail_width = {'rail': rail_width_max, 'subway': road_width_max * 0.5}

    print_title = False
    color_title = color_fg
    title_space = 0.1
    title_size = 40
    title_font = 'Segoe UI'
    title_pad = 12

    for i, location in enumerate(locations):
        print('Processing {} of {}: {}'.format(i+1, len(locations), location['name']),  flush=True)

        fig, ax = generate_plot_skeleton()

        bbox_wgs84, bbox_utm = get_bounding_box(location['address'], location['distance'] if 'distance' in location else default_distance)
        roads = get_roads_from_overpass(bbox_wgs84)
        rails = get_rails_from_overpass(bbox_wgs84)
        water = get_water_from_overpass(bbox_wgs84)

        plot_map_data()
        style_plot()
        save_plot()






