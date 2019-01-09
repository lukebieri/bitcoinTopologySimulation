import BitcoinNode as bn
from math import ceil
import networkAnalytics as na
import networkx as nx
import numpy as np
import Power2Choices as p2c
import pprint
import random
import sys


class Simulation:

    simulation_protocol: str
    simulation_time: float
    DG_last_id: int

    def __init__(self, simulation_type='bitcoin_protocol', MAX_OUTBOUND_CONNECTIONS=8, with_evil_nodes=False,
                 show_plots=True, connection_strategy: str = 'p2c_max', initial_connection_filter: bool = False,
                 outbound_distribution='const8_125', data={}):  # bitcoin_protocol power_2_choices
        self.MAX_OUTBOUND_CONNECTIONS = MAX_OUTBOUND_CONNECTIONS
        self.outbound_distribution = outbound_distribution
        self.evil_nodes_id = list()
        if with_evil_nodes:
            self.evil_nodes_percentage = .0025
        else:
            self.evil_nodes_percentage = 0
        self.data = data
        self.DG = nx.Graph()
        self.connection_strategy = connection_strategy
        self.DG_last_id = 0
        self.NUMBER_FIXED_DNS = 3
        self.FIXED_DNS = range(self.NUMBER_FIXED_DNS)
        self.simulation_time = 0.0  # seconds
        self.simulation_protocol = simulation_type
        self.whiteboard = na.NetworkAnalytics(self.DG, self.FIXED_DNS, show_plots=show_plots,
                                              connection_strategy=connection_strategy, with_evil_nodes=with_evil_nodes,
                                              max_outbound=MAX_OUTBOUND_CONNECTIONS,
                                              initial_connection_filter=initial_connection_filter,
                                              simulation_protocol=simulation_type,
                                              outbound_distribution=outbound_distribution)
        self._initialize_fixed_dns_servers()

        # if a node goes offline and online again it does not reconnect to the initial dns servers
        self.offline_nodes_reconnect = True
        self.offline_nodes = list()

    ############################
    # public functions
    ############################

    def run(self, t_start=1, t_end=60, n_iterations=124, plot_first_x_graphs=10,
            avg_paths_after_n_iterations=[10, 25, 50, 75, 100, 125, 150, 175, 200],
            MAX_OUTBOUND_CONNECTIONS=8, numb_nodes=600):
        self.MAX_OUTBOUND_CONNECTIONS = MAX_OUTBOUND_CONNECTIONS
        max_growth_rate = 0.05
        max_reconnect_rate = 0.04
        max_die_rate = 0.01
        finish_simulation_counter_max = 2000
        finish_simulation_counter = 0

        for ii, t in enumerate(list(np.linspace(t_start, t_end, n_iterations))):
            self.simulation_time = t
            print('simulation time: ' + str(round(self.simulation_time, 2))
                  + ', iteration: ' + str(ii)
                  + ' of ' + str(n_iterations)
                  + ', with ' + str(len(self.DG.nodes)) + ' nodes')
            for node_id in self.DG.nodes:
                self._process_envelopes(node_id)

            # some new nodes join the network or get offline
            if finish_simulation_counter == 0:
                number_of_dying_nodes = random.randint(0, ceil(max_die_rate * len(self.DG.nodes)))
                for node_id in random.choices(list(self.DG.nodes), k=number_of_dying_nodes):
                    if node_id in self.FIXED_DNS:
                        continue
                    if node_id not in list(self.DG.nodes):
                        continue
                    self._delete_node(node_id, save_offline_node=self.offline_nodes_reconnect)
                number_of_new_nodes = max(5, random.randint(0, ceil(max_growth_rate * len(self.DG.nodes))))
                for _ in range(number_of_new_nodes):
                    self._new_node_connects_to_network()

                if self.offline_nodes_reconnect is True:
                    reconnection_number = random.randint(0, int(max_reconnect_rate * len(self.offline_nodes)))
                    for _ in range(reconnection_number):
                        self._offline_node_gets_online(pop_random_element_from_list(self.offline_nodes))
            else:
                finish_simulation_counter += 1
                if finish_simulation_counter > finish_simulation_counter_max:
                    if self.outbound_distribution is 'hacky_1':
                        self._hacky_1()
                    self.whiteboard.plot_degree()
                    if (self.connection_strategy is 'geo_bc') or (self.connection_strategy is 'no_geo_bc'):
                        self.whiteboard.shortest_path_time_histogram_undirected(is_final=True)
                    else:
                        self.whiteboard.shortest_path_histogram_undirected(is_final=True)
                    return self.whiteboard.avg_path_length_plot(self.MAX_OUTBOUND_CONNECTIONS)

            # plot state of the net
            if (ii < plot_first_x_graphs) and (finish_simulation_counter == 0):
                self.whiteboard.plot_net()

            if (ii in avg_paths_after_n_iterations) and (finish_simulation_counter == 0):
                # self.whiteboard.avg_path_length_log()
                self.whiteboard.plot_degree()
                if (self.connection_strategy is 'geo_bc') or (self.connection_strategy is 'no_geo_bc'):
                    self.whiteboard.shortest_path_time_histogram_undirected()
                else:
                    self.whiteboard.shortest_path_histogram_undirected()

            if (len(self.DG.node) > numb_nodes) and (finish_simulation_counter == 0):
                # self.whiteboard.shortest_path_histogram_undirected()
                # self.whiteboard.avg_path_length_plot(self.MAX_OUTBOUND_CONNECTIONS)
                # self.whiteboard.save_graph()
                finish_simulation_counter += 1


    ############################
    # private functions
    ############################

    def _hacky_1(self) -> bool:
        for node in random.sample(self.DG.nodes(), round(len(self.DG.nodes()) * 0.1)):
            self.DG.node[node][self.simulation_protocol].MAX_OUTBOUND_CONNECTIONS = 600  # round(len(self.DG.nodes()) * 0.1)
            self.DG.node[node][self.simulation_protocol].MAX_TOTAL_CONNECTIONS = sys.maxsize

        ii = 0
        while True:
            ii += 1
            self.simulation_time += 0.6
            print('postprocess simulation time: ' + str(round(self.simulation_time, 2))
                  + ', iteration: ' + str(ii)
                  + ', with ' + str(len(self.DG.nodes)) + ' nodes')
            outbound_is_full = True
            for node_id in self.DG.nodes():
                self._process_envelopes(node_id)
                outbound_is_full = outbound_is_full and self.DG.node[node_id][
                    self.simulation_protocol].outbound_is_full()
            if outbound_is_full:
                return True

    def _process_envelopes(self, node_id):
        envelopes = self.DG.node[node_id][self.simulation_protocol].interval_processes(
            self.simulation_time)
        tmp_envelope = list()
        for envelope in envelopes:
            # validate an envelope
            if envelope is None:
                raise ValueError("envelope is None")
            if envelope['sender'] != node_id:
                raise ValueError("envelope['sender'] = " + str(envelope['sender']))
            if envelope['receiver'] not in self.DG.nodes:
                continue  # new connection question

            # parse envelope to check action
            if self.simulation_protocol == 'bitcoin_protocol':
                if envelope['connect_as_outbound'] == 'can_I_send_you_stuff':
                    self._node_updates_outbound_connection(envelope['sender'], envelope=envelope)
            elif self.simulation_protocol == 'power_2_choices':
                if envelope['whats_your_degree'] is True:
                    if len(tmp_envelope) == 1:
                        if tmp_envelope[0]['sender'] == envelope['sender']:
                            tmp_envelope.append(envelope)
                            self._node_updates_outbound_connection(envelope['sender'], envelope=tmp_envelope)
                        tmp_envelope = list()
                    else:
                        tmp_envelope.append(envelope)

            if envelope['get_address'] is True:
                self._get_addresses_from_neighbour(envelope['sender'], envelope=envelope)
            elif envelope['kill_connection'] is True:
                answer_envelope = self.DG.node[envelope['receiver']][self.simulation_protocol].receive_message(
                    self.simulation_time, envelope)
                self.DG.node[answer_envelope['receiver']][self.simulation_protocol].receive_message(
                    self.simulation_time, answer_envelope)
                if answer_envelope['connection_killed'] is True:
                    if self.DG.has_edge(envelope['sender'], envelope['receiver']):
                        self.DG.remove_edge(envelope['sender'], envelope['receiver'])
                    if self.DG.has_edge(envelope['receiver'], envelope['sender']):
                        self.DG.remove_edge(envelope['receiver'], envelope['sender'])

    def _offline_node_gets_online(self, node):
        id: int = node.get_id()
        self.DG.add_node(id)
        self.DG.node[id][self.simulation_protocol] = node
        self._get_addresses_from_neighbour(id)
        self._node_updates_outbound_connection(id)

    def _new_node_connects_to_network(self, show_network=False):
        self.DG_last_id += 1
        self.DG.add_node(self.DG_last_id)
        if float(len(self.evil_nodes_id) + 1) < len(self.DG.node) * self.evil_nodes_percentage:
            is_evil = True
        else:
            is_evil = False
        if self.simulation_protocol == 'bitcoin_protocol':
            max_outbound_connections, max_total_connections = self._get_outbound_connection_size()
            self.DG.node[self.DG_last_id][self.simulation_protocol] = bn.BitcoinNode(self.DG_last_id,
                                                                                     self.simulation_time,
                                                                                     self.FIXED_DNS,
                                                                                     self.DG,
                                                                                     MAX_OUTBOUND_CONNECTIONS=max_outbound_connections,
                                                                                     is_evil=is_evil,
                                                                                     connection_strategy=self.connection_strategy,
                                                                                     MAX_TOTAL_CONNECTIONS=max_total_connections)
            if is_evil:
                self.evil_nodes_id.append(self.DG_last_id)
                print('The evil node ' + str(self.DG_last_id) + ' has been added\n'
                      'all current evil nodes: ' + str(self.evil_nodes_id))
        elif self.simulation_protocol == 'power_2_choices':
            self.DG.node[self.DG_last_id][self.simulation_protocol] = p2c.Power2Choices(self.DG_last_id,
                                                                                        self.simulation_time,
                                                                                        self.FIXED_DNS)
        self._get_addresses_from_neighbour(self.DG_last_id)
        self._node_updates_outbound_connection(self.DG_last_id)
        if show_network is True:
            self.whiteboard.plot_net()

    def _get_outbound_connection_size(self) -> [int, int]:
        # returns the initial number of connections and the max number of connections
        if self.outbound_distribution is 'const8_125':
            return self.MAX_OUTBOUND_CONNECTIONS, 125
        if self.outbound_distribution is 'const13_125':
            return 13, 125
        if self.outbound_distribution is 'uniform_1_max':
            return random.randint(1, len(self.DG.nodes)), sys.maxsize
        if self.outbound_distribution is 'normal_mu8_sig4':
            return max(1, np.random.normal(8, 4, 1).astype(int)[0]), sys.maxsize
        if self.outbound_distribution is 'normal_mu_sig_auto':
            return max(1, np.random.normal(len(self.DG.nodes) * .25, len(self.DG.nodes) * .1, 1).astype(int)[0]),\
                   sys.maxsize
        if self.outbound_distribution is 'normal_mu16_sig8':
            return max(1, np.random.normal(16, 8, 1).astype(int)[0]), sys.maxsize
        if self.outbound_distribution is '1percent':
            if random.randint(1, 100) <= 1:
                return sys.maxsize / 2, sys.maxsize
            return self.MAX_OUTBOUND_CONNECTIONS, 125
        if self.outbound_distribution is '1percent_10':
            if random.randint(1, 100) <= 1:
                return len(self.DG.nodes) * 0.1, sys.maxsize
            return self.MAX_OUTBOUND_CONNECTIONS, 125
        if self.outbound_distribution is 'const_iter':
            return self.data['initial_min'], self.data['initial_max']
        if self.outbound_distribution is 'hacky_1':
            return self.MAX_OUTBOUND_CONNECTIONS, 125

        print(self.outbound_distribution)
        assert True

    def _delete_node(self, node_id, show_protocol=False, save_offline_node=True):

        envelopes = self.DG.node[node_id][self.simulation_protocol].go_offline(self.simulation_time)

        if show_protocol is True:
            pprint.pprint(envelopes)
        for envelope in envelopes:
            envelope_1 = self.DG.node[envelope['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelope)
            self.DG.node[envelope_1['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelope_1)

        if save_offline_node is True:
            self.offline_nodes.append(self.DG.node[node_id][self.simulation_protocol])
            
        self.DG.remove_node(node_id)
        if node_id in self.evil_nodes_id:
            self.evil_nodes_id.remove(node_id)
        return True

    def _get_addresses_from_neighbour(self, node_id, envelope=None, show_protocol=False):
        envelope_1 = envelope
        if envelope is None:
            envelope_1 = self.DG.node[node_id][self.simulation_protocol].ask_neighbour_to_get_addresses(
                self.simulation_time)

        if envelope_1['receiver'] not in self.DG.nodes:
            return False

        envelope_2 = self.DG.node[envelope_1['receiver']][self.simulation_protocol].receive_message(
            self.simulation_time, envelope_1)
        envelope_3 = self.DG.node[envelope_2['receiver']][self.simulation_protocol].receive_message(
            self.simulation_time, envelope_2)

        if show_protocol is True:
            pprint.pprint(envelope_1)
            pprint.pprint(envelope_2)
            pprint.pprint(envelope_3)
        return True

    def _node_updates_outbound_connection(self, node_id, envelope=None, show_protocol=False, show_connection_failures=False):

        if envelope is not None:
            envelope_1 = envelope
        else:
            envelope_1 = self.DG.node[node_id][self.simulation_protocol].update_outbound_connections(
                self.simulation_time)
        # there is no need to update the connections
        if envelope_1 is None:
            return False

        if self.simulation_protocol == 'bitcoin_protocol':
            success: bool = self._node_bitcoin(envelope_1, node_id, show_protocol, show_connection_failures)
        elif self.simulation_protocol == 'power_2_choices':
            success: bool = self._node_power_2_choices(envelope_1, node_id, show_protocol, show_connection_failures)
        return success

    def _node_power_2_choices(self, envelopes_1, node_id, show_protocol, show_connection_failures):
        assert len(envelopes_1) == 2, 'a node has to ask 2 other nodes in order to get to chose between two degrees'
        # if the node to connect does not exist anymore
        if envelopes_1[0]['receiver'] not in self.DG.nodes:
            if show_connection_failures:
                print('node_id: ' + str(node_id) + 'could not connect to ' + str(envelopes_1['receiver']))
            return False
        if envelopes_1[1]['receiver'] not in self.DG.nodes:
            if show_connection_failures:
                print('node_id: ' + str(node_id) + 'could not connect to ' + str(envelopes_1['receiver']))
            return False
        # one of the nodes wants to connect to himeself
        if (envelopes_1[0]['receiver'] == envelopes_1[0]['sender']) or (envelopes_1[1]['receiver'] == envelopes_1[1]['sender']):
            if show_connection_failures:
                print('node might connect to himself')
            return False
        envelopes_2 = list()
        envelopes_3 = list()
        for ii in range(2):
            envelopes_2.append(self.DG.node[envelopes_1[ii]['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelopes_1[ii]))
            envelopes_3.append(self.DG.node[envelopes_2[ii]['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelopes_2[ii]))
        envelope_4 = self.DG.node[envelopes_3[1]['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelopes_3[1])
        envelope_5 = self.DG.node[envelope_4['receiver']][self.simulation_protocol].receive_message(self.simulation_time, envelope_4)

        # add connection to graph if successful connection was established
        #propabaly still an error because we always return done!!!!
        if envelope_5['connect_as_outbound'] == 'done':
            self.DG.add_edge(envelopes_1[0]['sender'], envelopes_1[0]['receiver'])
        elif show_protocol:
            print(str(node_id) + ' could not update its outbound connections')
            print('### node ' + str(node_id) + ' looks for an outbound connection')
            pprint.pprint(envelopes_1)
            pprint.pprint(envelopes_2)
            pprint.pprint(envelopes_3)
            pprint.pprint(envelope_4)
            pprint.pprint(envelope_5)
            return False
        return True


    def _node_bitcoin(self, envelope_1, node_id, show_protocol, show_connection_failures):
        # if the node to connect does not exist anymore
        if envelope_1['receiver'] not in self.DG.nodes:
            if show_connection_failures:
                print('node_id: ' + str(node_id) + 'could not connect to ' + str(envelope_1['receiver']))
            return False

        # try to connect to node
        envelope_2 = self.DG.node[envelope_1['receiver']][self.simulation_protocol].receive_message(
            self.simulation_time, envelope_1)
        envelope_3 = self.DG.node[envelope_2['receiver']][self.simulation_protocol].receive_message(
            self.simulation_time, envelope_2)

        # add connection to graph if successful connection was established
        if envelope_3['connect_as_outbound'] == 'done':
            self.DG.add_edge(envelope_1['sender'], envelope_1['receiver'])
        elif show_protocol:
            print(str(node_id) + ' could not update its outbound connections')

        if show_protocol:
            print('### node ' + str(node_id) + ' looks for an outbound connection')
            pprint.pprint(envelope_1)
            pprint.pprint(envelope_2)
            pprint.pprint(envelope_3)
        return True

    def _initialize_fixed_dns_servers(self):
        for ii in self.FIXED_DNS:
            self.DG_last_id = ii
            self.DG.add_node(ii)
            if self.simulation_protocol == 'bitcoin_protocol':
                self.DG.node[ii][self.simulation_protocol] = bn.BitcoinNode(ii, self.simulation_time, self.FIXED_DNS, self.DG, connection_strategy=self.connection_strategy)
            elif self.simulation_protocol == 'power_2_choices':
                self.DG.node[ii][self.simulation_protocol] = p2c.Power2Choices(ii, self.simulation_time, self.FIXED_DNS)
        for ii in list(self.DG.nodes):
            self._node_updates_outbound_connection(ii)


def pop_random_element_from_list(x):
    return x.pop(random.randrange(len(x)))
