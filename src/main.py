#!/usr/bin/python
import argparse
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pathlib
import simulation


def main(show_plots):
    #s = simulation.Simulation(simulation_type='bitcoin_protocol', with_evil_nodes=True, show_plots=show_plots)
    #s.run()
    big_simulation_bitcoin()
    #big_simulation_power2choices()


def big_simulation_bitcoin():
    t_start = 1
    t_end = 2000
    n_iterations = 4000
    plot_first_x_graphs = 5
    avg_paths_after_n_iterations = [25, 50, 75, 100, 125, 150, 175, 200, 225]
    initial_connection_filter = False
    with_evil_nodes = [False]
    y = list()
    initial_min = np.array([4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 220, 256, 300, 700])
    initial_max = (initial_min / min(initial_min) * 125 / (8 / min(initial_min))).astype('int').tolist()
    x = initial_min.tolist()

    x = [8]
    initial_max = [128]
    # outbound_distributions = ['hacky_1', 'const8_125', 'uniform_1_max', 'normal_mu8_sig4', '1percent',
    #                           'normal_mu_sig_auto', 'const13_125']
    outbound_distributions = ['const13_125', '1percent']
    connection_strategy = ['stand_bc']
    # connection_strategy = ['stand_bc', 'p2c_min', 'p2c_max', 'geo_bc', 'no_geo_bc]
    max_outbound_connections = [8]
    for outbound_distribution in outbound_distributions:
        for min_init, max_init in zip(x, initial_max):
            for connection_strategy_element in connection_strategy:
                for outbound_number in max_outbound_connections:
                    s = simulation.Simulation(simulation_type='bitcoin_protocol', with_evil_nodes=False,
                                              connection_strategy=connection_strategy_element,
                                              initial_connection_filter=initial_connection_filter,
                                              outbound_distribution=outbound_distribution,
                                              data={'initial_min': min_init, 'initial_max': max_init})
                    y.append(s.run(t_start=t_start, t_end=t_end, n_iterations=n_iterations, plot_first_x_graphs=plot_first_x_graphs,
                                   avg_paths_after_n_iterations=avg_paths_after_n_iterations,
                                   MAX_OUTBOUND_CONNECTIONS=outbound_number, numb_nodes=10000))
                    # if len(y) > 0:
                    #     plot_distribution(initial_min[: len(y)], y)


def plot_distribution(x, y):
    t = datetime.datetime.now()
    path = './../../data/' + str(t.year) + '_' + str(t.month) + '_' + str(t.day) + '_' + str(t.hour) + '_' + \
           str(t.minute) + '_' + str(t.second) + '_initial_connections'
    p = pathlib.Path(path)
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    result_json = pathlib.Path('results.json')
    result_png = pathlib.Path('results.png')
    plt.plot(x, y)
    plt.title('different initial connections')
    plt.xlabel('number of initial connections')
    plt.ylabel('average hops')
    export_text = "{\n" + \
                  "    \"title\": " + "\"different initial connections\",\n" + \
                  "    \"number of initial connections\": " + "\"" + str(x) + "\",\n" + \
                  "    \"average hops\": " + "\"" + str(y) + "\"\n" + \
                  "}"
    with open(p / result_json, 'a') as my_file:
        my_file.write(export_text)
    plt.savefig(p / result_png)
    plt.show()

def big_simulation_power2choices():
    s = simulation.Simulation(simulation_type='power_2_choices')
    t_start = 1
    t_end = 160
    n_iterations = 250
    plot_first_x_graphs = 5
    avg_paths_after_n_iterations = [10, 25, 50, 75, 100, 125, 150, 175, 200, 225]
    s.run(t_start=t_start, t_end=t_end, n_iterations=n_iterations, plot_first_x_graphs=plot_first_x_graphs,
          avg_paths_after_n_iterations=avg_paths_after_n_iterations)

#
#     network_analytics.plot_net()
#     network_analytics.shortest_path_histogram()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='hoi Lukas')
    parser.add_argument('-display', default=True, help='Can show stuff on the display?')
    args = parser.parse_args()
    main(bool(args.display))
