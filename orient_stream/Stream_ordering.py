import networkx as nx

G = nx.read_shp(r'C:\Users\vital\Desktop\Diplom\vectors\flip_riv.shp')
D = G.degree()
list_leaves = []
for i in D:
    if i[1] == 0:
        list_leaves.append(i[0])
print(list_leaves)
# G = nx.Graph(G)

# A = (G.subgraph(c) for c in nx.connected_components(G))
# A = list(A)
# print(A)
# subgraphs = len(list(A))



# subgraphs_leaves = []
# for G in A:
#     print(G)
#     # Periphery
#     D = G.degree()
#     list_leaves = []
#     for i in D:
#         if i[1] == 1:
#             list_leaves.append(i[0])
#     # print('Degree:', D)
#     # print('List of leaf nodes:', list_leaves)
#
#     nodes_list = list(G.nodes(data=True))
#     edge_list = list(G.edges)
#     # print('All nodes:', nodes_list)
#     # print('All edges:', edge_list)
#
#     CC = nx.closeness_centrality(G)
#     # print('Closeness centrality dict:', CC)
#
#     leaves_list_with_elev = []
#     l = 9999
#     for i in list_leaves:
#         k = G.nodes[i].pop('Elev')
#         leaves_list_with_elev.append((i, k))
#         if k < l:
#             l = k
#             min_node = i
#     # print('leaf with min elev:', min_node)
#
#     try:
#         list_leaves.remove(min_node)
#     except ValueError:
#         continue
#     sub_l = {min_node: list_leaves}
#     subgraphs_leaves.append(sub_l)
#     # edge_labels = nx.get_edge_attributes(G, 'Elev')
#     # print(edge_labels)
#     for i in list_leaves:
#         End_ID_list = []
#         # Find the shortest path from node1 to node2
#         # sp_l = nx.shortest_path(G, source=i, target=min_node, weight = 'Line_ID')
#         sp_e = nx.shortest_path(G, source=i, target=min_node)
#         # print('path from {0} to {1}:'.format(i, min_node), sp_e)
#
#         # Create a graph from 'sp'
#         pathGraph = nx.path_graph(sp_e)  # does not pass edges attributes
#
#         # Read attributes from each edge
#         for ea in pathGraph.edges():
#             #print from_node, to_node, edge's attributes
#             # print(ea, G.edges[ea[0], ea[1]])
#             if ea[1] == G.edges[ea[0], ea[1]]['End_ID']:
#                 flip_fid_list.append(G.edges[ea[0], ea[1]]['FID'])
#     counter += 1
#     print('subgraph {0} of {1}'.format(counter, subgraphs))
# print(subgraphs_leaves)