from unittest import TestCase
import main

class TestPlot_distribution(TestCase):
    def test_plot_distribution(self):
        x = [5, 6, 7, 8, 9, 10, 100]
        y = [1, 2, 3, 2.3]
        main.plot_distribution(x[:len(y)], y)
