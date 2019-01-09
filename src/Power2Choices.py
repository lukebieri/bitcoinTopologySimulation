import random
import operator
from typing import List, Any

import Power2ChoicesHeader as p2ph


class Power2Choices:

    id: int

    ############################
    # initialization
    ############################
    def __init__(self, node_id, t, hard_coded_dns):
        self.id = node_id

        self.address_manual = dict()
        for address in hard_coded_dns:
            if address is not node_id:
                self.address_manual[address] = t

        self.friend_address_manual = dict()
        self.output_envelope = list()

        # peer is an outbound connection
        self.outbound = dict()

        # peer is an inbound connection
        self.inbound = dict()

        # for finding out which neighbour has a lower degree
        self.neighbour_degree = dict()

        # when the addresses were broadcasted the last time
        self.interval_timestamps = {'100ms': t, '24h': t}

        # set of addresses to send to peer
        self.address_buffer = list()

        self._hard_coded_dns = hard_coded_dns
        if self.id in self._hard_coded_dns:
            self._is_hard_coded_DNS = True
        else:
            self._is_hard_coded_DNS = False

    ############################
    # public functions
    ############################

    def get_id(self) -> int:
        return self.id

    def is_hard_coded_dns(self):
        return self._is_hard_coded_DNS

    def update_outbound_connections(self, t):
        addresses = self._get_addresses_to_connect()
        if addresses is None:
            return addresses
        envelopes = list()
        for address in addresses:
            env = self._get_empty_envelope(t, address)
            env['whats_your_degree'] = True
            envelopes.append(env)
        self.output_envelope = envelopes
        return envelopes

    def cleanup_address_manual(self):
        while len(self.address_manual) > p2ph.MAX_ADDRESS_MANUAL_SIZE * 0.8:
            key_to_delete = min(self.address_manual, key=lambda k: self.address_manual[k])
            self.address_manual.pop(key_to_delete)
            for address in self.friend_address_manual:
                if key_to_delete in self.friend_address_manual:
                    self.friend_address_manual[address].remove(key_to_delete)
        return True

    def ask_for_outbound_connection(self, t, address):
        if len(self.inbound) >= p2ph.MAX_NUMBER_CONNECTIONS - p2ph.MAX_OUTBOUND_CONNECTIONS:
            return False
        self.inbound[address] = t
        return True

    def ask_neighbour_to_get_addresses(self, t):
        if len(self.outbound) == 0:
            neighbour_address = random.choice(self._hard_coded_dns)
        else:
            neighbour_address = random.choice(list(self.outbound))
        envelope = self._get_empty_envelope(t, neighbour_address)
        envelope['get_address'] = True
        self.output_envelope = [envelope]
        return envelope

    def go_offline(self, t):
        connected_nodes = list(set(list(self.inbound) + list(self.outbound)))
        envelopes = [self._kill_connection(t, address) for address in connected_nodes]
        self.output_envelope = envelopes
        return envelopes

    def buffer_to_send(self, addresses, neighbour):
        for address in addresses:
            if address not in self.friend_address_manual[neighbour]:
                timestamp = self.address_manual[address]
                self.address_buffer.append({address: timestamp})
        if len(self.address_buffer) > p2ph.MAX_BUFFER_SIZE:
            n = len(self.address_buffer) - p2ph.MAX_BUFFER_SIZE
            temp = self.address_buffer[n:]
            self.address_buffer = temp

    def receive_message(self, t, envelope):

        # validate input
        if envelope['sender'] == self.id:
            raise ValueError("envelope['sender'] = " + str(envelope['sender']) + ", self.id = " + str(self.id))

        # initialize return statement
        answer_envelope = self._get_empty_envelope(t, envelope['sender'])

        # sender has never been seen before
        if envelope['sender'] not in self.address_manual:
            self.address_manual[envelope['sender']] = t
        if envelope['sender'] not in self.friend_address_manual:
            self.friend_address_manual[envelope['sender']] = list()

        # address message response from connect_as_outbound
        if envelope['connect_as_outbound'] == 'can_I_send_you_stuff':
            if self.ask_for_outbound_connection(t, envelope['sender']):
                answer_envelope['connect_as_outbound'] = 'accepted'
        if envelope['connect_as_outbound'] == 'accepted':
            self.outbound[envelope['sender']] = t
            answer_envelope['connect_as_outbound'] = 'done'

        if isinstance(envelope['whats_your_degree'], (int, float)):
            if not isinstance(envelope['whats_your_degree'], bool):
                # if one has to choose a connection
                self.neighbour_degree[envelope['sender']] = envelope['whats_your_degree']
                if len(self.neighbour_degree) > 1:
                    address_to_connect = min(self.neighbour_degree.items(), key=operator.itemgetter(1))[0]
                    # for key in self.neighbour_degree.items():
                    #     self.neighbour_degree.pop(key)
                    self.neighbour_degree = dict()
                    # send a request to the one neighbour that has the lowest number of degrees
                    answer_envelope['receiver'] = address_to_connect
                    answer_envelope['connect_as_outbound'] = 'can_I_send_you_stuff'
            else:
                answer_envelope['whats_your_degree'] = len(list(self.outbound) + list(self.inbound))

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
        if envelope['sender'] in self.address_manual:
            if envelope['sender'] in self.outbound:
                if self.address_manual[envelope['sender']] < t - 20 * 60:
                    self.address_manual[envelope['sender']] = t

        # address message from peer with addresses in address_vector
        for address_dict in envelope['address_list']:
            address = list(address_dict.keys()).pop()
            if address != self.id:
                if address not in self.address_manual:
                    self.address_manual[address] = address_dict[address]
                if address not in self.friend_address_manual[envelope['sender']]:
                    self.friend_address_manual[envelope['sender']].append(address)
                if self._is_terrible(t, address):
                    self.address_manual[address] = t - 5 * 60 * 60
                if t - self.address_manual[address] < 10 * 60:
                    addresses = list(set(random.choices(list(self.address_manual), k=2)))
                    self.buffer_to_send(addresses, envelope['sender'])

        # get address call
        if envelope['get_address'] is True:
            self.address_buffer = []  # clear send buffer
            number_addresses = max(min(min(2500, int(0.23 * len(self.address_manual))), len(self.address_manual)),
                                   len(self._hard_coded_dns) - 1)
            addresses = random.choices(list(self.address_manual), k=number_addresses)
            self.buffer_to_send(addresses, envelope['sender'])
            answer_envelope['address_list'] = self.address_buffer
        return answer_envelope

    def interval_processes(self, t):
        self.output_envelope = []
        output = []
        if t - self.interval_timestamps['100ms'] > 0.1:
            self.interval_timestamps['100ms'] = t
            if len(self.outbound) > 0:
                random_neighbour = random.choice(list(self.outbound))
                envelope = self._get_empty_envelope(t, random_neighbour)
                envelope['address_list'] = self.address_buffer
                self.address_buffer = []
                if envelope is not None:
                    # self.output_envelope.append(envelope)
                    output.append(envelope)
        if t - self.interval_timestamps['24h'] > 24 * 60 * 60:
            for address in (self.outbound + self.inbound):
                envelope = self._get_empty_envelope(t, address)
                envelope['address_list'] = self.address_buffer
                if envelope is not None:
                    # self.output_envelope.append(envelope)
                    output.append(envelope)
            self.address_buffer = []
        if len(self.outbound) >= p2ph.MAX_OUTBOUND_CONNECTIONS:
            envelope = self._delete_oldest_outbound_connection(t)
            if envelope is not None:
                # self.output_envelope.append(envelope)
                output.append(envelope)
        if len(self.outbound) < p2ph.MAX_OUTBOUND_CONNECTIONS:
            envelope = self.update_outbound_connections(t)
            if envelope is not None:
                if isinstance(envelope, list):
                    # self.output_envelope.extend(envelope)
                    output.extend(envelope)
                else:
                    # self.output_envelope.append(envelope)
                    output.append(envelope)
        outdated_connections = self._outdated_connections(t)
        # self.output_envelope.extend(outdated_connections)
        output.extend(outdated_connections)
        return output


    ############################
    # private functions
    ############################

    def _get_addresses_to_connect(self, number_of_addresses=2):
        if len(self.address_manual) == 0:
            addresses = random.choices(list(self._hard_coded_dns), k=number_of_addresses)
            ii = 0
            while (len(addresses) > len(set(addresses))) and (ii < 10):
                addresses = list(set(addresses))
                addresses.append(random.choice(list(self._hard_coded_dns)))
                ii += 1
            return addresses
        elif len(self.outbound) <= p2ph.MAX_OUTBOUND_CONNECTIONS:
            if len(self.address_manual) - len(_intersection_of_2_lists(self.address_manual, self.outbound)) < number_of_addresses:
                a = list(self.address_manual)
                intersection = _intersection_of_2_lists(self.address_manual, self.outbound)
                for intersect in list(intersection) + list(self._hard_coded_dns):
                    if intersect in a:
                        a.remove(intersect)
                addresses = random.choices(list(set(list(self._hard_coded_dns) + a)), k=number_of_addresses)
            else:
                addresses = self._get_x_addresses_from_address_manual(x=number_of_addresses)
        elif bool(_intersection_of_2_lists(self.outbound, self._hard_coded_dns)):
            addresses = self._get_x_addresses_from_address_manual(x=number_of_addresses)
        else:
            return None
        return addresses

    def _get_x_addresses_from_address_manual(self, x=2):
        manual: List[Any] = list(self.address_manual)
        for element in list(self.outbound):
            manual.remove(element)
        assert len(manual) >= x, 'there are not as many unique addresses in address_manual as requested'
        addresses = random.choices(manual, k=x)
        ii = 0
        while (len(addresses) != len(set(addresses))) and (ii < 10):
            addresses = random.choices(manual, k=x)
            ii += 1
        return addresses

    def _initialize_outgoing_connections(self, t):
        if self._is_hard_coded_DNS is True:
            return None
        envelope = self._get_empty_envelope(t, random.choice(self._hard_coded_dns))
        envelope['get_address'] = True
        self.output_envelope = envelope
        return envelope

    def _is_terrible(self, t, address):
        if self.address_manual[address] >= t - 60:
            # never remove things tried in the last minute
            return False
        if self.address_manual[address] > t + 10 * 60:
            # came in a flying DeLorean
            return True
        if t - self.address_manual[address] > p2ph.HORIZON_DAYS * 24 * 60 * 60:
            # not seen in recent history
            return True

    def _kill_connection(self, t, address):
        envelope = self._get_empty_envelope(t, address)
        envelope['kill_connection'] = True
        return envelope

    def _delete_oldest_outbound_connection(self, t):
        oldest_outbound_node_address = min(self.outbound, key=self.outbound.get)
        return self._kill_connection(t, oldest_outbound_node_address)

    def _outdated_connections(self, t):
        envelopes = []
        for address, timestamp in self.outbound.items():
            if self.address_manual[address] + p2ph.ADDRESS_MANUAL_REPLACEMENT_HOURS * 60 * 60 < timestamp:
                envelope = self._get_empty_envelope(t, address)
                envelope['kill_connection'] = True
                envelopes.append(envelope)
        return envelopes

    def _get_empty_envelope(self, t, receiver):
        return dict(sender=self.id, receiver=receiver, timestamp=t, address_list=dict(), get_address=False,
                    version=False, connect_as_outbound=None, kill_connection=False, connection_killed=False,
                    whats_your_degree=None)


############################
# static functions
############################
def _intersection_of_2_lists(a, b):
    return set(list(a)).intersection(set(b))
