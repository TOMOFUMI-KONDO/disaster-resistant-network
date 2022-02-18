import unittest

from components import HostClient, HostServer, Path, DirectedLink
from enums import RoutingAlgorithm
from route_calculator import RouteCalculator, Switch, Link


# FIXME: follow RouteCalculator implementation
class RouteCalculatorTest(unittest.TestCase):
    @unittest.skip('not implement')
    def test_calc_shortest_path_simple_topology(self):
        """
        n1(src) --1-- n2(dst)
        """
        src = Switch("n1")
        dst = Switch("n2")
        links = [Link(src.name, dst.name, 1)]

        router = RouteCalculator([src, dst], links, src, dst)
        path = router.calc_shortest_path()

        self.assertIsNotNone(path)
        self.assertListEqual(path.links, links)

    @unittest.skip('not implement')
    def test_calc_shortest_path_complex_topology(self):
        """
        n01 --2-- n02 --3-- n03 --1-- n04
         |      /  |      /  |      /  |
         3    1    1    2    2    3    2
         |  /      |  /      |  /      |
        n05 --5-- n06 --3-- n07 --2-- n08
         |      /  |  \      |      /  |
         2    2    1    1    2    5    1
         |  /      |      \  |  /      |
        n09 --6-- n10 --1-- n11 --1-- n12
         |  \      |      /  |      /  |
         1    1    3    1    2    5    2
         |      \  |  /      |  /      |
        n13 --3-- n14 --2-- n15 --4-- n16
        """
        switches = [Switch(f"n{i}") for i in range(1, 17)]
        links = [
            Link("n1", "n2", 2),
            Link("n1", "n5", 3),
            Link("n2", "n3", 3),
            Link("n2", "n5", 1),
            Link("n2", "n6", 1),
            Link("n3", "n4", 1),
            Link("n3", "n6", 2),
            Link("n3", "n7", 2),
            Link("n4", "n7", 3),
            Link("n4", "n8", 2),
            Link("n5", "n6", 5),
            Link("n5", "n9", 2),
            Link("n6", "n7", 3),
            Link("n6", "n9", 2),
            Link("n6", "n10", 1),
            Link("n6", "n11", 1),
            Link("n7", "n8", 2),
            Link("n7", "n11", 2),
            Link("n8", "n11", 5),
            Link("n8", "n12", 1),
            Link("n9", "n10", 6),
            Link("n9", "n13", 1),
            Link("n9", "n14", 1),
            Link("n10", "n11", 1),
            Link("n10", "n14", 3),
            Link("n11", "n12", 1),
            Link("n11", "n14", 1),
            Link("n11", "n15", 2),
            Link("n12", "n15", 5),
            Link("n12", "n16", 2),
            Link("n13", "n14", 3),
            Link("n14", "n15", 2),
            Link("n15", "n16", 4),
        ]

        router = RouteCalculator(switches, links, Switch("n13"), Switch("n4"))
        path = router.calc_shortest_path()
        self.assertIsNotNone(path)
        self.assertListEqual(path.links, [
            links[21],
            links[13],
            links[6],
            links[5],
        ])

        router.set_dst(Switch("n16"))
        path = router.calc_shortest_path()
        self.assertIsNotNone(path)
        self.assertListEqual(path.links, [
            links[21],
            links[22],
            links[26],
            links[25],
            links[29],
        ])

    def test_calc_takahira_with_simple_topology(self):
        """
        h1-s --- s1 --1-- s2 --- h1-c
        """

        client = HostClient('h1-c', 's2', 100, 20)
        server = HostServer('h1-s', 's1')
        link = Link('s1', 's2', 1, 50)
        router = RouteCalculator(
            routing_algorithm=RoutingAlgorithm.TAKAHIRA,
            host_pairs=[[client, server]],
            switches=[Switch('s1'), Switch('s2')],
            links=[link]
        )
        path = router.calc_shortest_path(0, 30)

        self.assertEqual(len(path), 1)
        self.assertEqual(path[0][0], client)
        self.assertEqual(path[0][1], server)
        p: Path = path[0][2]
        self.assertListEqual(p.links, [DirectedLink.from_link(link, 's2', 's1')])

    def test_calc_takahira_considering_host_failure(self):
        """
        h1-s --- s1 --100-- s2 --- h2-c
                  |          |
                  1          10
                  |          |
        h2-s --- s3 --100-- s4 --- h1-c
        """

        # h2 pair should be preferred because it will fail earlier
        host_pairs = [
            [HostClient('h1-c', 's4', 1000, 20), HostServer('h1-s', 's1')],
            [HostClient('h2-c', 's2', 500, 20), HostServer('h2-s', 's3')],
        ]
        links = [
            Link('s1', 's2', 100, 1000),
            Link('s1', 's3', 1, 1000),
            Link('s2', 's4', 10, 1000),
            Link('s3', 's4', 100, 1000),
        ]
        router = RouteCalculator(
            routing_algorithm=RoutingAlgorithm.TAKAHIRA,
            host_pairs=host_pairs,
            switches=[Switch('s1'), Switch('s2'), Switch('s3'), Switch('s4')],
            links=links
        )
        paths = router.calc_shortest_path(0, 30)

        self.assertEqual(len(paths), 2)
        # path for h2 pair
        self.assertEqual(paths[0][0], host_pairs[1][0])
        self.assertEqual(paths[0][1], host_pairs[1][1])
        self.assertListEqual(paths[0][2].links, [
            DirectedLink.from_link(links[2], 's2', 's4'),
            DirectedLink.from_link(links[3], 's4', 's3'),
        ])
        # path for h1 pair
        self.assertEqual(paths[1][0], host_pairs[0][0])
        self.assertEqual(paths[1][1], host_pairs[0][1])
        self.assertListEqual(paths[1][2].links, [
            DirectedLink.from_link(links[3], 's4', 's3'),
            DirectedLink.from_link(links[1], 's3', 's1'),
        ])

    def test_calc_takahira_considering_link_failure(self):
        """
        h1-s --- s1 --100-- s2 --- h2-c
                 |          |
                 1          10
                 |          |
        h2-s --- s3 --100-- s4 --- h1-c
        """

        # h2 pair should be preferred because it will fail earlier
        host_pairs = [
            [HostClient('h1-c', 's4', 1000, 20), HostServer('h1-s', 's1')],
            [HostClient('h2-c', 's2', 500, 20), HostServer('h2-s', 's3')],
        ]
        links = [
            Link('s1', 's2', 100, 1000),
            Link('s1', 's3', 1, 1000),
            Link('s2', 's4', 10, 1000),
            Link('s3', 's4', 100, 100),
        ]
        router = RouteCalculator(
            routing_algorithm=RoutingAlgorithm.TAKAHIRA,
            host_pairs=host_pairs,
            switches=[Switch('s1'), Switch('s2'), Switch('s3'), Switch('s4')],
            links=links
        )

        # case1: before Link(s3-s4) fails
        paths = router.calc_shortest_path(0, 30)

        self.assertEqual(len(paths), 2)
        # path for h2 pair
        self.assertEqual(paths[0][0], host_pairs[1][0])
        self.assertEqual(paths[0][1], host_pairs[1][1])
        self.assertListEqual(paths[0][2].links, [
            DirectedLink.from_link(links[2], 's2', 's4'),
            DirectedLink.from_link(links[3], 's4', 's3'),
        ])
        # path for h1 pair
        self.assertEqual(paths[1][0], host_pairs[0][0])
        self.assertEqual(paths[1][1], host_pairs[0][1])
        self.assertListEqual(paths[1][2].links, [
            DirectedLink.from_link(links[3], 's4', 's3'),
            DirectedLink.from_link(links[1], 's3', 's1'),
        ])

        # case2: after Link(s3-s4) fails
        paths = router.calc_shortest_path(4, 30)

        self.assertEqual(len(paths), 2)
        # path for h2 pair
        self.assertEqual(paths[0][0], host_pairs[1][0])
        self.assertEqual(paths[0][1], host_pairs[1][1])
        self.assertListEqual(paths[0][2].links, [
            DirectedLink.from_link(links[0], 's2', 's1'),
            DirectedLink.from_link(links[1], 's1', 's3'),
        ])
        # path for h1 pair
        self.assertEqual(paths[1][0], host_pairs[0][0])
        self.assertEqual(paths[1][1], host_pairs[0][1])
        self.assertListEqual(paths[1][2].links, [
            DirectedLink.from_link(links[2], 's4', 's2'),
            DirectedLink.from_link(links[0], 's2', 's1'),
        ])

    def test_calc_takahira_considering_data_size(self):
        """
        h1-s --- s1 --100-- s2 --- h2-c
                 |          |
                 1          10
                 |          |
        h2-s --- s3 --100-- s4 --- h1-c
        """

        # h2 pair should be preferred because it has more data
        host_pairs = [
            [HostClient('h1-c', 's4', 1000, 20), HostServer('h1-s', 's1')],
            [HostClient('h2-c', 's2', 1000, 100), HostServer('h2-s', 's3')],
        ]
        links = [
            Link('s1', 's2', 100, 1000),
            Link('s1', 's3', 1, 1000),
            Link('s2', 's4', 10, 1000),
            Link('s3', 's4', 100, 1000),
        ]
        router = RouteCalculator(
            routing_algorithm=RoutingAlgorithm.TAKAHIRA,
            host_pairs=host_pairs,
            switches=[Switch('s1'), Switch('s2'), Switch('s3'), Switch('s4')],
            links=links
        )

        paths = router.calc_shortest_path(0, 30)

        self.assertEqual(len(paths), 2)
        # path for h2 pair
        self.assertEqual(paths[0][0], host_pairs[1][0])
        self.assertEqual(paths[0][1], host_pairs[1][1])
        self.assertListEqual(paths[0][2].links, [
            DirectedLink.from_link(links[2], 's2', 's4'),
            DirectedLink.from_link(links[3], 's4', 's3'),
        ])
        # path for h1 pair
        self.assertEqual(paths[1][0], host_pairs[0][0])
        self.assertEqual(paths[1][1], host_pairs[0][1])
        self.assertListEqual(paths[1][2].links, [
            DirectedLink.from_link(links[3], 's4', 's3'),
            DirectedLink.from_link(links[1], 's3', 's1'),
        ])


if __name__ == '__main__':
    unittest.main()
