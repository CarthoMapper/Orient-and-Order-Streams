import networkx as nx
import math
from osgeo import ogr
from qgis import processing

def streams_ordering(rivers, output):
    processing.run("qgis:advancedpythonfieldcalculator", {'INPUT': rivers, 'FIELD_NAME': 'length', 'FIELD_TYPE': 1, 'FIELD_LENGTH': 20, 'FORMULA': '$length/1000', 'OUTPUT': rivers})
    GG = nx.read_shp(rivers)

    nx.set_node_attributes(GG, 0, 'Shrive')
    nx.set_node_attributes(GG, 0, 'Stahler')
    nx.set_node_attributes(GG, 0, 'Rzhanitsyn')
    nx.set_node_attributes(GG, 0, 'Scheideg')
    nx.set_node_attributes(GG, 0, 'temp')
    l = [x for x in GG.nodes() if GG.out_degree(x) == 1 and GG.in_degree(x) == 0]
    k = [x for x in GG.nodes() if GG.out_degree(x) == 0 and GG.in_degree(x) == 1]

    GG = GG.to_undirected(as_view=True)
    A = (GG.subgraph(c) for c in nx.connected_components(GG))
    A = list(A)

    # Rzhanitsyn ordering

    for G in A:
        for i in k:
            if G.has_node(i):
                min_node = i
        leaves = []
        for j in l:
            if G.has_node(j):
                leaves.append(j)

        for leaf in leaves:
            G.nodes[leaf]['Rzhanitsyn'] = 1
            sp_e = nx.shortest_path(G, source=leaf, target=min_node)

            for i in range(1, len(sp_e)):
                G.nodes[sp_e[i]]['Rzhanitsyn'] = G.nodes[sp_e[i - 1]]['Rzhanitsyn']
                G.nodes[sp_e[i]]['temp'] = G.nodes[sp_e[i - 1]]['temp']
                if G.degree[sp_e[i]] > 2:
                    nbrs = [n for n in G.neighbors(sp_e[i])]
                    inflow = []
                    inflow.extend(nbrs)
                    inflow.remove(sp_e[i - 1])
                    if len(nbrs) > 2:
                        inflow.remove(sp_e[i + 1])
                        nbrs.remove(sp_e[i + 1])
                    G.nodes[sp_e[i]]['Rzhanitsyn'] = max(G.nodes[sp_e[i - 1]]['Rzhanitsyn'],
                                                         G.nodes[inflow[0]]['Rzhanitsyn'])
                    G.nodes[sp_e[i]]['temp'] = max(G.nodes[sp_e[i - 1]]['temp'], G.nodes[inflow[0]]['temp'])
                    if G.nodes[inflow[0]]['Rzhanitsyn'] == 0:
                        continue
                    elif G.nodes[inflow[0]]['Rzhanitsyn'] == G.nodes[sp_e[i - 1]]['Rzhanitsyn']:
                        G.nodes[sp_e[i]]['Rzhanitsyn'] += 1
                        G.nodes[sp_e[i]]['temp'] = G.nodes[sp_e[i - 1]]['Rzhanitsyn'] * 2
                        continue
                    elif G.nodes[inflow[0]]['temp'] >= G.nodes[sp_e[i]]['Rzhanitsyn'] - 2:
                        G.nodes[sp_e[i]]['temp'] += 1
                    if G.nodes[sp_e[i]]['temp'] / G.nodes[sp_e[i]]['Rzhanitsyn'] == 2:
                        G.nodes[sp_e[i]]['Rzhanitsyn'] += 1
        for m in G.nodes():
            del G.nodes[m]['temp']
    # Shrive and Scheidegger ordering

    for G in A:
        for i in k:
            if G.has_node(i):
                min_node = i
        leaves = []
        for j in l:
            if G.has_node(j):
                leaves.append(j)

        for leaf in leaves:
            G.nodes[leaf]['Shrive'] = 1
            sp_e = nx.shortest_path(G, source=leaf, target=min_node)

            for i in range(1, len(sp_e)):
                G.nodes[sp_e[i]]['Shrive'] = G.nodes[sp_e[i - 1]]['Shrive']
                if G.degree[sp_e[i]] > 2:
                    nbrs = [n for n in G.neighbors(sp_e[i])]
                    inflow = []
                    inflow.extend(nbrs)
                    inflow.remove(sp_e[i - 1])
                    if len(nbrs) > 2:
                        inflow.remove(sp_e[i + 1])
                        nbrs.remove(sp_e[i + 1])
                    G.nodes[sp_e[i]]['Shrive'] = max(G.nodes[sp_e[i - 1]]['Shrive'], G.nodes[inflow[0]]['Shrive'])
                    if G.nodes[inflow[0]]['Shrive'] == 0:
                        continue
                    summ = 0
                    for nbr in nbrs:
                        summ += G.nodes[nbr]['Shrive']
                    G.nodes[sp_e[i]]['Shrive'] = summ
            for i in range(len(sp_e)):
                G.nodes[sp_e[i]]['Scheideg'] = float('{:.2f}'.format(math.log2(G.nodes[sp_e[i]]['Shrive']) + 1))

    # Stahler ordering

    for G in A:
        for i in k:
            if G.has_node(i):
                min_node = i
        leaves = []
        for j in l:
            if G.has_node(j):
                leaves.append(j)

        for leaf in leaves:
            G.nodes[leaf]['Stahler'] = 1
            sp_e = nx.shortest_path(G, source=leaf, target=min_node)
            #         pathGraph = nx.path_graph(sp_e)
            #         print(sp_e[1])
            for i in range(1, len(sp_e)):
                G.nodes[sp_e[i]]['Stahler'] = G.nodes[sp_e[i - 1]]['Stahler']
                if G.degree[sp_e[i]] > 2:
                    nbrs = [n for n in G.neighbors(sp_e[i])]
                    inflow = []
                    inflow.extend(nbrs)
                    inflow.remove(sp_e[i - 1])
                    if len(nbrs) > 2:
                        inflow.remove(sp_e[i + 1])
                        nbrs.remove(sp_e[i + 1])
                    G.nodes[sp_e[i]]['Stahler'] = max(G.nodes[sp_e[i - 1]]['Stahler'], G.nodes[inflow[0]]['Stahler'])
                    if G.nodes[inflow[0]]['Stahler'] == 0:
                        continue
                    if G.nodes[inflow[0]]['Stahler'] == G.nodes[sp_e[i - 1]]['Stahler']:
                        G.nodes[sp_e[i]]['Stahler'] = (G.nodes[sp_e[i - 1]]['Stahler'] + 1)
        print(G.edges(data=True))
        weighted_G = nx.Graph()
        for data in G.edges(data=True):
            weighted_G.add_edge(data[0], data[1], weight=data[2]['length'])

    nx.write_shp(G, output)

    return r'{0}/edges.shp'.format(output)