# coding=utf-8
import utm
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from geopy.geocoders import Nominatim
import overpy
import random
import numpy as np
import datetime
from pathlib import Path
import time
from tqdm import tqdm
import pickle
import os
import json


def rgb(r, g, b):
    return r / 255, g / 255, b / 255


def wait_for(x):
    for i in tqdm(range(60)):
        time.sleep(1)


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


    # ['highway' !~ 'footway']
    # ['highway' !~ 'track']


def query_osm_data_via_overpass(query_type):
    # To get only roads within a city relation see: https://gist.github.com/4gus71n/26589a508d8deca333bb05928fd4beb0
    # https://overpass-turbo.eu/#

    queries = {'roads': """
[timeout:900][out:json][bbox: {}, {}, {}, {}];
(
  way
    ['highway']
    ['highway' !~ 'steps']
    ['highway' !~ 'path']
    ['highway' !~ 'raceway']
    ['highway' !~ 'road']
    ['highway' !~ 'bridleway']
    ['highway' !~ 'proposed']
    ['highway' !~ 'construction']
    ['highway' !~ 'corridor']
    ['highway' !~ 'elevator']
    ['highway' !~ 'passing_place']
    ['highway' !~ 'bus_guideway']
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
    if query_type == 'buildings':
        print('\t Query overpass 1/3...', end='', flush=True)

        # boxes = [south, west, north, east]
        step_size = (bbox_wgs84[2] - bbox_wgs84[0]) / 3
        bbox_wgs84_top = [bbox_wgs84[2] - step_size, bbox_wgs84[1], bbox_wgs84[2], bbox_wgs84[3]]
        bbox_wgs84_mid = [bbox_wgs84[2] - 2*step_size, bbox_wgs84[1], bbox_wgs84[2] - step_size, bbox_wgs84[3]]
        bbox_wgs84_bot = [bbox_wgs84[2] - 3*step_size, bbox_wgs84[1], bbox_wgs84[2] - 2*step_size, bbox_wgs84[3]]

        data_top = api.query(queries[query_type].format(*bbox_wgs84_top))

        wait_for(2000)
        print('\t2/3...', end='', flush=True)
        data_mid = api.query(queries[query_type].format(*bbox_wgs84_mid))
        wait_for(2000)
        print('\t3/3...', end='', flush=True)
        data_bot = api.query(queries[query_type].format(*bbox_wgs84_bot))

        print('data received.', end='', flush=True)

        return data_top, data_mid, data_bot
    else:


        print('\t Query overpass...', end='', flush=True)

        data = api.query(queries[query_type].format(*bbox_wgs84))
        #with open('data/' + filename + '.json', 'wb') as bin_file:
        #    data = json.dump(data, bin_file)

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


def load_from_disk(query_type):
    filename = location['address'][0:20] + '_' + str(int(custom_params['km_distance_north'])) + '_' \
               + str(int(custom_params['km_distance_east'])) + "_" + query_type + '.bin'
    filename = filename.replace(' ', '')
    file_on_disk = ''
    saved_files = os.listdir('./data')
    for file in saved_files:
        loc, north, east, q_type = file[:-4].split('_')
        if loc == location['address'][0:20].replace(' ', ''):
            if int(north) >= int(custom_params['km_distance_north']):
                if int(east) >= int(custom_params['km_distance_east']):
                    if q_type == query_type:
                        file_on_disk = file
                        break
    if file_on_disk == '':
        return None
    else:
        print('\t Load from Disk...', end='', flush=True)
        with open('data/' + file_on_disk, 'rb') as bin_file:
            data = pickle.load(bin_file)
        return data


def save_to_file(data, query_type):
    filename = location['address'][0:20] + '_' + str(int(custom_params['km_distance_north'])) + '_' \
               + str(int(custom_params['km_distance_east'])) + "_" + query_type + '.bin'
    filename = filename.replace(' ', '')
    with open('data/' + filename, 'wb') as bin_file:
        data = pickle.dump(data, bin_file)


def process_roads():
    if 'roads' in hide:
        return {}
    print('\tRoads:', end='', flush=True)

    roads = load_from_disk('roads')
    if roads == None:

        data = query_osm_data_via_overpass('roads')
        print('\tStart converting...', end='', flush=True)

        roads = {}
        for way in data.ways:
            easts, norths = convert_way_to_utm(way)
            roads[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['highway']}

        save_to_file(roads, 'roads')
    print('done.', flush=True)
    return roads




def process_rails():
    if 'rails' in hide:
        return {}
    print('\tRails:', end='', flush=True)

    rails = load_from_disk('rails')
    if rails == None:

        data = query_osm_data_via_overpass('rails')
        print('\tStart converting...', end='', flush=True)

        rails = {}
        for way in data.ways:
            easts, norths = convert_way_to_utm(way)
            rails[int(way.id)] = {'e': easts, 'n': norths, 'type': way.tags['railway']}

        save_to_file(rails, 'rails')
    print('done.', flush=True)
    return rails


def process_water():
    if 'water' in hide:
        return {}, {}
    print('\tWater:', end='', flush=True)

    water_islands = load_from_disk('water')
    if water_islands == None:

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
                if not way.tags['width'].isdigit():
                    break
                width = float(way.tags['width'])
            elif 'natural' in way.tags.keys() and way.tags['natural'] == 'coastline':
                width = 4
            else:
                width = 0
            easts, norths = convert_way_to_utm(way)
            water[int(way.id)] = {'e': easts, 'n': norths, 'w': width}

        save_to_file([water, islands], 'water')

    else:
        water, islands = water_islands
    print('done.', flush=True)
    return water, islands


def process_buildings():
    if 'buildings' in hide:
        return {}, {}
    print('\tBuildings:', end='', flush=True)

    buildings_yards = load_from_disk('buildings')
    if buildings_yards == None:

        data_top, data_mid, data_bot = query_osm_data_via_overpass('buildings')
        print('\tStart converting...', end='', flush=True)

        buildings = {}
        yards = {}
        added = set()
        for data in [data_top, data_mid, data_bot]:

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

        save_to_file([buildings, yards], 'buildings')

    else:
        buildings, yards = buildings_yards

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
                    linewidth=params_l3['{}_lw'.format(v['type'])], zorder=7 if v['type'] == 'footway' or v['type'] == 'track' else 11)
    for k, v in buildings.items():
        ax.fill(v['e'], v['n'], color=params_l3['building_c'], zorder=7)
        ax.plot(v['e'], v['n'], color=params_l1['color_fg'], linewidth=params_l2['road_width_max'] * 0.1, zorder=8)
    for k, v in yards.items():
        ax.fill(v['e'], v['n'], color=params_l2['plot_bg_color'], zorder=9)
        ax.plot(v['e'], v['n'], color=params_l1['color_fg'], linewidth=params_l2['road_width_max'] * 0.1, zorder=9)


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

    # ax.set_xlabel(u'© OpenStreetMap contributors', fontsize=5, labelpad=4, loc='right', color=params_l1['color_fg'])
    cmap = ListedColormap([[1, 1, 1, i] for i in np.linspace(0, .9, 50)])
    csfont = {'fontname': 'Kinetika Ultra'}
    ax.imshow([[0, 0], [0.1, 0.1], [0.3, 0.3], [0.7, 0.7], [1, 1], [1, 1], [1, 1]], extent=(bbox_utm[0], bbox_utm[2], bbox_utm[1], bbox_utm[1] + .4*(bbox_utm[3]-bbox_utm[1])), interpolation='bilinear', cmap=cmap, zorder=60)
    ax.text((bbox_utm[0]+bbox_utm[2])/2, bbox_utm[1] + .12*(bbox_utm[3]-bbox_utm[1]), location['name'], horizontalalignment='center', verticalalignment='center', fontsize=60, weight=550, zorder=61, fontname='Bahnschrift')
    ax.plot([(bbox_utm[0]+bbox_utm[2])/2, (bbox_utm[0]+bbox_utm[2])/2], [bbox_utm[1] + .065*(bbox_utm[3]-bbox_utm[1]), bbox_utm[1] + .07*(bbox_utm[3]-bbox_utm[1])], linewidth=1, color=rgb(0, 0, 0), zorder=61)
    ax.text((.51*bbox_utm[0]+.49*bbox_utm[2]), bbox_utm[1] + .065*(bbox_utm[3]-bbox_utm[1]), location['gpsn'], horizontalalignment='right', verticalalignment='center', fontsize=17, weight=150, zorder=61)
    ax.text((.49*bbox_utm[0]+.51*bbox_utm[2]), bbox_utm[1] + .065*(bbox_utm[3]-bbox_utm[1]), location['gpse'], horizontalalignment='left', verticalalignment='center', fontsize=17, weight=150, zorder=61)

    #ornament = plt.imread('Ornament.png')
    #ax.imshow(ornament,
    #          extent=(bbox_utm[0]*.7+.3*bbox_utm[2], bbox_utm[0]*.3+.7*bbox_utm[2], bbox_utm[1] + .093*(bbox_utm[3]-bbox_utm[1]), bbox_utm[1] + .099*(bbox_utm[3]-bbox_utm[1])), zorder=61)

    print('\tdone', flush=True)


def save_plot():
    print('\tSaving...', end='', flush=True)
    fig.set_size_inches(params_l2['image_width_cm'] / 2.54, params_l2['image_height_cm'] / 2.54)
    Path(dir).mkdir(parents=True, exist_ok=True)
    # plt.show()
    plt.savefig('{}/{}_{}_{}.png'.format(dir, location['name'], params_l1['km_distance_north'], params_l1['km_distance_east']), dpi=600)
    print('\t{}.png saved!\n'.format(location['name']), flush=True)


if __name__ == '__main__':

    # use 'custom_params' to override the default params in the following param dicts
    custom_params = {'locations': [
                                   #{'name': 'WERL', 'address': 'Werl, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E', 'road_width_max': 1.6},
                                   #{'name': 'VÖLLINGHAUSEN', 'address': 'Wamel, Möhnesee, Germany', 'gpsn': '51.3546°N', 'gpse': '8.1753°E', 'road_width_max': 1.6},
                                   {'name': 'MÖHNESEE', 'address': 'Hoher Stoß, Möhnesee, Germany', 'gpsn': '51.3546°N', 'gpse': '8.1753°E', 'road_width_max': 1.6},
                                    #{'name': 'MÜNCHEN', 'address': 'Munich, Germany', 'gpsn': '48.1372°N', 'gpse': '11.5755°E'}
                                    #{'name': 'HEVEN', 'address': 'Heven, Germany', 'gpsn': '51.2625°N', 'gpse': '7.1831°E'}
                                    #{'name': 'DORTMUND', 'address': 'Dortmund, Germany', 'gpsn': '51.5135°N', 'gpse': '7.4652°E'}
                                    #{'name': 'LÜNEBURG', 'address': 'Lüneburg, Germany', 'gpsn': '53.2464°N', 'gpse': '10.4115°E'}
                                    #{'name': 'BERLIN', 'address': 'Berlin, Germany', 'gpsn': '52.3112°N', 'gpse': '13.4049°E'}
                                    #{'name': 'SOEST', 'address': 'Soest, Germany', 'gpsn': '51.5711°N', 'gpse': '8.1057°E'}
                                    #{'name': 'GÖTTINGEN', 'address': 'Göttingen, Germany', 'gpsn': '51.5412°N', 'gpse': '9.9158°E'}
                                    #{'name': 'PADERBORN', 'address': 'Paderborn, Germany', 'gpsn': '51.4308°N', 'gpse': '8.4517°E'}
                                    # ,{'name': 'HAGEN', 'address': 'Hagen, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'DORTMUND', 'address': 'Dortmund, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'AACHEN', 'address': 'Aachen, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'HERDECKE', 'address': 'Herdecke, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'WETTER', 'address': 'Wetter, Ruhr, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'MÜNSTER', 'address': 'Münster, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'BREMEN', 'address': 'Bremen, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'PEKING', 'address': 'Peking, Forbidden City, China', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'OSLO', 'address': 'Oslo, Norway', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'BRISBANE', 'address': 'Brisbane, Australia', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   # ,{'name': 'RECKLINGHAUSEN', 'address': 'Recklinghausen, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E'}
                                   #,{'name': 'TOKYO', 'address': 'Tokyo, Japan', 'gpsn': '51.5507°N', 'gpse': '7.8829°E', 'road_width_max': .8}
                                   #,{'name': 'HANGZHOU', 'address': 'Hangzhou, China', 'gpsn': '51.5507°N', 'gpse': '7.8829°E', 'road_width_max': .8}
                                   #,{'name': 'IPSWITCH', 'address': 'Ipswitch, Germany', 'gpsn': '51.5507°N', 'gpse': '7.8829°E', 'road_width_max': 1.3}

                                   ],
                 'km_distance': 9,
                 'inner_gap_size': 0,
                 'outer_gap_size': 0,
                 'color_fg': rgb(20, 20, 20),
                 'color_bg': rgb(255, 255, 255),
                 'image_width_cm': 20,
                 'image_height_cm': 30,
                 'frame_size': 0,
                 'road_width_max': 1.6,
                 'print_title': False}
    # use 'hide' to hide elements
    # hide = ['buildings', 'subway', 'tram', 'service', 'rails', 'water']
    hide = ['subway', 'tram', 'service']
    custom_params['km_distance_north'] = 6
    custom_params['km_distance_east'] = 4
    custom_params['building_color'] = rgb(225, 225, 225)
    #################################################################
    dir = datetime.datetime.now().strftime("%b%d_%H-%M-%S")
    custom_params_in = custom_params
    for i, location in enumerate(custom_params_in['locations']):
        custom_params = custom_params_in
        ####################################################################################################################
        #                                       Level One Parameter                                                        #
        ####################################################################################################################
        params_l1 = {'locations': [{'name': 'Trump', 'address': 'Oval Office, Washington DC'},
                                   {'name': 'London', 'address': 'Onslow Sq 21, London, England'}],
                     'km_distance_east': 8,
                     'km_distance_north': 8,
                     'color_fg': rgb(255, 30, 30),
                     'color_bg': rgb(255, 255, 255)}
        params_l1.update(custom_params)
        ####################################################################################################################
        #                                       Level Two Parameter                                                        #
        ####################################################################################################################
        params_l2 = {'water_color': rgb(140, 140, 140),
                     'building_color': rgb(240, 240, 240),
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
                     'footway_c': rgb(160, 160, 160), 'track_c': rgb(160, 160, 160),
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
        line_widths = {'motorway_lw': params_l2['road_width_max']*1.8, 'motorway_link_lw': params_l2['road_width_max'] * 1.1,
                       'footway_lw': params_l2['road_width_max']*0.15, 'track_lw': params_l2['road_width_max']*0.15,
                       'trunk_lw': params_l2['road_width_max'] * 1.1, 'trunk_link_lw': params_l2['road_width_max'] * 1,
                       'primary_lw': params_l2['road_width_max'] * 1.1,
                       'primary_link_lw': params_l2['road_width_max'] * 1,
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
    # for i, location in enumerate(params_l1['locations']):
        custom_params = custom_params_in
        custom_params.update(location)
        print('Processing {} of {}: {}'.format(i + 1, len(params_l1['locations']), location['name']), flush=True)

        fig, ax = generate_plot_skeleton()

        bbox_wgs84, bbox_utm = get_bounding_box(location['address'])
        param = [location, custom_params['km_distance_north'], custom_params['km_distance_east']]
        #wait_for(2000)

        roads = process_roads()
        #wait_for(2000)
        water, islands = process_water()
        wait_for(2000)
        buildings, yards = process_buildings()
        wait_for(2000)
        rails = process_rails()

        plot_map_data()
        style_plot()
        save_plot()
