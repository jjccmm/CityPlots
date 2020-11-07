# coding=utf-8
import utm
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
import overpy
import random


def rgb(r, g, b):
    return r/255, g/255, b/255


def generate_plot_skeleton():
    fig = plt.figure()
    ax = fig.add_subplot()

    fig.patch.set_facecolor(outer_gap_color)
    fig.subplots_adjust(left=outer_gap_size, bottom=outer_gap_size,
                        right=1-outer_gap_size, top=1-(outer_gap_size + print_title * title_space))

    return fig, ax


def get_bounding_box(address):
    print('\tGet Bounding Box for "%s"...' % address, end='',  flush=True)

    # get the wgs84 and utm coordinates of the center address
    geo_locator = Nominatim(user_agent="City Location Maps")
    wgs84_center = geo_locator.geocode(address)
    center = (wgs84_center.latitude, wgs84_center.longitude)
    utm_center = utm.from_latlon(wgs84_center.latitude, wgs84_center.longitude)

    # define the top-right and bottom-left points of the visible quare in utm
    utm_top_right = (utm_center[0] + 1000*km_distance/2, utm_center[1] + 1000*km_distance/2, utm_center[2], utm_center[3])
    utm_bottom_left = (utm_center[0] - 1000*km_distance/2, utm_center[1] - 1000*km_distance/2, utm_center[2], utm_center[3])
    # add 1km buffer for the overpass query
    wgs84_top_right = utm.to_latlon(utm_top_right[0] + 1000, utm_top_right[1] + 1000, utm_top_right[2], utm_top_right[3])
    wgs84_bottom_left = utm.to_latlon(utm_bottom_left[0] - 1000, utm_bottom_left[1] - 1000, utm_bottom_left[2], utm_bottom_left[3])

    # put together the bounding boxes = [south,west,north,east]
    bbox_wgs84 = [wgs84_bottom_left[0], wgs84_bottom_left[1], wgs84_top_right[0], wgs84_top_right[1]]
    bbox_utm = [utm_bottom_left[0], utm_bottom_left[1], utm_top_right[0], utm_top_right[1]]
    print('\tdone')
    return bbox_wgs84, bbox_utm


def get_roads_from_overpass(bbox):
    print('\tLoad Roads from Overpass...', end='',  flush=True)

    # To get only roads within a city relation see: https://gist.github.com/4gus71n/26589a508d8deca333bb05928fd4beb0
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

    # create road dict with east and north coordinates in utm and the highway type for each way received from overpass
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
    ['railway' !~ 'subway']
    ['railway' !~ 'station'];
);
(._;>;);
out;""".format(*bbox))
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


def get_borders_from_relation(data, relation_members):
    outer_borders = []
    inner_borders = []
    for member in relation_members:
        first = None
        last = None
        for way in data.ways:
            if way.id == member.ref:
                first = way.nodes[0].id
                last = way.nodes[-1].id
                break
        if member.role == 'outer':
            outer_borders.append({'id': member.ref, 'first': first, 'last': last, 'used': False})
        elif member.role == 'inner':
            inner_borders.append({'id': member.ref, 'first': first, 'last': last, 'used': False})
    return inner_borders, outer_borders


def separate_and_sort_borders(borders):
    sorted_loops = []
    borders_sorted = []
    next_id = 0
    start_id = 0
    cnt = len(borders) * 3  # If borders do not fit together it stops after cnt attempts
    borders_sorted_cnt = 0

    while borders_sorted_cnt < len(borders) and cnt > 0:
        cnt -= 1

        if len(borders_sorted) == 0:  # if current loop is empty, start with first unused element
            for el in borders:
                if not el['used']:
                    start_id = el['first']
                    el['used'] = True
                    borders_sorted.append((el['id'], 1))
                    next_id = el['last']
                    break
        else:
            for el in borders:
                if el['used']:
                    continue
                else:
                    if el['first'] == next_id:
                        borders_sorted.append((el['id'], 1))
                        next_id = el['last']
                        el['used'] = True
                    elif el['last'] == next_id:
                        borders_sorted.append((el['id'], -1))
                        next_id = el['first']
                        el['used'] = True

        if start_id == next_id:  # Check if loop is closed
            sorted_loops.append(borders_sorted)
            borders_sorted_cnt += len(borders_sorted)
            borders_sorted = []

    return sorted_loops


def concatenate_borders_as_utm(data, relation, borders, added):
    norths = []
    easts = []
    for el in borders:
        for member in relation.members:
            if member.ref == el[0]:
                for way in data.ways:
                    if way.id == member.ref:
                        added.add(member.ref)
                        for node in way.nodes[::el[1]]:
                            utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
                            easts.append(utm_cord[0])
                            norths.append(utm_cord[1])
    return easts, norths


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
    islands = {}
    added = set()

    for relation in data.relations:
        inner_borders, outer_borders = get_borders_from_relation(data, relation.members)
        inner_border_sorted_loops = separate_and_sort_borders(inner_borders)
        outer_borders_sorted_loops = separate_and_sort_borders(outer_borders)

        for outer_loop in outer_borders_sorted_loops:
            easts, norths = concatenate_borders_as_utm(data, relation, outer_loop, added)
            water[int(relation.id) + len(water) + random.randint(0, 10000)] = {'e': easts, 'n': norths, 'w': 0}

        for inner_loop in inner_border_sorted_loops:
            if inner_loop:
                easts, norths = concatenate_borders_as_utm(data, relation, inner_loop, added)
                islands[int(relation.id) + len(islands) + random.randint(0, 10000)] = {'e': easts, 'n': norths, 'w': 0}

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
    return water, islands


def plot_map_data():
    print('\tPlotting...', end='', flush=True)

    for k, v in water.items():
        if v['w'] == 0:
            ax.fill(v['e'], v['n'], color=water_color)
        else:
            ax.plot(v['e'], v['n'], color=water_color, linewidth=v['w'] * water_width_factor)
    for k, v in islands.items():
        ax.fill(v['e'], v['n'], color=plot_bg_color)
    for k, v in rails.items():
        if v['type'] in rail_width.keys():
            ax.plot(v['e'], v['n'], color=color_rails, linewidth=rail_width[v['type']])
            # ax.plot(v['e'], v['n'], color=color_bg, linewidth=.5*rail_width[v['type']])
    for k, v in roads.items():
        if v['type'] in road_width.keys():
            ax.plot(v['e'], v['n'], color=road_color, linewidth=road_width[v['type']])


    print('\tdone', flush=True)


def style_plot():
    print('\tStyling...', end='', flush=True)
    if print_title:
        ax.set_title(location['name'], fontsize=title_size, fontname=title_font, pad=title_pad, color=title_color)

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

    # ax.set_xlabel(u'© OpenStreetMap contributors', fontsize=5, labelpad=4, loc='right', color=color_fg)

    print('\tdone', flush=True)


def save_plot():
    print('\tSaving...', end='', flush=True)
    fig.set_size_inches(image_width_cm / 2.54, image_height_cm / 2.54)
    plt.savefig('{}.png'.format(location['name']), dpi=600)
    print('\t{}.png saved!\n'.format(location['name']), flush=True)


if __name__ == '__main__':

    ####################################################################################################################
    #                                          Define Location Input                                                   #
    ####################################################################################################################
    km_distance = 8  # default 8
    locations = [{'name': 'Trump', 'address': 'Oval Office, Washington DC'},
                 {'name': 'Home', 'address': 'Onslow Sq 21, London, England'}]

    ####################################################################################################################
    #                                          Define Style Parameter                                                  #
    ####################################################################################################################
    image_width_cm = 20             # default 20
    image_height_cm = 20            # default 20

    color_fg = rgb(30, 30, 30)      # default rgb(30, 30, 30)
    color_bg = rgb(255, 255, 255)   # default rgb(255, 255, 255)

    outer_gap_size = 0.02           # default 0.02 (size in percentage of plot)
    outer_gap_color = color_bg      # default color_bg

    frame_size = 1                  # default 1 (size as linewidth)
    frame_color = color_fg          # default color_fg

    inner_gap_size = 15             # default 15 (size as linewidth)
    inner_gap_color = color_bg      # default color_bg

    plot_bg_color = color_bg        # default color_bg
    water_color = rgb(120, 120, 255)  # default rgb(120, 120, 255)
    road_color = color_fg           # default color_fg
    color_rails = rgb(120, 120, 120)  # default rgb(120, 120, 120)

    water_width_factor = 0.1        # default 0.1 (as percentage of OSM width)
    road_width_max = 1.5            # default 1.5 (size as line width)
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
    rail_width_max = .4             # default 2.5 (size as line width)
    rail_width = {'rail': rail_width_max, 'subway': rail_width_max * 0.5}

    print_title = False             # default False
    title_color = color_fg          # default color_fg
    title_space = 0.08              # default 0.08 (as percentage of height)
    title_size = 40                 # default 40 (as fontsize)
    title_font = 'Segoe UI'         # default 'Segoe UI'
    title_pad = 12                  # default 12

    ####################################################################################################################
    #                                                End of Input                                                      #
    ####################################################################################################################

    for i, location in enumerate(locations):
        print('Processing {} of {}: {}'.format(i+1, len(locations), location['name']),  flush=True)

        fig, ax = generate_plot_skeleton()

        bbox_wgs84, bbox_utm = get_bounding_box(location['address'])
        roads = get_roads_from_overpass(bbox_wgs84)
        water, islands = get_water_from_overpass(bbox_wgs84)
        rails = get_rails_from_overpass(bbox_wgs84)

        plot_map_data()
        style_plot()
        save_plot()






