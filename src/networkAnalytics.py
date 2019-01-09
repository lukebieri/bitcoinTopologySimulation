from collections import Counter
import datetime
import json
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pathlib
import pprint


class NetworkAnalytics:

    def __init__(self, di_graph, hard_coded_dns, show_plots=True, connection_strategy='',
                 with_evil_nodes=False, max_outbound=8, initial_connection_filter=False,
                 simulation_protocol='bitcoin_protocol', outbound_distribution='const8'):
        """
        initialization
        """
        self.show_plots = show_plots
        self.outbound_distribution = outbound_distribution
        self.connection_strategy = connection_strategy
        self.max_outbound = max_outbound
        self.simulation_protocol = simulation_protocol
        self.initial_connection_filter = initial_connection_filter
        self.DG = di_graph
        self.HARD_CODED_DNS = hard_coded_dns
        self.avg_hop = dict()
        self.avg_dist_node_to_all_neighbours = dict()
        self.std_dist_node_to_all_neighbours = dict()
        self.var_dist_node_to_all_neighbours = dict()
        self.std_avg_dist_node_to_all_neighbours = dict()
        self.var_avg_dist_node_to_all_neighbours = dict()
        t = datetime.datetime.now()
        path = './../../data/' + str(t.year) + '_' + str(t.month) + '_' + str(t.day) + '_' + str(t.hour) + '_' +\
               str(t.minute) + '_' + str(t.second) + '_' + connection_strategy + '_evilNodes' + str(with_evil_nodes) +\
               '_' + str(outbound_distribution)
        p = pathlib.Path(path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
        self.path_results = p
        file = 'results.txt'
        self.file_path_results = p / file

    ############################
    # public functions
    ############################

    def add_conn(self, start, end):
        """
        addConn adds a connection to the network
        :param start: from which node the connection is outgoing
        :param end: where the connection is incoming
        :return: networkx directed graph
        """
        if self.DG.has_edge(start, end):
            self.DG[start][end]['weight'] += 1
        else:
            self.DG.add_edge(start, end, weight=1)
        return self.DG

    def plot_net(self):
        """
        plots the graph
        :return: success
        """
        color_map = []
        for node in self.DG:
            if node in self.HARD_CODED_DNS:
                color_map.append('red')
            else:
                color_map.append('green')
        pos, edge_labels, node_labels = self._get_graph_info()
        if self.show_plots:
            nx.draw(self.DG, pos, title='simulated bitcoin network topology', node_color=color_map)
            nx.draw_networkx_labels(self.DG, pos, labels=node_labels)
            nx.draw_networkx_edge_labels(self.DG, pos, edge_labels=edge_labels)
            plt.show()
        return True

    def remove_edge(self, start, end):
        """
        removes an edge
        :param start: beginning of the edge to be removed
        :param end: end of the edge to be removed
        :return: directed graph
        """
        if self.DG[start][end]['weight'] > 1:
            self.DG[start][end]['weight'] += -1
        else:
            self.DG.remove_edge(start, end)
        return self.DG

    def remove_node(self, node_id):
        self.DG.remove_node(node_id)
        return self.DG

    def shortest_path_length(self, output=True):
        """
        gets the shortest path lengths for any node pair within the graph
        :param output: if it should print the result
        :return: distance dictionary
        """
        distance = dict()
        for start in self.DG.node:
            distance[start] = dict()
            for end in self.DG.node:
                try:
                    distance[start][end] = nx.shortest_path_length(self.DG, source=start, target=end)
                except nx.NetworkXNoPath:
                    distance[start][end] = None
        if output:
            pprint.pprint(distance)
        return distance

    def shortest_path_histogram_dicrected(self, output=True):
        """
        makes a histogram plot with the shortest paths
        :param output: showing more detail in console
        :return: success
        """
        distance = self.shortest_path_length(output=False)
        no_connection = list()
        distance_dict = dict()
        for start, value in distance.items():
            for end, path_length in value.items():
                if start == end:
                    continue
                if path_length is None:
                    # no connection between nodes
                    no_connection.append((start, end))
                else:
                    if not path_length in distance_dict:
                        distance_dict[path_length] = 1
                    else:
                        distance_dict[path_length] += 1
        if output:
            print('### detailed information about the shortest path length histogram')
            print('exact numbers: ', distance_dict)
            print('elements without any connection:')
            pprint.pprint(no_connection)
        hops = sorted(distance_dict)
        count = [distance_dict[x] for x in hops]
        plt.bar(hops, count, width=0.8, bottom=None, align='center')
        plt.xticks(hops, hops)
        plt.xlabel('number of hops')
        plt.ylabel('number of node pairs')
        plt.title('shortest paths between any nodes in the network')
        if self.show_plots:
            plt.show()
        return True

    @property
    def shortest_path_length_all_pair(self):
        # return sp.optimized_shortest_path_length_all_pair(self.DG, undirected=True)
        if (self.connection_strategy is 'geo_bc') or (self.connection_strategy is 'no_geo_bc'):
            self.add_weights_to_graph()
            distance = dict(nx.all_pairs_dijkstra_path_length(self.DG))
        else:
            if self.DG.is_directed():
                distance = dict(nx.all_pairs_shortest_path_length(self.DG.to_undirected()))
            else:
                distance = dict(nx.all_pairs_shortest_path_length(self.DG))

        if self.initial_connection_filter:
            for node_start in list(distance.keys()):
                if self.DG.node[node_start][self.simulation_protocol].number_outbound() < self.max_outbound:
                    distance.pop(node_start, None)
                    continue
                for node_end in list(distance[node_start].keys()):
                    if self.DG.node[node_end][self.simulation_protocol].number_outbound() < self.max_outbound:
                        distance[node_start].pop(node_end, None)
        return distance

    @property
    def length_summary_undirected(self):
        distance = self.shortest_path_length_all_pair

        # average path length of particular node to all other nodes
        avg_distance_of_node = dict()
        std_distance_of_node = dict()
        var_distance_of_node = dict()

        # overall length summary
        length_summary = dict()
        for start_node, values in distance.items():
            if len(values.values()) > 1:
                avg_distance_of_node[start_node] = sum(values.values()) / float(len(values.values()) - 1)  # mean without itself
                std_distance_of_node[start_node] = np.std(np.array(list(values.values())))
                var_distance_of_node[start_node] = np.var(np.array(list(values.values())))
            for end_node, path_length in values.items():
                if path_length not in length_summary:
                    length_summary[path_length] = 1
                else:
                    length_summary[path_length] += 1
        not_connected_count = length_summary.pop(0, None)

        self.avg_dist_node_to_all_neighbours[len(self.DG.nodes)] = avg_distance_of_node
        self.std_dist_node_to_all_neighbours[len(self.DG.nodes)] = std_distance_of_node
        self.var_dist_node_to_all_neighbours[len(self.DG.nodes)] = var_distance_of_node

        data_list = list()
        for key, value in length_summary.items():
            data_list.extend([key] * value)

        self.std_avg_dist_node_to_all_neighbours[len(self.DG.nodes)] = np.std(np.array(data_list))
        self.var_avg_dist_node_to_all_neighbours[len(self.DG.nodes)] = np.var(np.array(data_list))

        if (self.connection_strategy is 'geo_bc') or (self.connection_strategy is 'no_geo_bc'):
            self.avg_time_dist_node_to_all_neighbours_plot()
        else:
            self.avg_dist_node_to_all_neighbours_plot()

        return length_summary, not_connected_count, self.std_avg_dist_node_to_all_neighbours[len(self.DG.nodes)],\
            self.var_avg_dist_node_to_all_neighbours[len(self.DG.nodes)]

    def avg_time_dist_node_to_all_neighbours_plot(self, network_size=None):
        if (network_size is None) or (network_size not in self.avg_dist_node_to_all_neighbours.keys()):
            network_size = max(self.avg_dist_node_to_all_neighbours.keys())
            if network_size < 1:
                print('avg_dist_node_to_all_neighbours has no values stored and we could not plot a graph')
                return None
        std = np.round(np.std(np.array(list(self.avg_dist_node_to_all_neighbours[network_size].values()))), 3)
        var = np.round(np.var(np.array(list(self.avg_dist_node_to_all_neighbours[network_size].values()))), 3)
        std_var_text = "std = " + str(std) + "\n" +\
                       "var = " + str(var) + "\n" +\
                       str(self.connection_strategy) + "\n" +\
                       str(self.outbound_distribution)
        data = [round(x, -1) for x in self.avg_dist_node_to_all_neighbours[network_size].values()]
        data_dict = Counter(data)
        x_avg = sorted(data_dict)
        y_count = [data_dict[x] for x in x_avg]
        plt.plot(x_avg, y_count, 'o')
        plt.xlabel(r'average $ms$ from one node to all  the others (resolution: $10 ms$)')
        plt.ylabel('number of nodes')
        plt.text(max(x_avg) * 0.85, max(y_count) * 0.8, std_var_text)
        # plt.xlim(1, 6)
        if self.initial_connection_filter:
            plt.title('average path time for network with ' + str(sum(y_count)) + ' nodes')
        else:
            plt.title('average path time for network with ' + str(network_size) + ' nodes')
        plt.ylim(bottom=0)
        plt.savefig(self.path_results / pathlib.Path('average hops for network with ' + str(network_size) + ' nodes' +
                                                     '.png'))
        export_text = r'average $ms$ from one node to all  the others (resolution: $50 ms$): ' + str(x_avg) + '\n' + \
                      'number of nodes: ' + str(y_count) + '\n' + std_var_text
        with open(self.path_results / pathlib.Path('average hops for network with ' + str(network_size) + ' nodes'
                                                   + '.txt'), "a") as my_file:
            my_file.write(export_text)
        if self.show_plots:
            plt.show()
        return

    def avg_dist_node_to_all_neighbours_plot(self, network_size=None):
        if (network_size is None) or (network_size not in self.avg_dist_node_to_all_neighbours.keys()):
            network_size = max(self.avg_dist_node_to_all_neighbours.keys())
            if network_size < 1:
                print('avg_dist_node_to_all_neighbours has no values stored and we could not plot a graph')
                return None
        std = np.round(np.std(np.array(list(self.avg_dist_node_to_all_neighbours[network_size].values()))), 3)
        var = np.round(np.var(np.array(list(self.avg_dist_node_to_all_neighbours[network_size].values()))), 3)
        std_var_text = "std = " + str(std) + "\n" +\
                       "var = " + str(var) + "\n" +\
                       str(self.connection_strategy) + "\n" +\
                       str(self.outbound_distribution)
        data = [round(x * 2, 1) / 2.0 for x in self.avg_dist_node_to_all_neighbours[network_size].values()]
        data_dict = Counter(data)
        x_avg = sorted(data_dict)
        y_count = [data_dict[x] for x in x_avg]
        plt.plot(x_avg, y_count, 'o')
        plt.xlabel('average hops from one node to all  the others (resolution: 0.05)')
        plt.ylabel('number of nodes')
        plt.text(1.2, max(y_count) * 0.85, std_var_text)
        plt.xlim(1, 6)
        if self.initial_connection_filter:
            plt.title('average hops for network with ' + str(sum(y_count)) + ' nodes')
        else:
            plt.title('average hops for network with ' + str(network_size) + ' nodes')
        plt.ylim(bottom=0)
        plt.savefig(self.path_results / pathlib.Path('average hops for network with ' + str(network_size) + ' nodes' +
                                                     '.png'))
        export_text = 'average hops from one node to all  the others (resolution: 0.05): ' + str(x_avg) + '\n' + \
                      'number of nodes: ' + str(y_count) + '\n' + std_var_text
        with open(self.path_results / pathlib.Path('average hops for network with ' + str(network_size) + ' nodes'
                                                   + '.txt'), "a") as my_file:
            my_file.write(export_text)
        if self.show_plots:
            plt.show()
        return

    def shortest_path_histogram_undirected(self, output=True, is_final=False):
        length_summary, not_connected_count, std, var = self.length_summary_undirected
        self.avg_path_length_log(length_summary=length_summary)

        std_round = np.round(std, 3)
        var_round = np.round(var, 3)

        var_std_text = "std = " + str(std_round) + "\n" \
                       "var = " + str(var_round) + "\n" +\
                       str(self.connection_strategy) + "\n" +\
                       str(self.outbound_distribution)
        if output:
            print('### detailed information about the shortest path length histogram')
            print('exact numbers: ')
            pprint.pprint(length_summary)
            print('number of initial DNS servers: ' + str(len(self.HARD_CODED_DNS)))
            print('number of nodes in the network: ' + str(len(self.DG.nodes)))
            print('number of edges in the network: ' + str(len(self.DG.edges())))
            print('pairs without any connection:')
            print(not_connected_count)
        hops = sorted(length_summary)
        count = [length_summary[x] for x in hops]
        plt.bar(hops, count, width=0.8, bottom=None, align='center')
        plt.xticks(hops, hops)
        plt.xlabel('number of hops')
        plt.ylabel('number of node pairs')
        plt.text(.8, max(count) * 0.85, var_std_text)
        plt.xlim(0.5, 7.5)
        plt.title('shortest paths between any 2 nodes - ' + str(len(self.DG.nodes)) + ' nodes')
        if not is_final:
            plt.savefig(self.path_results / pathlib.Path('shortest paths between any nodes - ' +
                                                         str(len(self.DG.nodes)) + ' nodes' + '.png'))
        else:
            plt.savefig(
                self.path_results / pathlib.Path('final shortest paths between any nodes - ' +
                                                 str(len(self.DG.nodes)) + ' nodes' + '.png'))
        export_text = 'number of hops: ' + str(hops) + '\n' + \
                      'number of node pairs: ' + str(count) + '\n' + var_std_text
        if not is_final:
            with open(self.path_results / pathlib.Path('shortest paths between any nodes - ' +
                                                       str(len(self.DG.nodes)) + ' nodes' + '.txt'), "a") as my_file:
                my_file.write(export_text)
        else:
            with open(self.path_results / pathlib.Path('final shortest paths between any nodes - ' +
                                                       str(len(self.DG.nodes)) + ' nodes' + '.txt'), "a") as my_file:
                my_file.write(export_text)

        if self.show_plots:
            plt.show()
        return True

    def shortest_path_time_histogram_undirected(self, output=True, is_final=False):
        length_summary, not_connected_count, std, var = self.length_summary_undirected
        self.avg_path_length_log(length_summary=length_summary)

        std_round = np.round(std, 3)
        var_round = np.round(var, 3)

        var_std_text = "std = " + str(std_round) + "\n" \
                       "var = " + str(var_round) + "\n" +\
                       str(self.connection_strategy) + "\n" +\
                       str(self.outbound_distribution)
        if output:
            print('### detailed information about the shortest path time length histogram')
            print('exact numbers: ')
            pprint.pprint(length_summary)
            print('number of initial DNS servers: ' + str(len(self.HARD_CODED_DNS)))
            print('number of nodes in the network: ' + str(len(self.DG.nodes)))
            print('number of edges in the network: ' + str(len(self.DG.edges())))
            print('pairs without any connection:')
            print(not_connected_count)
        length_summary_rounded = dict()
        for key, value in length_summary.items():
            if round(key * 2, -2) / 2 not in length_summary_rounded:
                length_summary_rounded[round(key * 2, -2) / 2] = length_summary[key]
            else:
                length_summary_rounded[round(key * 2, -2) / 2] += length_summary[key]
        milli_sec = sorted(length_summary_rounded.keys())
        count = [length_summary_rounded[x] for x in milli_sec]
        plt.plot(milli_sec, count, 'om')
        # plt.xticks(milli_sec, milli_sec)
        plt.xlabel(r'$ms$ (resolution: $50 ms$)')
        plt.ylabel('number of node pairs')
        plt.text(max(milli_sec) * 0.8, max(count) * 0.85, var_std_text)
        # plt.xlim(0.5, 7.5)
        plt.title('shortest paths between any 2 nodes - ' + str(len(self.DG.nodes)) + ' nodes')
        if not is_final:
            plt.savefig(self.path_results / pathlib.Path('shortest paths between any nodes - ' +
                                                         str(len(self.DG.nodes)) + ' nodes' + '.png'))
        else:
            plt.savefig(
                self.path_results / pathlib.Path('final shortest paths between any nodes - ' +
                                                 str(len(self.DG.nodes)) + ' nodes' + '.png'))
        export_text = 'milli_sec: ' + str(milli_sec) + '\n' + \
                      'number of node pairs: ' + str(count) + '\n' + var_std_text
        if not is_final:
            with open(self.path_results / pathlib.Path('shortest paths between any nodes - ' +
                                                       str(len(self.DG.nodes)) + ' nodes' + '.txt'), "a") as my_file:
                my_file.write(export_text)
        else:
            with open(self.path_results / pathlib.Path('final shortest paths between any nodes - ' +
                                                       str(len(self.DG.nodes)) + ' nodes' + '.txt'), "a") as my_file:
                my_file.write(export_text)

        if self.show_plots:
            plt.show()
        return True

    def avg_path_length_log(self, length_summary=None):
        if length_summary is None:
            length_summary, _ = self.length_summary_undirected
        n_nodes = len(self.DG.nodes)
        self.avg_hop[n_nodes] = 0.0
        connections = 0
        for key, value in length_summary.items():
            self.avg_hop[n_nodes] += key * value
            connections += value
        self.avg_hop[n_nodes] = self.avg_hop[n_nodes] / connections
        return self.avg_hop[n_nodes]

    def avg_path_length_plot(self, max_outbound_connections) -> int:
        lists = sorted(self.avg_hop.items())
        x, y = zip(*lists)
        plt.plot(x, y, '--bo')
        plt.xticks(x, x)
        plt.yticks(y, [round(p, 2) for p in y])
        plt.xlabel('number of nodes in the network')
        plt.ylabel('average hops over all shortest paths')
        plt.title('average hops for different network sizes')
        export_text = "### data of average hops in Network\n" + \
                      "max_outbound_connections: " + str(max_outbound_connections) + "\n" +\
                      "avg: " + str(y) + "\n" \
                      "nodes: " + str(x) + "\n"
        with open(self.file_path_results, "a") as my_file:
            my_file.write(export_text)
        plt.savefig(self.path_results / pathlib.Path('avg_hops_for_different_network_sizes_' +
                                                     str(max_outbound_connections) + '.png'))
        if self.show_plots:
            plt.show()
        print(export_text)
        return max(y)

    def save_graph(self):
        if self.DG.is_directed:
            nx.write_gexf(self.DG.to_undirected(), self.path_results / pathlib.Path('graph.gexf'))
        else:
            nx.write_gexf(self.DG, self.path_results / pathlib.Path('graph.gexf'))

    def plot_degree(self):
        degree_list = [self.DG.degree(node) for node in self.DG.nodes]
        var = np.round(np.var(np.array(degree_list)), 3)
        std = np.round(np.std(np.array(degree_list)), 3)
        degree_dict = Counter(degree_list)
        x = sorted(degree_dict)
        y = [degree_dict[ii] for ii in x]
        plt.plot(x, y, 'o')
        plt.xlabel('degree')
        plt.ylabel('number of nodes')
        var_std_text = "var = " + str(var) + "\n" + \
                       "std =" + str(std) + "\n" + \
                       str(self.connection_strategy) + "\n" + \
                       str(self.outbound_distribution)
        plt.text(max(max(x), 125) * 0.8, max(y) * 0.85, var_std_text)
        plt.title('degree distribution in the network - ' + str(len(self.DG.nodes)) + ' nodes')
        if max(x) <= 125:
            plt.xlim(0, 125)
        plt.savefig(self.path_results / pathlib.Path('degree distribution - ' +
                                                     str(len(self.DG.nodes)) + ' nodes' + '.png'))
        export_text = "### data of degree distribution in the network\n" + \
                      "max_outbound_connections: " + str(self.max_outbound) + "\n" + \
                      "number of nodes: " + str(y) + "\n" \
                      "degree: " + str(x) + "\n" + \
                      var_std_text
        with open(self.path_results / pathlib.Path('degree distribution - ' +
                                                   str(len(self.DG.nodes)) + ' nodes' + '.txt'), "a") as my_file:
            my_file.write(export_text)
        if self.show_plots:
            plt.show()

    def add_weights_to_graph(self, filepath='ping.json') -> bool:
        d = self._get_ping_information(filepath)
        data: dict = d['data']
        bubbles: int = len(data['continentID_continent'])
        for start, end in self.DG.edges():
            if start % bubbles == end % bubbles:
                # connection within the same bubble
                # self.DG[start][end]['weight'] = data['inter_continent_distance_const']
                # self.DG[start][end]['weight'] = data['inter_continent_distance'][str(start % bubbles)]
                self.DG[start][end]['weight'] = max(np.random.normal(data['inter_continent_distance'][str(start % bubbles)],
                                                                     data['inter_continent_distance_sigma'][str(start % bubbles)], 1).astype(int)[0], 1)
            else:
                # connection between two bubbles
                if start % bubbles < end % bubbles:
                    key = str(start % bubbles) + '-' + str(end % bubbles)
                else:
                    key = str(end % bubbles) + '-' + str(start % bubbles)
                # self.DG[start][end]['weight'] = data['continent_distance_const']
                self.DG[start][end]['weight'] = max(np.random.normal(data['continent_distance'][key],
                                                                     data['continent_distance_sigma'][key], 1).astype(int)[0], 1)
        return True

    ############################
    # private functions
    ############################

    def _get_ping_information(self, filepath: str) -> dict:
        with open(filepath) as json_data:
            d = json.load(json_data)
        return dict(d)

    def _get_graph_info(self):
        """
        investigates the graph closer to return information for plotting
        :return: position of the nodes, edge labels, node labels
        """
        pos = nx.spring_layout(self.DG)
        edge_labels = nx.get_edge_attributes(self.DG, 'weight')
        node_labels = dict()
        for idx, node in enumerate(self.DG.nodes()):
            # node_labels[node] = 'id: ' + str(node)
            node_labels[node] = str(node)
        return pos, edge_labels, node_labels
