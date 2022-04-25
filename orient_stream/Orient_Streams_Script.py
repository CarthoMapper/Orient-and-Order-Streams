import networkx as nx
# import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
from .srtm_py.srtm import main
import os
import numpy as np
from qgis import processing
from osgeo import gdal

# rivers =r'C:\Users\vital\Desktop\Diplom\vectors\1223.shp' #'C:/Users/vital/Desktop/Diplom/vectors/test2.shp'

def linestring_to_points(line, i, j):
   return line.coords[i][j]

def extract_point(input, i):
    layer = input.copy()
    layer['x'] = layer.apply(lambda l: linestring_to_points(l['geometry'], i, 0), axis=1)
    layer['y'] = layer.apply(lambda l: linestring_to_points(l['geometry'], i, 1), axis=1)
    layer['geometry'] = gpd.points_from_xy(layer['x'], layer['y'])
    layer = layer.drop(columns=['x', 'y'])
    return layer

def orient_streams(streams, dem, field, output):
    # streams = r'C:\Users\vital\Desktop\Diplom\vectors\split_lines.shp' #C:/Users/vital/Desktop/Diplom/vectors/river_OSM1.shp
    split_streams = 'in_memory/split_streams'
    flip_streams = 'in_memory/flip_streams'
    flipped_streams = 'in_memory/flipped_streams'
    not_flip_streams = 'in_memory/not_flipped_streams'
    # gdf = 'C:/Users/vital/Desktop/Diplom/vectors/gdf.shp'
    # nodes = 'C:/Users/vital/Desktop/Diplom/vectors/nodes.shp'

    # FIRSTLY, Need to split lines with a tool 'split' in qgis or arcgis. AND get singlepart lines
    processing.run("qgis:splitwithlines", {'INPUT': streams, 'LINES': streams, 'OUTPUT': split_streams})

    rivers = gpd.read_file(split_streams)
    rivers['Line_ID'] = range(1, len(rivers.index)+1)
    n = rivers.shape[0]
    source = gpd.GeoDataFrame(crs="EPSG:4326")
    destination = gpd.GeoDataFrame(crs="EPSG:4326")
    for i in range(n):
        # rivers.iloc[[i]].to_file(river)
        df_source = extract_point(rivers.iloc[[i]], -1)
        df_destination = extract_point(rivers.iloc[[i]], 0)
        source = source.append(df_source)
        destination = destination.append(df_destination)
    source = source.assign(R=0)
    destination = destination.assign(R=1)
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
        for j in range(i+1, n):
            if all.iloc[j]['geometry'] == all.iloc[i]['geometry']:
                temp_list.append(j)
                id2_list.append(j)
        for k in temp_list:
            all.at[k+1, 'Point_ID2'] = i+1
        if all.iloc[i]['Point_ID2'] == 0:
            all.at[i + 1, 'Point_ID2'] = i + 1

    ###3###
    elevation_data = main.get_data()
    all.insert(4, 'Elev', 0)
    n = len(all)
    for i in range(n):
        h = elevation_data.get_elevation(all.geometry.y.iloc[i], all.geometry.x.iloc[i])
        all.at[i + 1, 'Elev'] = h

    geo_df2 = all.groupby(['Line_ID'])['geometry'].apply(lambda x: LineString(x.tolist()))
    geo_df2 = gpd.GeoDataFrame(geo_df2, geometry='geometry')

    gdf_source = all[all['R']==0]
    gdf_source = gdf_source[['Line_ID', 'Point_ID2']]
    gdf_source = gdf_source.rename(columns = {'Point_ID2': 'Start_ID'}, inplace = False)
    gdf_dest = all[all['R']==1]
    gdf_dest = gdf_dest[['Line_ID', 'Point_ID2', field]]
    gdf_dest = gdf_dest.rename(columns = {'Point_ID2': 'End_ID'}, inplace = False)
    geo_df2 = geo_df2.merge(gdf_source, on='Line_ID')
    geo_df2 = geo_df2.merge(gdf_dest, on='Line_ID')
    all_nodes = all.drop_duplicates(["geometry"])
    # print(all_nodes)
    # print(geo_df2)
    all_nodes.to_file(nodes)
    geo_df2.to_file(gdf)

    ###4###

    G = nx.Graph()

    for i in range(len(all_nodes)):
        G.add_node(all_nodes.iloc[i]['Point_ID2'], Elev=all_nodes.iloc[i]['Elev']) #Line_ID = all.iloc[i]['Line_ID'], geometry=all.iloc[i]['geometry']
    for i in range(len(geo_df2)):
        G.add_edge(geo_df2.iloc[i]['Start_ID'], geo_df2.iloc[i]['End_ID'], FID = geo_df2.iloc[i][field], End_ID = geo_df2.iloc[i]['End_ID'])
    flip_fid_list = ()
    counter = 0

    A = (G.subgraph(c) for c in nx.connected_components(G))
    A = list(A)
    print(A)
    subgraphs = len(list(A))

    two_degree_list = []
    for G in A:
        print(G)
        # Periphery
        D = G.degree()
        list_leaves = []
        for i in D:
            if i[1] == 1:
                list_leaves.append(i[0])
            elif i[1] == 2:
                two_degree_list.append(i[0])
        # print('Degree:', D)
        # print('List of leaf nodes:', list_leaves)

        # nodes_list = list(G.nodes(data=True))
        # edge_list = list(G.edges)
        # print('All nodes:', nodes_list)
        # print('All edges:', edge_list)

        leaves_list_with_elev = []
        l = 9999
        for i in list_leaves:
            # Добавить извлечение высоты вот сюда
            k = G.nodes[i].pop('Elev')
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
        for i in list_leaves:
            End_ID_list = []
            # Find the shortest path from node1 to node2
            # sp_l = nx.shortest_path(G, source=i, target=min_node, weight = 'Line_ID')
            sp_e = nx.all_shortest_path(G, source=i, target=min_node)
            # print('path from {0} to {1}:'.format(i, min_node), sp_e)

            # Create a graph from 'sp'
            for path in sp_e:
                pathGraph = nx.path_graph(path)  # does not pass edges attributes

                # Read attributes from each edge
                for ea in pathGraph.edges():
                    if ea[1] == G.edges[ea[0], ea[1]]['End_ID']:
                        flip_fid_list.append(G.edges[ea[0], ea[1]]['FID'])
        counter += 1
        print('subgraph {0} of {1}'.format(counter, subgraphs))

    flip_fid_list = set(flip_fid_list)
    print('Need to Flip Edges ID:', flip_fid_list)
    flip_fid_list = str(flip_fid_list)[1:-1]

    processing.run("qgis:extractbyexpression", {'INPUT': streams, 'EXPRESSION': '"{0}" IN ({1})'.format(field, flip_fid_list), 'OUTPUT' : flip_streams, 'FAIL_OUTPUT': not_flip_streams})
    processing.run("native:reverselinedirection", {'INPUT': flip_streams, 'OUTPUT': flipped_streams})
    processing.run("native:mergevectorlayers", {'LAYERS': [flipped_streams, not_flip_streams], CRS : 'ESPG:4326', 'OUTPUT' : output})
    merge_lines_list = []
    for i in two_degree_list:
        merge_lines_list.append(G.edges(i))
    return output
    # os.chdir("C:/Users/vital/Desktop/Diplom")
    # file = open('test.txt', 'w')
    # for item in flip_fid_list: file.write("%s\n" % item)
    # file.close()