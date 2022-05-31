import networkx as nx
import json
import urllib
import urllib3
import requests
import pandas as pd
from shapely.geometry import LineString, Point
from srtm_py.srtm import main
import os
import numpy as np
from qgis import processing
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtCore import *
from osgeo import gdal, ogr
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsGeometry,
    QgsJsonUtils
)

# rivers =r'C:\Users\vital\Desktop\Diplom\vectors\1223.shp' #'C:/Users/vital/Desktop/Diplom/vectors/test2.shp'
def pixel(dx, dy, gt):
    px = gt[0]
    py = gt[3]
    rx = gt[1]
    ry = gt[5]
    x = round((dx - px)/rx)-1
    y = round((dy - py)/ry)-1
    return y, x

def extract_point(shape, attr):
    x_src = shape['coordinates'][0][0]
    y_src = shape['coordinates'][0][1]
    x_dst = shape['coordinates'][-1][0]
    y_dst = shape['coordinates'][-1][1]
    FID = attr['FID_split']
    return [x_src, y_src, x_dst, y_dst, FID]

def make_remote_request(url: str, params: dict):
   """
   Makes the remote request
   Continues making attempts until it succeeds
   """

   count = 1
   while True:
       try:
           response = requests.get((url + urllib.parse.urlencode(params)))
       except (OSError, urllib3.exceptions.ProtocolError) as error:
           print('\n')
           print('*' * 20, 'Error Occured', '*' * 20)
           print(f'Number of tries: {count}')
           print(f'URL: {url}')
           print(error)
           print('\n')
           count += 1
           continue
       break

   return response

def elevation_function(x):
   # url = 'https://api.opentopodata.org/v1/eudem25m?'
   url = 'https://api.open-elevation.com/api/v1/lookup?'
   params = {'locations': f"{x[0]},{x[1]}"}
   result = make_remote_request(url, params)
   return result.json()['results'][0]['elevation']

def orient_streams(streams, DEM, tolerance, elev_method, output):
    # output = r'C:\Users\vital\Desktop\Diplom\scratch\split_lines.shp' #C:/Users/vital/Desktop/Diplom/vectors/river_OSM1.shp
    # split_streams = 'in_memory/split_streams'

    # FIRSTLY, Need to split lines with a tool 'split' in qgis or arcgis. AND get singlepart lines
    splitwithlines = processing.run("native:splitwithlines", {'INPUT': streams, 'LINES': streams, 'OUTPUT': 'TEMPORARY_OUTPUT'}) #'TEMPORARY_OUTPUT'
    split_streams = splitwithlines['OUTPUT']
    added_field = processing.run("native:addautoincrementalfield", {'INPUT': split_streams, 'FIELD_NAME': 'FID_split', 'OUTPUT': 'TEMPORARY_OUTPUT'})
    split_streams = added_field['OUTPUT']
    shape = split_streams.getFeatures()
    df0 = []
    os.chdir("C:/Users/vital/Desktop/Diplom")
    for feature in shape:
        geom = feature.geometry().asJson()
        attr = QgsJsonUtils.exportAttributes(feature)
        dict_geom = json.loads(geom)
        dict_attr = json.loads(attr)
        # iface.statusBarIface().showMessage("{}".format(str(python_dict)))
        # QgsMessageLog.logMessage(str(python_dict))
        dict_shp = extract_point(dict_geom, dict_attr)
        df0.append(dict_shp)

    df = pd.DataFrame(df0, columns=['x_src', 'y_src', 'x_dst', 'y_dst', 'FID'])
    df['Line_ID'] = range(1, len(df.index) + 1)
    df_src = df[['x_src', 'y_src', 'FID', 'Line_ID']]
    df_dst = df[['x_dst', 'y_dst', 'FID', 'Line_ID']]
    df_src.columns = ['x', 'y', 'FID', 'Line_ID']
    df_dst.columns = ['x', 'y', 'FID', 'Line_ID']
    source = df_src.assign(R=0)
    destination = df_dst.assign(R=1)
    all = source.append(destination)

    ###2###
    all.insert(0, 'Point_ID', range(1, 1 + len(all)))
    all.insert(1, 'Point_ID2', 0)
    all.set_index('Point_ID', inplace=True)

    n = len(all)
    id2_list = []

    for i in range(n):
        if all.iloc[i]['Point_ID2'] != 0:
            continue
        temp_list = []
        for j in range(i + 1, n):
            if all.iloc[j]['x'] == all.iloc[i]['x'] and all.iloc[j]['y'] == all.iloc[i]['y']:
                temp_list.append(j)
                id2_list.append(j)
        for k in temp_list:
            all.at[k + 1, 'Point_ID2'] = i + 1
        if all.iloc[i]['Point_ID2'] == 0:
            all.at[i + 1, 'Point_ID2'] = i + 1
    all.insert(3, 'geometry', [(xy) for xy in zip(all.x, all.y)])
    ###3###
    # elevation_data = main.get_data()
    # all.insert(4, 'Elev', 0)
    # n = len(all)
    # for i in range(n):
    #     h = elevation_data.get_elevation(all.geometry.y.iloc[i], all.geometry.x.iloc[i])
    #     all.at[i + 1, 'Elev'] = h
    #
    # geo_df2 = all.groupby(['Line_ID'])['geometry'].apply(lambda x: LineString(x.tolist()))
    # geo_df2 = gpd.GeoDataFrame(geo_df2, geometry='geometry')

    gdf_source = all[all['R'] == 0]
    gdf_source = gdf_source[['Line_ID', 'Point_ID2']]
    gdf_source = gdf_source.rename(columns={'Point_ID2': 'Start_ID'}, inplace=False)
    gdf_dest = all[all['R'] == 1]
    gdf_dest = gdf_dest[['Line_ID', 'Point_ID2', 'FID']]
    gdf_dest = gdf_dest.rename(columns={'Point_ID2': 'End_ID'}, inplace=False)
    geo_df2 = gdf_source.merge(gdf_dest, on='Line_ID')
    all_nodes = all.drop_duplicates(["geometry"])

    ###4###

    GG = nx.Graph()

    for i in range(len(all_nodes)):
        GG.add_node(all_nodes.iloc[i]['Point_ID2'])
    for i in range(len(geo_df2)):
        GG.add_edge(geo_df2.iloc[i]['Start_ID'], geo_df2.iloc[i]['End_ID'], FID=geo_df2.iloc[i]['FID'],
                    End_ID=geo_df2.iloc[i]['End_ID'])
    flip_fid_list = []
    counter = 0

    D = GG.degree()
    list_leaves = []
    two_degree_list = []
    for i in D:
        if i[1] == 1:
            list_leaves.append(i[0])
        elif i[1] == 2:
            two_degree_list.append(i[0])
    # print(list_leaves)
    #With local DEM get elevation
    if elev_method == 0:
        raster = gdal.Open(DEM)
        gt = raster.GetGeoTransform()
        myarray = np.array(raster.GetRasterBand(1).ReadAsArray())
        for node in list_leaves:
            wkt = pixel(all_nodes.loc[node]['x'], all_nodes.loc[node]['y'], gt)
            elev = myarray[wkt[0], wkt[1]]
            GG.nodes[node]['elev'] = elev
    # With online get elevation (250m)
    if elev_method == 1:
        for node in list_leaves:
            elev = elevation_function((all_nodes.loc[node]['x'], all_nodes.loc[node]['y']))
            GG.nodes[node]['elev'] = elev
    # With SRTM-online get elevation(30m)
    if elev_method == 2:
        elevation_data = main.get_data()
        for node in list_leaves:
            elev = elevation_data.get_elevation(all_nodes.loc[node]['y'], all_nodes.loc[node]['x'])
            GG.nodes[node]['elev'] = elev

    A = (GG.subgraph(c) for c in nx.connected_components(GG))
    A = list(A)
    subgraphs = len(list(A))

    for G in A:
        D = G.degree()
        list_leaves_G = []
        for i in D:
            if i[1] == 1:
                list_leaves_G.append(i[0])

        leaves_list_with_elev = []
        l = 9999
        for i in list_leaves_G:
            k = G.nodes[i].pop('elev')
            if k == None:
                k = 0
            leaves_list_with_elev.append((i, k))
            if k < l:
                l = k
                min_elev = k
        dest = []
        for j in leaves_list_with_elev:
            if min_elev - tolerance <= j[1] <= min_elev + tolerance:
                dest.append(j[0])

        try:
            for d in dest:
                list_leaves_G.remove(d)
        except ValueError:
            continue

        for i in list_leaves_G:
            # Find the shortest path from node1 to node2
            all_sp = nx.all_simple_paths(G, source=i, target=dest)
            for sp_e in all_sp:

                # Create a graph from 'shortest path'
                pathGraph = nx.path_graph(sp_e)  # does not pass edges attributes

                # Read attributes from each edge
                for ea in pathGraph.edges():
                    # print from_node, to_node, edge's attributes
                    if ea[1] != G.edges[ea[0], ea[1]]['End_ID']:
                        flip_fid_list.append(G.edges[ea[0], ea[1]]['FID'])
        counter += 1
        print('subgraph {0} of {1}'.format(counter, subgraphs))

    flip_fid_list = set(flip_fid_list)
    print('Need to Flip Edges ID:', list(flip_fid_list))

    extr_by = processing.run("qgis:extractbyexpression", {'INPUT': split_streams, 'EXPRESSION': '"FID_split" IN ({0})'.format(str(list(flip_fid_list))[1:-1]), 'OUTPUT' : 'TEMPORARY_OUTPUT', 'FAIL_OUTPUT': 'TEMPORARY_OUTPUT'})
    flip_streams = extr_by['OUTPUT']
    not_flip_streams = extr_by['FAIL_OUTPUT']
    reverse = processing.run("native:reverselinedirection", {'INPUT': flip_streams, 'OUTPUT': 'TEMPORARY_OUTPUT'})
    flipped_streams = reverse['OUTPUT']
    processing.run("native:mergevectorlayers", {'LAYERS': [flipped_streams, not_flip_streams], 'CRS' : 'ESPG:4326', 'OUTPUT' : output})

    return output
