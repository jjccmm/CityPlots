# coding=utf-8
import utm
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
import overpy
import random


def rgb(r, g, b):
    return r / 255, g / 255, b / 255


def generate_plot_skeleton():
    fig = plt.figure()
    ax = fig.add_subplot()

    fig.patch.set_facecolor(params_l2['outer_gap_color'])
    fig.subplots_adjust(left=params_l2['outer_gap_size'], bottom=params_l2['outer_gap_size'],
                        right=1 - params_l2['outer_gap_size'],
                        top=1 - (params_l2['outer_gap_size'] + params_l2['print_title'] * params_l2['title_space']))

    return fig, ax


def get_bounding_box(address):
    print('\tGet Bounding Box for "%s"...' % address, end='', flush=True)

    # get the wgs84 and utm coordinates of the center address
    geo_locator = Nominatim(user_agent="City Location Maps")
    wgs84_center = geo_locator.geocode(address)
    center = (wgs84_center.latitude, wgs84_center.longitude)
    utm_center = utm.from_latlon(wgs84_center.latitude, wgs84_center.longitude)

    # define the top-right and bottom-left points of the visible square in utm
    utm_top_right = (
        utm_center[0] + 1000 * params_l1['km_distance_east'] / 2,
        utm_center[1] + 1000 * params_l1['km_distance_north'] / 2, utm_center[2], utm_center[3])
    utm_bottom_left = (
        utm_center[0] - 1000 * params_l1['km_distance_east'] / 2,
        utm_center[1] - 1000 * params_l1['km_distance_north'] / 2, utm_center[2], utm_center[3])

    # add 1km buffer for the overpass query
    wgs84_top_right = utm.to_latlon(utm_top_right[0] + 1000, utm_top_right[1] + 1000, utm_top_right[2],
                                    utm_top_right[3])
    wgs84_bottom_left = utm.to_latlon(utm_bottom_left[0] - 1000, utm_bottom_left[1] - 1000, utm_bottom_left[2],
                                      utm_bottom_left[3])

    # put together the bounding boxes = [south,west,north,east]
    bbox_wgs84 = [wgs84_bottom_left[0], wgs84_bottom_left[1], wgs84_top_right[0], wgs84_top_right[1]]
    bbox_utm = [utm_bottom_left[0], utm_bottom_left[1], utm_top_right[0], utm_top_right[1]]
    print('\tdone')
    return bbox_wgs84, bbox_utm


def query_osm_data_via_overpass(query_type):
    # To get only roads within a city relation see: https://gist.github.com/4gus71n/26589a508d8deca333bb05928fd4beb0
    # https://overpass-turbo.eu/#
    print('\t Query overpass...', end='', flush=True)

    queries = {'roads': """
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
    ['highway' !~ 'bus_stop']
    ['highway' !~ 'platform']
    ['building:part' !~ 'yes'];
);
(._;>;);
out;""",
               'water': """
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
out;""",
               'rails': """
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
  	['railway' = 'rail']
  	['tunnel' !~ 'yes'];
  way
  	['railway' = 'subway'];
  way['railway' = 'tram']
   ['tunnel' !~ 'yes'];

);
(._;>;);
out;""",
               'buildings': """
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
  ['building'];
  relation
  ['building'];
);
(._;>;);
out;"""}

    api = overpy.Overpass()
    data = api.query(queries[query_type].format(*bbox_wgs84))

    print('data received.', end='', flush=True)
    return data


def convert_way_to_utm(way):
    norths = []
    easts = []
    for node in way.nodes:
        utm_cord = utm.from_latlon(float(node.lat), float(node.lon))
        easts.append(utm_cord[0])
        norths.append(utm_cord[1])
    return easts, norths


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


def process_roads():
    if 'roads' in hide:
        return {}
    print('\tRoads:', end='', flush=True)

    data = query_osm_data_via_overpass('roads')
    print('\tStart converting...', end='', flush=True)

    roads = {}
    for way in data.ways:
        easts, norths = convert_way_to_utm(way)
        roads[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['highway']}
    print('done.', flush=True)
    return roads


def process_rails():
    if 'rails' in hide:
        return {}
    print('\tRails:', end='', flush=True)

    data = query_osm_data_via_overpass('rails')
    print('\tStart converting...', end='', flush=True)

    rails = {}
    for way in data.ways:
        easts, norths = convert_way_to_utm(way)
        rails[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['railway']}
    print('done.', flush=True)
    return rails


def process_water():
    if 'water' in hide:
        return {}, {}
    print('\tWater:', end='', flush=True)

    data = query_osm_data_via_overpass('water')
    print('\tStart converting...', end='', flush=True)

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
            easts, norths = concatenate_borders_as_utm(data, relation, inner_loop, added)
            islands[int(relation.id) + len(islands) + random.randint(0, 10000)] = {'e': easts, 'n': norths, 'w': 0}

    for way in data.ways:
        if way.id in added:
            continue
        if 'width' in way.tags.keys():
            width = float(way.tags['width'])
        elif 'natural' in way.tags.keys() and way.tags['natural'] == 'coastline':
            width = 4
        else:
            width = 0
        easts, norths = convert_way_to_utm(way)
        water[int(way.id)] = {'e': easts, 'n': norths, 'w': width}

    print('done.', flush=True)
    return water, islands


def process_buildings():
    if 'buildings' in hide:
        return {}, {}
    print('\tBuildings:', end='', flush=True)

    data = query_osm_data_via_overpass('buildings')
    print('\tStart converting...', end='', flush=True)

    buildings = {}
    yards = {}
    added = set()

    for relation in data.relations:
        inner_borders, outer_borders = get_borders_from_relation(data, relation.members)
        inner_border_sorted_loops = separate_and_sort_borders(inner_borders)
        outer_borders_sorted_loops = separate_and_sort_borders(outer_borders)

        for outer_loop in outer_borders_sorted_loops:
            easts, norths = concatenate_borders_as_utm(data, relation, outer_loop, added)
            buildings[int(relation.id) + len(buildings) + random.randint(0, 10000)] = {'e': easts, 'n': norths}

        for inner_loop in inner_border_sorted_loops:
            easts, norths = concatenate_borders_as_utm(data, relation, inner_loop, added)
            yards[int(relation.id) + len(yards) + random.randint(0, 10000)] = {'e': easts, 'n': norths}

    for way in data.ways:
        if way.id in added:
            continue
        easts, norths = convert_way_to_utm(way)
        buildings[int(way.id)] = {'e': easts, 'n': norths}

    print('done.', flush=True)
    return buildings, yards


def plot_map_data():
    print('\tPlotting...', end='', flush=True)

    for k, v in water.items():
        if v['w'] == 0:
            ax.fill(v['e'], v['n'], color=params_l3['water_c'], zorder=2)
        else:
            ax.plot(v['e'], v['n'], color=params_l3['water_c'], linewidth=v['w'] * params_l2['water_width_factor'],
                    zorder=2)
    for k, v in islands.items():
        ax.fill(v['e'], v['n'], color=params_l2['plot_bg_color'], zorder=3)
    for k, v in rails.items():
        if v['type'] not in hide and '{}_lw'.format(v['type']) in params_l3.keys():
            ax.plot(v['e'], v['n'], color=params_l3['{}_c'.format(v['type'])],
                    linewidth=params_l3['{}_lw'.format(v['type'])], zorder=5)
    for k, v in roads.items():
        if v['type'] not in hide and '{}_lw'.format(v['type']) in params_l3.keys():
            ax.plot(v['e'], v['n'], color=params_l3['{}_c'.format(v['type'])],
                    linewidth=params_l3['{}_lw'.format(v['type'])], zorder=9)
    for k, v in buildings.items():
        ax.fill(v['e'], v['n'], color=params_l3['building_c'], zorder=7)
    for k, v in yards.items():
        ax.fill(v['e'], v['n'], color=params_l2['plot_bg_color'], zorder=8)

    print('\tdone', flush=True)


def style_plot():
    print('\tStyling...', end='', flush=True)
    if params_l2['print_title']:
        ax.set_title(location['name'], fontsize=params_l2['title_size'], fontname=params_l2['title_font'],
                     pad=params_l2['title_pad'], color=params_l2['title_color'])

    ax.axes.get_xaxis().set_ticks([])
    ax.axes.get_yaxis().set_ticks([])
    ax.axes.yaxis.set_ticklabels([])
    ax.patch.set_facecolor(params_l2['plot_bg_color'])

    for axis in ['top', 'bottom', 'left', 'right']:
        ax.spines[axis].set_linewidth(params_l2['frame_size'])
        ax.spines[axis].set_color(params_l2['frame_color'])

    ax.axis('square')
    ax.plot([bbox_utm[0], bbox_utm[0], bbox_utm[2], bbox_utm[2], bbox_utm[0]],
            [bbox_utm[1], bbox_utm[3], bbox_utm[3], bbox_utm[1], bbox_utm[1]],
            linewidth=params_l2['inner_gap_size'], color=params_l2['inner_gap_color'], zorder=50)
    ax.set(xlim=(bbox_utm[0], bbox_utm[2]), ylim=(bbox_utm[1], bbox_utm[3]))

    ax.set_xlabel(u'© OpenStreetMap contributors', fontsize=5, labelpad=4, loc='right', color=params_l1['color_fg'])

    print('\tdone', flush=True)


def save_plot():
    print('\tSaving...', end='', flush=True)
    fig.set_size_inches(params_l2['image_width_cm'] / 2.54, params_l2['image_height_cm'] / 2.54)
    plt.savefig('{}.png'.format(location['name']), dpi=600)
    print('\t{}.png saved!\n'.format(location['name']), flush=True)


if __name__ == '__main__':

    # use 'custom_params' to override the default params in the following param dicts
    custom_params = {'locations': [{'name': 'Your_Location_Name', 'address': 'Your_Location_Address'}],
                     'color_fg': rgb(255, 30, 30)}
    # use 'hide' to hide elements
    hide = ['buildings', 'subway', 'tram', 'service']

    ####################################################################################################################
    #                                       Level One Parameter                                                        #
    ####################################################################################################################
    params_l1 = {'locations': [{'name': 'Trump', 'address': 'Oval Office, Washington DC'},
                               {'name': 'London', 'address': 'Onslow Sq 21, London, England'}],
                 'km_distance_east': 8,
                 'km_distance_north': 8,
                 'color_fg': rgb(30, 30, 30),
                 'color_bg': rgb(255, 255, 255)}
    params_l1.update(custom_params)
    ####################################################################################################################
    #                                       Level Two Parameter                                                        #
    ####################################################################################################################
    params_l2 = {'water_color': rgb(120, 120, 255),
                 'building_color': rgb(220, 220, 220),
                 'road_color': params_l1['color_fg'],
                 'rail_color': params_l1['color_fg'],
                 'plot_bg_color': params_l1['color_bg'],
                 'water_width_factor': 0.1,
                 'road_width_max': 1.5,
                 'rail_width_max': 0.2,
                 'image_width_cm': 20,
                 'image_height_cm': 20,
                 'outer_gap_size': 0.02,
                 'outer_gap_color': params_l1['color_bg'],
                 'frame_size': 1,
                 'frame_color': params_l1['color_fg'],
                 'inner_gap_size': 15,
                 'inner_gap_color': params_l1['color_bg'],
                 'print_title': False,
                 'title_color': params_l1['color_fg'],
                 'title_space': 0.08,
                 'title_size': 40,
                 'title_font': 'Segoe UI',
                 'title_pad': 12}
    params_l2.update(custom_params)
    ####################################################################################################################
    #                                    Level Three Parameter: Color                                                  #
    ####################################################################################################################
    params_l3 = {'motorway_c': params_l2['road_color'], 'motorway_link_c': params_l2['road_color'],
                 'trunk_c': params_l2['road_color'], 'trunk_link_c': params_l2['road_color'],
                 'primary_c': params_l2['road_color'], 'primary_link_c': params_l2['road_color'],
                 'secondary_c': params_l2['road_color'], 'secondary_link_c': params_l2['road_color'],
                 'tertiary_c': params_l2['road_color'], 'tertiary_link_c': params_l2['road_color'],
                 'unclassified_c': params_l2['road_color'],
                 'residential_c': params_l2['road_color'],
                 'pedestrian_c': params_l2['road_color'],
                 'living_street_c': params_l2['road_color'],
                 'cycleway_c': params_l2['road_color'],
                 'service_c': params_l2['road_color'],
                 'rail_c': params_l2['rail_color'],
                 'subway_c': params_l2['rail_color'],
                 'tram_c': params_l2['rail_color'],
                 'water_c': params_l2['water_color'],
                 'building_c': params_l2['building_color']}
    params_l3.update(custom_params)
    ####################################################################################################################
    #                                    Level Three Parameter: Line width                                             #
    ####################################################################################################################
    line_widths = {'motorway_lw': params_l2['road_width_max'], 'motorway_link_lw': params_l2['road_width_max'] * 0.9,
                   'trunk_lw': params_l2['road_width_max'] * 0.9, 'trunk_link_lw': params_l2['road_width_max'] * 0.8,
                   'primary_lw': params_l2['road_width_max'] * 0.8,
                   'primary_link_lw': params_l2['road_width_max'] * 0.7,
                   'secondary_lw': params_l2['road_width_max'] * 0.75,
                   'secondary_link_lw': params_l2['road_width_max'] * 0.65,
                   'tertiary_lw': params_l2['road_width_max'] * 0.75,
                   'tertiary_link_lw': params_l2['road_width_max'] * 0.65,
                   'unclassified_lw': params_l2['road_width_max'] * 0.4,
                   'residential_lw': params_l2['road_width_max'] * 0.4,
                   'pedestrian_lw': params_l2['road_width_max'] * 0.35,
                   'living_street_lw': params_l2['road_width_max'] * 0.3,
                   'service_lw': params_l2['road_width_max'] * 0.2,
                   'cycleway_lw': params_l2['road_width_max'] * 0.15,
                   'rail_lw': params_l2['rail_width_max'],
                   'subway_lw': params_l2['rail_width_max'] * 0.5,
                   'tram_lw': params_l2['rail_width_max'] * 0.3}
    params_l3.update(line_widths)
    params_l3.update(custom_params)
    ####################################################################################################################
    #                                                End of Input                                                      #
    ####################################################################################################################

    for i, location in enumerate(params_l1['locations']):
        print('Processing {} of {}: {}'.format(i + 1, len(params_l1['locations']), location['name']), flush=True)

        fig, ax = generate_plot_skeleton()

        bbox_wgs84, bbox_utm = get_bounding_box(location['address'])
        roads = process_roads()
        water, islands = process_water()
        buildings, yards = process_buildings()
        rails = process_rails()

        plot_map_data()
        style_plot()
        save_plot()
