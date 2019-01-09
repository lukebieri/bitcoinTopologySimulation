import multiprocessing as mp
import networkx as nx


def worker(process_id, n_processes, G, d):
    """thread worker function"""
    n_nodes = len(G.nodes)
    local_dict = dict()
    for ii in range(int(n_nodes / n_processes * process_id), int(n_nodes / n_processes * (process_id + 1))):
        length = nx.single_source_shortest_path_length(G, ii)
        local_dict[ii] = length
    d[process_id] = local_dict


def optimized_shortest_path_length_all_pair(g, undirected=True):

    if g.is_directed() and undirected:
        g = g.to_undirected()

    if len(g.nodes) < 5000:
        return dict(nx.all_pairs_shortest_path_length(g))

    # create concurrency for the function all_pairs_shortest_path_length
    manager = mp.Manager()
    d = manager.dict()
    process = []
    n_processes = mp.cpu_count()

    # create different processes
    for i in range(n_processes):
        p = mp.Process(target=worker, args=(i, n_processes, g, d,))
        process.append(p)
        p.start()

    # rejoin processes
    for p in process:
        p.join()

    return_dict = dict()
    for ii in d.values():
        for node, length_dict in ii.items():
            return_dict[node] = length_dict
    return return_dict

