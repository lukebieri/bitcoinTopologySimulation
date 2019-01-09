from unittest import TestCase
import simulation
import sys


class TestSimulation(TestCase):

    def _get_simulation(self, simulation_type='bitcoin_protocol', MAX_OUTBOUND_CONNECTIONS=8, with_evil_nodes=False,
                        show_plots=True, connection_strategy: str = 'p2c_max', initial_connection_filter: bool = False,
                        outbound_distribution='const8_125'):
        return simulation.Simulation(simulation_type=simulation_type, MAX_OUTBOUND_CONNECTIONS=MAX_OUTBOUND_CONNECTIONS, with_evil_nodes=with_evil_nodes,
                                     show_plots=show_plots, connection_strategy=connection_strategy, initial_connection_filter=initial_connection_filter,
                                     outbound_distribution=outbound_distribution)

    def test__new_node_connects_to_network(self):
        b = self._get_simulation(outbound_distribution='uniform_1_max')
        for ii in range(1000):
            b.DG.add_edge(0, ii)
        b.DG_last_id = len(b.DG) + 1
        b._new_node_connects_to_network()
        b._new_node_connects_to_network()
        b._new_node_connects_to_network()
        for ii in range(b.DG_last_id, b.DG_last_id + 1000):
            b._new_node_connects_to_network()
            if (b.DG.node[len(b.DG.nodes())-1]['bitcoin_protocol'].MAX_OUTBOUND_CONNECTIONS > 200) and \
               (b.DG.node[len(b.DG.nodes())-1]['bitcoin_protocol'].MAX_TOTAL_CONNECTIONS == sys.maxsize):
                break
            if ii == b.DG_last_id + 999:
                self.fail(msg='simulation: _get_outbound_connection_size uniform_1_max did not work properly')
        self.assertTrue(True, msg='simulation: _get_outbound_connection_size uniform_1_max has correct boundaries')

