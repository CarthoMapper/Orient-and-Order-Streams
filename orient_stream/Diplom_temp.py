#!/usr/bin/env python
# coding: utf-8

import networkx as nx
import matplotlib.pyplot as plt
import networkx as nx
from osgeo import ogr
import pandas as pd
from shapely.geometry import LineString, Point
from srtm_py.srtm import main
import os
import numpy as np
from qgis import processing
from osgeo import gdal


def pixel(dx, dy, gt):
    px = gt[0]
    py = gt[3]
    rx = gt[1]
    ry = gt[5]
    x = round((dx - px)/rx)-1
    y = round((dy - py)/ry)-1
    return y, x

def extract_point(shape):
    layer = shape.copy()
    layer['x_src'] = shape['geometry']['coordinates'][0][0]
    layer['y_src'] = shape['geometry']['coordinates'][0][1]
    layer['x_dst'] = shape['geometry']['coordinates'][-1][0]
    layer['y_dst'] = shape['geometry']['coordinates'][-1][1]
    layer['FID'] = shape['properties']['FID']
    return [layer['x_src'], layer['y_src'], layer['x_dst'], layer['y_dst'], layer['FID']]

streams = r'C:\Users\vital\Desktop\Diplom\vectors\split_lines.shp' #C:/Users/vital/Desktop/Diplom/vectors/river_OSM1.shp
split_streams = 'in_memory/split_streams'
flip_streams = 'in_memory/flip_streams'
flipped_streams = 'in_memory/flipped_streams'
not_flip_streams = 'in_memory/not_flipped_streams'

def orient_streams(streams, dem, field, output):
    shape = fiona.open(streams)
    df0 = []
    for i in range(len(shape)):
        dict_shp = extract_point(shape[i])
        df0.append(dict_shp)
    df = pd.DataFrame(df0, columns =['x_src', 'y_src', 'x_dst', 'y_dst', 'FID'])
    df['Line_ID'] = range(1, len(df.index)+1)
    df_src = df[['x_src', 'y_src','FID', 'Line_ID']]
    df_dst = df[['x_dst', 'y_dst', 'FID', 'Line_ID']]
    df_src.columns = ['x', 'y', 'FID', 'Line_ID']
    df_dst.columns = ['x', 'y', 'FID', 'Line_ID']
    source = df_src.assign(R=0)
    destination = df_dst.assign(R=1)
    all = source.append(destination)

    all.insert(0, 'Point_ID', range(1, 1 + len(all)))
    all.insert(1, 'Point_ID2', 0)
    all.set_index('Point_ID', inplace=True)

    n = len(all)
    id2_list = []

    for i in range(n):
        if all.iloc[i]['Point_ID2'] != 0:
            continue
        temp_list = []
        for j in range(i+1, n):
            if all.iloc[j]['x'] == all.iloc[i]['x'] and all.iloc[j]['y'] == all.iloc[i]['y']:
                temp_list.append(j)
                id2_list.append(j)
        for k in temp_list:
            all.at[k+1, 'Point_ID2'] = i+1
        if all.iloc[i]['Point_ID2'] == 0:
            all.at[i + 1, 'Point_ID2'] = i + 1

    all.insert(3, 'geometry', [(xy) for xy in zip(all.x, all.y)])

    gdf_source = all[all['R']==0]
    gdf_source = gdf_source[['Line_ID', 'Point_ID2']]
    gdf_source = gdf_source.rename(columns = {'Point_ID2': 'Start_ID'}, inplace = False)
    gdf_dest = all[all['R']==1]
    gdf_dest = gdf_dest[['Line_ID', 'Point_ID2', 'FID']]
    gdf_dest = gdf_dest.rename(columns = {'Point_ID2': 'End_ID'}, inplace = False)
    # geo_df2 = geo_df2.merge(gdf_source, on='Line_ID')
    geo_df2 = gdf_source.merge(gdf_dest, on='Line_ID')
    all_nodes = all.drop_duplicates(["geometry"])
    print(all_nodes)
    print(geo_df2)

    DEM = r'C:\Users\vital\Desktop\Diplom\DEM\Mosaic1.tif'
    raster = gdal.Open(DEM)
    gt = raster.GetGeoTransform()
    print(all_nodes.loc[3]['x'], all_nodes.loc[3]['y'], gt)

    GG = nx.Graph()

    for i in range(len(all_nodes)):
        GG.add_node(all_nodes.iloc[i]['Point_ID2']) #Line_ID = all.iloc[i]['Line_ID'], geometry=all.iloc[i]['geometry']
    for i in range(len(geo_df2)):
        GG.add_edge(geo_df2.iloc[i]['Start_ID'], geo_df2.iloc[i]['End_ID'], FID = geo_df2.iloc[i]['FID'], End_ID = geo_df2.iloc[i]['End_ID'])
    print(5)
    flip_fid_list = []
    counter = 0
    print(GG)

    DEM = r'C:\Users\vital\Desktop\Diplom\DEM\Mosaic1.tif'
    raster = gdal.Open(DEM)
    gt = raster.GetGeoTransform()
    myarray = np.array(raster.GetRasterBand(1).ReadAsArray())

    D = GG.degree()
    list_leaves = []
    two_degree_list = []
    for i in D:
        if i[1] == 1:
            list_leaves.append(i[0])
        elif i[1] == 2:
            two_degree_list.append(i[0])
    print(list_leaves)
    for node in list_leaves:
        wkt = pixel(all_nodes.loc[node]['x'], all_nodes.loc[node]['y'], gt)
        elev = myarray[wkt[0], wkt[1]]
        GG.nodes[node]['elev'] = elev

    A = (GG.subgraph(c) for c in nx.connected_components(GG))
    A = list(A)
    print(A)
    subgraphs = len(list(A))

    for G in A:
        D = G.degree()
        list_leaves_G = []
        for i in D:
            if i[1] == 1:
                list_leaves_G.append(i[0])

        nodes_list = list(G.nodes(data=True))
        edge_list = list(G.edges)

        leaves_list_with_elev = []
        l = 9999
        for i in list_leaves_G:
            k = G.nodes[i].pop('elev')
            leaves_list_with_elev.append((i, k))
            if k < l:
                l = k
                min_node = i
        # print('leaf with min elev:', min_node)

        try:
            list_leaves.remove(min_node)
        except ValueError:
            continue
        edge_labels = nx.get_edge_attributes(G, 'Elev')
        # print(edge_labels)
        for i in list_leaves_G:
            End_ID_list = []
            # Find the shortest path from node1 to node2
            # sp_l = nx.shortest_path(G, source=i, target=min_node, weight = 'Line_ID')
            sp_e = nx.shortest_path(G, source=i, target=min_node)
            # print('path from {0} to {1}:'.format(i, min_node), sp_e)

            # Create a graph from 'sp'
            pathGraph = nx.path_graph(sp_e)  # does not pass edges attributes

            # Read attributes from each edge
            for ea in pathGraph.edges():
                #print from_node, to_node, edge's attributes
                if ea[1] != G.edges[ea[0], ea[1]]['End_ID']:
                    flip_fid_list.append(G.edges[ea[0], ea[1]]['FID'])
        counter += 1
        print('subgraph {0} of {1}'.format(counter, subgraphs))

    flip_fid_list = set(flip_fid_list)
    print('Need to Flip Edges ID:', list(flip_fid_list))

    os.chdir("C:/Users/vital/Desktop/Diplom")
    file = open('test.txt', 'w')
    for item in flip_fid_list: file.write("%s\n" % item)
    file.close()




