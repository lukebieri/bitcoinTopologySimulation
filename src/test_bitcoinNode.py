from unittest import TestCase
import BitcoinNode as bn
import networkx as nx
import pprint


class TestBitcoinNode(TestCase):

    @staticmethod
    def get_empty_bitcoinNode(is_evil=False, connection_strategy='normal', g_last_id=5, simulation_time=3.4,
                              fixed_dns=[1, 2, 3], max_outbound_connections=8, g=nx.Graph(), max_total_connections=125):
        return bn.BitcoinNode(g_last_id,
                              simulation_time,
                              fixed_dns,
                              g,
                              MAX_OUTBOUND_CONNECTIONS=max_outbound_connections,
                              MAX_TOTAL_CONNECTIONS=max_total_connections,
                              is_evil=is_evil,
                              connection_strategy=connection_strategy)

    def test_get_id(self):
        expected_id = 10
        b = self.get_empty_bitcoinNode(g_last_id=expected_id)
        got_id = b.get_id()
        self.assertEqual(expected_id, got_id, msg='bitcoinNode: ID should be set')

    def test_is_hard_coded_dns(self):
        id_dns = 2
        b = self.get_empty_bitcoinNode(fixed_dns=[id_dns, 3, 4], g_last_id=id_dns)
        is_hard_coded_dns_1 = b.is_hard_coded_dns()
        self.assertTrue(is_hard_coded_dns_1, msg='bitcoinNode: If it is a hard coded DNS')

        b = self.get_empty_bitcoinNode(fixed_dns=[1, 2, 3], g_last_id=10000)
        is_hard_coded_dns_1 = b.is_hard_coded_dns()
        self.assertFalse(is_hard_coded_dns_1, msg='bitcoinNode: If it is not a hard coded DNS')

    def get_graph(self):
        g = nx.Graph()
        g.add_edge(1, 2)
        g.add_edge(1, 3)
        g.add_edge(1, 4)
        g.add_edge(1, 20)
        g.add_edge(10, 20)
        g.add_edge(20, 30)
        g.add_edge(30, 40)
        g.add_edge(20, 40)
        return g

    def test_update_outbound_connections(self):
        # test 'normal' case
        t = 10000.1
        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='bc_standard')
        b.addrMan = {100: 1200.0}
        expected_envelope = b._get_empty_envelope(t, 100)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, b.update_outbound_connections(t),
                             msg='bitcoinNode: update_outbound_connection() under the normal bitcoin protocol')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_min')
        b.addrMan = {10: 123.3, 40: 44.2}
        for _ in range(100):
            received_envelope = b.update_outbound_connections(t)
            if received_envelope['receiver'] == 10:
                break
        expected_envelope = b._get_empty_envelope(t, 10)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices min protocol'
                                 '(1)')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_min')
        b.addrMan = {10: 123.3}
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 10)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices min protocol'
                                 '(2) only 1 address to chose from')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_min', fixed_dns=[20])
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 20)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices min protocol'
                                 '(2) connect to dns')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_max')
        b.addrMan = {10: 123.3, 40: 44.2}
        for _ in range(100):
            received_envelope = b.update_outbound_connections(t)
            if received_envelope['receiver'] == 40:
                break
        expected_envelope = b._get_empty_envelope(t, 40)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices max protocol'
                                 '(1)')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_max')
        b.addrMan = {10: 123.3}
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 10)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices max protocol'
                                 '(2) only 1 address to chose from')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='p2c_min', fixed_dns=[20])
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 20)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under the power of two choices max protocol'
                                 '(2) connect to dns')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='geo_bc', fixed_dns=[1], g_last_id=1)
        b.outbound = {}
        b.addrMan = {6: 22.3}
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 6)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under geo bitcoin protocol'
                                 '(1) initial connection')

        b = self.get_empty_bitcoinNode(g=self.get_graph(), connection_strategy='geo_bc', fixed_dns=[1], g_last_id=1)
        b.outbound = {11: 4.323}
        b.addrMan = {6: 22.3, 11: 2.23}
        received_envelope = b.update_outbound_connections(t)
        expected_envelope = b._get_empty_envelope(t, 6)
        expected_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_envelope, received_envelope,
                             msg='bitcoinNode: update_outbound_connection() under geo bitcoin protocol (1) initial connection')

    def test_ask_for_outbound_connection(self):
        t = 10000.1
        max_outbound_connections = 3
        max_total_connections = 10
        b = self.get_empty_bitcoinNode(max_outbound_connections=max_outbound_connections,
                                       max_total_connections=max_total_connections)
        for ii in range(max_outbound_connections + max_total_connections):
            b.inbound[ii] = t
        self.assertFalse(b.ask_for_outbound_connection(t, 20),
                         msg='bitcoinNode: ask_for_outbound_connection() check if no node cannot be added (1)')
        self.assertEqual(len(b.inbound), max_outbound_connections + max_total_connections,
                         msg='bitcoinNode: ask_for_outbound_connection() check if no node cannot be added (2)')

        max_outbound_connections = 3
        max_total_connections = 10
        b = self.get_empty_bitcoinNode(max_outbound_connections=max_outbound_connections,
                                       max_total_connections=max_total_connections)
        self.assertTrue(b.ask_for_outbound_connection(t, 20),
                        msg='bitcoinNode: ask_for_outbound_connection() check if node can be added (1)')
        self.assertDictEqual(b.inbound, {20: t},
                             msg='bitcoinNode: ask_for_outbound_connection() check if node can be added (2)')

    def test_receive_message(self):
        t = 1000.2
        fixed_dns = [9, 19, 29]
        id_1 = 999
        id_2 = 888
        b1 = self.get_empty_bitcoinNode(g_last_id=id_1, fixed_dns=fixed_dns)
        b2 = self.get_empty_bitcoinNode(g_last_id=id_2, fixed_dns=fixed_dns)

        envelope_1 = b1._get_empty_envelope(t, id_1)
        with self.assertRaises(ValueError, msg='envelope is sent to itself'):
            b2.receive_message(t, envelope_1)

        envelope_2 = b2._get_empty_envelope(t, id_1)
        with self.assertRaises(ValueError, msg='envelope sent back to the initial sender'):
            b2.receive_message(t, envelope_2)

        envelope_3 = b1._get_empty_envelope(t, id_2)
        self.assertDictEqual(b2.receive_message(t, envelope_3), b2._get_empty_envelope(t, id_1),
                             msg='process empty envelope and return empty message')

        b1 = self.get_empty_bitcoinNode(g_last_id=id_1, fixed_dns=fixed_dns)
        b2 = self.get_empty_bitcoinNode(g_last_id=id_2, fixed_dns=fixed_dns)
        envelope_4 = b1._get_empty_envelope(t, id_2)
        envelope_4['connect_as_outbound'] = 'can_I_send_you_stuff'
        envelope_5 = b2._get_empty_envelope(t, id_1)
        envelope_5['connect_as_outbound'] = 'accepted'
        self.assertDictEqual(b2.receive_message(t, envelope_4), envelope_5,
                             msg='bitcoinNode: receive_message() getting new connection')

        b1 = self.get_empty_bitcoinNode(g_last_id=id_1, fixed_dns=fixed_dns, simulation_time=t)
        b2 = self.get_empty_bitcoinNode(g_last_id=id_2, fixed_dns=fixed_dns, simulation_time=t)
        envelope_6 = b1._get_empty_envelope(t, id_2)
        envelope_6['get_address'] = True
        envelope_7 = b2.receive_message(t, envelope_6)
        for address_dict in envelope_7['address_list']:
            for key, value in address_dict.items():
                self.assertTrue(t == value,
                                 msg='bitcoinNode: receive_message() get_address returns correct timestamp of address')
                self.assertTrue(key in fixed_dns,
                                 msg='bitcoinNode: receive_message() get_address returns correct address')

    def test_ask_neighbour_to_get_addresses(self):
        t = 10000.1
        fixed_dns = [40]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns)
        expected_envelope = b._get_empty_envelope(t, 40)
        expected_envelope['get_address'] = True
        self.assertDictEqual(expected_envelope, b.ask_neighbour_to_get_addresses(t),
                             msg='bitcoinNode: ask_neighbour_to_get_addresses for node without connections')

        b.outbound = {100: 12341234.4}
        expected_envelope = b._get_empty_envelope(t, 100)
        expected_envelope['get_address'] = True
        self.assertDictEqual(expected_envelope, b.ask_neighbour_to_get_addresses(t),
                         msg='bitcoinNode: ask_neighbour_to_get_addresses for node with connections')

    def test_buffer_to_send(self):
        t = 123
        b = self.get_empty_bitcoinNode()
        neighbour = 12
        addresses = [101, 2000, 5000]
        address_known = {10: {1000: 3.5,
                              5000: 4.3,
                              },
                         12: {2000: 5.2,
                              5000: 4.3,
                              6000: 1.2,
                              },
                         }
        addrMan = {100: 4.2,
                   101: 3.9,
                   1000: 3.5,
                   12: 4.9,
                   2000: 4.3,
                   5000: 88.2,
                   }
        b.addrMan = addrMan
        b.address_known = address_known
        b.buffer_to_send(addresses, neighbour)
        got = b.address_buffer
        expected = [{101: 3.9}, {5000: 88.2}]
        for ii in range(len(expected)):
            self.assertDictEqual(expected[ii], got[ii],
                                 msg='bitcoinNode: buffer_to_send() received wrong data')

    def test_interval_processes(self):
        fixed_dns = [4]
        id_1 = 999
        b1 = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, g_last_id=id_1, max_outbound_connections=2)
        got_1 = b1.interval_processes(0)
        expected_1 = [b1._get_empty_envelope(0, fixed_dns[0])]
        expected_1[0]['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.assertDictEqual(expected_1[0], got_1[0],
                             msg='bitcoinNode: interval_process initial connection')

        t = 2.8
        fixed_dns = [4]
        b2 = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, g_last_id=id_1, max_outbound_connections=2)
        b2.addrMan = {4: 0, 5: 2.8}
        b2.outbound = {4: 0, 5: 2.8}
        b2.interval_timestamps['100ms'] = t
        got_2 = b2.interval_processes(t)
        expected_2 = b2._get_empty_envelope(t, 4)
        expected_2['kill_connection'] = True
        self.assertListEqual([expected_2], got_2,
                             msg='bitcoinNode: interval_process() all outbound connections ok & everything up to date')

        t = 2.8
        fixed_dns = [4]
        b3 = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, g_last_id=id_1, max_outbound_connections=3)
        b3.addrMan = {4: 0, 5: 2.8, 6: 1.5}
        b3.outbound = {4: 0, 5: 2.8}
        b3.interval_timestamps['100ms'] = t
        for _ in range(50):
            got_3 = b3.interval_processes(t)
            if len(got_3) > 0:
                break
        expected_3 = b3._get_empty_envelope(t, 6)
        expected_3['connect_as_outbound'] = 'can_I_send_you_stuff'
        pprint.pprint('hi lukas')
        pprint.pprint(got_3)
        pprint.pprint([expected_3])
        self.assertListEqual(got_3, [expected_3],
                             msg='bitcoinNode: interval_process() update outbound')

        # 'address_list' was tested manually


    def test__delete_oldest_outbound_connection(self):
        t = 123
        b = self.get_empty_bitcoinNode()
        outbound = {10000: 3.6, 6: 4.9, 2: 100.3}
        b.outbound = outbound
        expected_envelope = b._get_empty_envelope(t, 10000)
        expected_envelope['kill_connection'] = True
        self.assertDictEqual(expected_envelope, b._delete_oldest_outbound_connection(t),
                             msg='bitcoinNode: _delete_oldest_outbound_connection')

    def test__get_address_to_connect(self):
        fixed_dns = [4, 5]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns)
        address1 = b._get_address_to_connect()
        self.assertTrue(address1 in fixed_dns,
                        msg='bitcoinNode: get_address_to_connect() if a new node connects to the network')

        fixed_dns = [4, 5]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns)
        addrMan = [10, 11, 12]
        b.addrMan = addrMan
        address2 = b._get_address_to_connect()
        self.assertTrue(address2 in addrMan,
                        msg='bitcoinNode: get_address_to_connect if a new outbound has to be found')

        fixed_dns = [4, 5]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, max_outbound_connections=3)
        addrMan = [10, 11, 12]
        outbound = [4, 100, 200]
        b.outbound = outbound
        b.addrMan = addrMan
        address2 = b._get_address_to_connect()
        self.assertTrue(address2 in addrMan,
                        msg='bitcoinNode: get_address_to_connect if outbound is full but has fixed_dns in it')

        fixed_dns = [4, 5]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, max_outbound_connections=3)
        addrMan = [10, 11, 12]
        outbound = [4, 100, 200, 300, 400, 500, 600]
        b.outbound = outbound
        b.addrMan = addrMan + fixed_dns
        address3 = b._get_address_to_connect()
        self.assertTrue(address3 is None,
                        msg='bitcoinNode: get_address_to_connect if outbound is full but has fixed_dns in it')


    def test__initialize_outgoing_connections(self):
        t = 100.9
        id = 4
        fixed_dns = [id, 5]
        b = self.get_empty_bitcoinNode(fixed_dns=fixed_dns, g_last_id=id)
        self.assertIsNone(b._initialize_outgoing_connections(t),
                          msg='bitcoinNode: _initialized_outgoing_connections if the node is a hard coded DNS')

        fixed_dns = [100]
        b = self.get_empty_bitcoinNode(g_last_id=id, fixed_dns=fixed_dns)
        expected_envelope = b._get_empty_envelope(t, 100)
        expected_envelope['get_address'] = True
        self.assertDictEqual(expected_envelope, b._initialize_outgoing_connections(t),
                             msg='bitcoinNode: _initialize_outgoing_connections if a non-DNS node connects to the'
                                 'network new')


    def test__get_empty_envelope(self):
        receiver = 1234
        t = 99.3
        sender = 44
        expected_envelope = dict(sender=sender, receiver=receiver, timestamp=t, address_list=dict(), get_address=False,
                                 version=False, connect_as_outbound=None, kill_connection=False,
                                 connection_killed=False)
        b = self.get_empty_bitcoinNode(g_last_id=sender)
        self.assertDictEqual(expected_envelope, b._get_empty_envelope(t, receiver),
                             msg='bitcoinNode: empty envelope test')
