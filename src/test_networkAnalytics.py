from unittest import TestCase
import networkAnalytics as na
import networkx as nx
import pprint


class TestNetworkAnalytics(TestCase):

    def _get_na(self, g=nx.Graph(), hard_coded_dns=[1, 2], connection_strategy='normal'):
        return na.NetworkAnalytics(g, hard_coded_dns, show_plots=True, connection_strategy=connection_strategy,
                                   with_evil_nodes=False, max_outbound=8, initial_connection_filter=False,
                                   simulation_protocol='bitcoin_protocol')

    def _get_graph(self):
        g = nx.Graph()
        g.add_edge(1, 2)
        g.add_edge(2, 3)
        g.add_edge(3, 4)
        g.add_edge(2, 4)
        g.add_edge(20, 1)
        g.add_edge(30, 1)
        g.add_edge(10, 1)
        g.add_edge(0, 20)
        g.add_edge(5, 6)
        g.add_edge(6, 7)
        g.add_edge(7, 8)
        g.add_edge(8, 9)
        g.add_edge(4, 5)
        return g

    def test_plot_degree(self):
        g = self._get_graph()
        n = self._get_na(g=g)
        n.plot_degree()

    def test_add_weights_to_graph(self):
        g = self._get_graph()
        n = self._get_na(g=g, connection_strategy='geo_bc')
        d = n.shortest_path_time_histogram_undirected()
        pprint.pprint(d)
