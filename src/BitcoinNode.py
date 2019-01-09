from collections import Counter
import pprint
import networkx as nx
import random
import sys


class BitcoinConstant(object):
    # total number of buckets for tried addresses
    ADDRMAN_TRIED_BUCKET_COUNT_LOG2 = 8

    # total number of buckets for new addresses
    ADDRMAN_NEW_BUCKET_COUNT_LOG2 = 10

    # maximum allowed number of entries in buckets for new and tried addresses
    ADDRMAN_BUCKET_SIZE_LOG2 = 6

    # over how many buckets entries with tried addresses from a single group ( / 16 for IPv4) are spread
    ADDRMAN_TRIED_BUCKETS_PER_GROUP = 8

    # over how many buckets entries with new addresses originating from a single group are spread
    ADDRMAN_NEW_BUCKETS_PER_SOURCE_GROUP = 64

    # in how many buckets for entries with new addresses a single address may occur
    ADDRMAN_NEW_BUCKETS_PER_ADDRESS = 8

    # how old addresses can maximally be
    ADDRMAN_HORIZON_DAYS = 30

    # after how many failed attempts we give up on a new node
    ADDRMAN_RETRIES = 3

    # how many successive failures are allowed ...
    ADDRMAN_MAX_FAILURES = 10

    # ... in at least this many days
    ADDRMAN_MIN_FAIL_DAYS = 7

    # how recent a successful connection should be before we allow an address to be evicted from tried
    ADDRMAN_REPLACEMENT_HOURS = 4

    # the maximum percentage of nodes to return in a getaddr call
    ADDRMAN_GETADDR_MAX_PCT = 23

    # the maximum number of nodes to return in a getaddr call
    ADDRMAN_GETADDR_MAX = 2500

    # the maximum number of tried addr collisions to store
    ADDRMAN_SET_TRIED_COLLISION_SIZE = 10

    # the maximum connections that a bitcoin node is allowed to have online
    # MAX_TOTAL_CONNECTIONS = 125

    # the maximum outgoing connections that a bitcoin node is allowed to have
    # MAX_OUTBOUND_CONNECTIONS = 8


class BitcoinNode(BitcoinConstant):

    id: int

    ############################
    # initialization
    ############################

    def __init__(self, node_id: int, t: float, hard_coded_dns, DG: object, MAX_OUTBOUND_CONNECTIONS: int = 8,
                 MAX_TOTAL_CONNECTIONS: int = 125,
                 is_evil: bool = False, connection_strategy: str = 'p2c_max') -> object:
        self.id = node_id

        # one should only read data from this variable but not modify any. This object is used to make the
        # simulations more compareable.
        self.DG = DG
        self.outbound_is_full_bool = False
        self.connection_strategy = connection_strategy
        self.is_evil = is_evil
        if is_evil:
            self.MAX_OUTBOUND_CONNECTIONS = int(sys.maxsize / 2)
            self.MAX_TOTAL_CONNECTIONS = sys.maxsize
            assert True
        else:
            self.MAX_OUTBOUND_CONNECTIONS = MAX_OUTBOUND_CONNECTIONS
            self.MAX_TOTAL_CONNECTIONS = MAX_TOTAL_CONNECTIONS

        # mapping from node to timestamp
        self.addrMan = dict()
        for address in hard_coded_dns:
            if address is not node_id:
                self.addrMan[address] = t

        # peer is an outbound connection
        self.outbound = dict()

        # peer is an inbound connection
        self.inbound = dict()

        # peer knows about address (can set/get)
        self.address_known = dict()

        # set of addresses to send to peer
        self.address_buffer = list()

        # bounce message from a call
        self.output_envelope = list()

        # when the addresses were broadcasted the last time
        self.interval_timestamps = {'100ms': t, '24h': t}

        self._hard_coded_dns = hard_coded_dns
        if self.id in self._hard_coded_dns:
            self._is_hard_coded_DNS = True
        else:
            self._is_hard_coded_DNS = False

        self._initialize_outgoing_connections(t)

    ############################
    # public functions
    ############################

    def get_id(self) -> int:
        return self.id

    def is_hard_coded_dns(self):
        return self._is_hard_coded_DNS

    def number_outbound(self):
        return len(self.outbound)

    def outbound_is_full(self) -> bool:
        if len(list(self.outbound.keys())) + len(list(self.inbound.keys())) >= self.MAX_OUTBOUND_CONNECTIONS:
            if self.outbound_is_full_bool is False:
                self.outbound_is_full_bool = True
        return self.outbound_is_full_bool

    def update_outbound_connections(self, t):
        address = self._get_address_to_connect()

        # look from a global perspective on the code and find out which degree out of two possibilities one should get
        if (self.connection_strategy is 'p2c_max') or (self.connection_strategy is 'p2c_min'):
            address2 = self._get_address_to_connect()
            if (address is not None) and (address2 is not None):
                if self.DG.is_directed():
                    graph = self.DG.to_undirected()
                else:
                    graph = self.DG
                addresses_in_graph = True
                if address not in graph.node:
                    addresses_in_graph = False
                if address2 not in graph.node:
                    addresses_in_graph = False
                if addresses_in_graph:
                    degree1 = graph.degree(address)
                    degree2 = graph.degree(address2)
                    if self.connection_strategy is 'p2c_min':
                        address = address if degree1 <= degree2 else address2
                    elif self.connection_strategy is 'p2c_max':
                        address = address if degree1 >= degree2 else address2
        elif self.connection_strategy is 'geo_bc':
            numb_bubble = 5
            my_bubble = self.id % numb_bubble
            my_bubble_neighbours = [x % numb_bubble for x in self.outbound.keys()]
            for _ in range(40):
                if address is None:
                    break
                address_bubble = address % numb_bubble
                if address_bubble not in my_bubble_neighbours:
                    # a new bubble that we have not yet connected
                    break
                if address_bubble == my_bubble:
                    # connecting to the same bubble
                    if Counter(my_bubble_neighbours)[my_bubble] <= 8:
                        # there are less than x connections within my own bubble
                        break
                address = self._get_address_to_connect()


        if address is None:
            return address
        envelope = self._get_empty_envelope(t, address)
        envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
        self.output_envelope = [envelope]
        return envelope

    def ask_for_outbound_connection(self, t, address):
        if len(self.inbound) >= self.MAX_TOTAL_CONNECTIONS - self.MAX_OUTBOUND_CONNECTIONS:
            return False
        self.inbound[address] = t
        return True

    def go_offline(self, t):
        connected_nodes = list(set(list(self.inbound) + list(self.outbound)))
        envelopes = [self._kill_connection(t, address) for address in connected_nodes]
        self.output_envelope = envelopes
        return envelopes

    def receive_message(self, t, envelope):

        # validate input
        if envelope['sender'] == self.id:
            raise ValueError("envelope['sender'] = " + str(envelope['sender']) + ", self.id = " + str(self.id))
        if envelope['sender'] == envelope['receiver']:
            raise ValueError('envelope is sent to itself')

        # initialize return statement
        answer_envelope = self._get_empty_envelope(t, envelope['sender'])

        # sender has never been seen before
        if envelope['sender'] not in self.addrMan:
            self.addrMan[envelope['sender']] = t
        if envelope['sender'] not in self.address_known:
            self.address_known[envelope['sender']] = dict()

        # address message response from connect_as_outbound
        if envelope['connect_as_outbound'] == 'can_I_send_you_stuff':
            if self.ask_for_outbound_connection(t, envelope['sender']):
                answer_envelope['connect_as_outbound'] = 'accepted'
        if envelope['connect_as_outbound'] == 'accepted':
            self.outbound[envelope['sender']] = t
            answer_envelope['connect_as_outbound'] = 'done'

        # neighbour node goes offline
        if envelope['kill_connection'] is True:
            if envelope['sender'] in self.outbound:
                self.outbound.pop(envelope['sender'], None)
            if envelope['sender'] in self.inbound:
                self.inbound.pop(envelope['sender'], None)
            answer_envelope['connection_killed'] = True
        if envelope['connection_killed'] is True:
            if envelope['sender'] in self.outbound:
                self.outbound.pop(envelope['sender'], None)
            if envelope['sender'] in self.inbound:
                self.inbound.pop(envelope['sender'], None)

        # update address timestamps
        if envelope['sender'] in self.addrMan:
            if envelope['sender'] in self.outbound:
                if self.addrMan[envelope['sender']] < t - 20 * 60:
                    self.addrMan[envelope['sender']] = t

        # address message from peer with addresses in address_vector
        for address_dict in envelope['address_list']:
            address = list(address_dict.keys()).pop()
            if address != self.id:
                if address not in self.addrMan:
                    self.addrMan[address] = address_dict[address]
                self.address_known[envelope['sender']][address] = address_dict[address]
                if self._is_terrible(t, address):
                    self.addrMan[address] = t - 5 * 60 * 60
                if t - self.addrMan[address] < 10 * 60:
                    addresses = list(set(random.choices(list(self.addrMan), k=2)))
                    self.buffer_to_send(addresses, envelope['sender'])

        # get address call
        if envelope['get_address'] is True:
            self.address_buffer = []  # clear send buffer
            number_addresses = max(min(min(2500, int(0.23 * len(self.addrMan))), len(self.addrMan)),
                                   len(self._hard_coded_dns) - 1)
            addresses = random.choices(list(self.addrMan), k=number_addresses)
            self.buffer_to_send(addresses, envelope['sender'])
            answer_envelope['address_list'] = self.address_buffer

        # if envelope['version'] is True:
        #     answer_envelope['get_address'] = True
        #     if envelope['sender'] in self.outbound:
        #         self.buffer_to_send(None)

        self.output_envelope = [answer_envelope]
        return answer_envelope

    def ask_neighbour_to_get_addresses(self, t):
        if len(self.outbound) == 0:
            neighbour_address = random.choice(self._hard_coded_dns)
        else:
            neighbour_address = random.choice(list(self.outbound))
        envelope = self._get_empty_envelope(t, neighbour_address)
        envelope['get_address'] = True
        self.output_envelope = [envelope]
        return envelope

    def buffer_to_send(self, addresses, neighbour):
        for address in addresses:
            if (address not in self.address_known[neighbour])\
                    or (self.addrMan[address] > self.address_known[neighbour][address]):
                timestamp = self.addrMan[address]
                self.address_buffer.append({address: timestamp})

    def interval_processes(self, t):
        self.output_envelope = []
        output = []
        if t - self.interval_timestamps['100ms'] > 0.1:
            self.interval_timestamps['100ms'] = t
            if len(self.outbound) > 0:
                random_neighbour = random.choice(list(self.outbound))
                envelope1 = self._get_empty_envelope(t, random_neighbour)
                envelope1['address_list'] = self.address_buffer
                self.address_buffer = []
                if envelope1 is not None:
                    self.output_envelope.append(envelope1)
                    output.append(envelope1)
        if t - self.interval_timestamps['24h'] > 24 * 60 * 60:
            for address in (self.outbound + self.inbound):
                envelope2 = self._get_empty_envelope(t, address)
                envelope2['address_list'] = self.address_buffer
                if envelope2 is not None:
                    self.output_envelope.append(envelope2)
                    output.append(envelope2)
            self.address_buffer = []
        if len(self.outbound) >= self.MAX_OUTBOUND_CONNECTIONS:
            envelope3 = self._delete_oldest_outbound_connection(t)
            if envelope3 is not None:
                self.output_envelope.append(envelope3)
                output.append(envelope3)
        if len(self.outbound) < self.MAX_OUTBOUND_CONNECTIONS:
            neighbours_to_connect = 1 if self.MAX_OUTBOUND_CONNECTIONS - 5 < len(list(self.outbound)) else 5
            for _ in range(neighbours_to_connect):
                envelope4 = self.update_outbound_connections(t)
                if envelope4 is not None:
                    self.output_envelope.append(envelope4)
                    output.append(envelope4)
        outdated_connections = self._outdated_connections(t)
        self.output_envelope.extend(outdated_connections)
        output.extend(outdated_connections)
        return output

    ############################
    # private functions
    ############################

    def _outdated_connections(self, t):
        envelopes = []
        for address, timestamp in self.outbound.items():
            if self.addrMan[address] + self.ADDRMAN_REPLACEMENT_HOURS * 60 * 60 < timestamp:
                envelope = self._get_empty_envelope(t, address)
                envelope['kill_connection'] = True
                envelopes.append(envelope)
        return envelopes

    def _delete_oldest_outbound_connection(self, t):
        oldest_outbound_node_address = min(self.outbound, key=self.outbound.get)
        # oldest_address = [key for key, value in self.outbound.items() if value == oldest_timestamp][0]
        return self._kill_connection(t, oldest_outbound_node_address)

    def _get_address_to_connect(self):
        if len(self.outbound) == 0:
            return random.choice(list(self.addrMan))
        elif len(self.outbound) - len(_intersection_of_2_lists(self.outbound, self._hard_coded_dns)) \
                <= self.MAX_OUTBOUND_CONNECTIONS:
            try_address = random.choice(list(self.addrMan))  # getting a random key from addrMan
        else:
            return None
        ii = 0  # maximum trials to find a new address to connect
        while (try_address in list(self.outbound) + list(self._hard_coded_dns)) and (ii < 3):
            try_address = random.choice(list(self.addrMan))
            if (try_address in self.outbound) or (try_address in self._hard_coded_dns):
                try_address = None
            ii += 1
        return try_address

    def _kill_connection(self, t, address):
        envelope = self._get_empty_envelope(t, address)
        envelope['kill_connection'] = True
        return envelope

    def _initialize_outgoing_connections(self, t):
        if self._is_hard_coded_DNS is True:
            return None

        envelope = self._get_empty_envelope(t, random.choice(self._hard_coded_dns))
        envelope['get_address'] = True
        self.output_envelope = envelope
        return envelope

    def _is_terrible(self, t, address):
        if self.addrMan[address] >= t - 60:
            # never remove things tried in the last minute
            return False
        if self.addrMan[address] > t + 10 * 60:
            # came in a flying DeLorean
            return True
        if t - self.addrMan[address] > self.ADDRMAN_HORIZON_DAYS * 24 * 60 * 60:
            # not seen in recent history
            return True

        # could include number of attempts to connect

        return False

    def _get_empty_envelope(self, t, receiver):
        return dict(sender=self.id, receiver=receiver, timestamp=t, address_list=dict(), get_address=False, version=False,
                    connect_as_outbound=None, kill_connection=False, connection_killed=False)


############################
# static functions
############################
def _intersection_of_2_lists(a, b):
    return set(list(a)).intersection(set(b))