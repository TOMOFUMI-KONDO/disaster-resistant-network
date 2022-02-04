import unittest

from router import Router, Node, Link


class RouterTest(unittest.TestCase):
    def test_calc_shortest_path_simple_topology(self):
        """
        n1(src) --1-- n2(dst)
        """
        src = Node(1)
        dst = Node(2)
        links = [Link(src.name, dst.name, 1)]

        router = Router([src, dst], links, src, dst)
        path = router.calc_shortest_path()

        self.assertListEqual(path.links, links)

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
        nodes = [Node(i) for i in range(1, 17)]
        links = [
            Link(1, 2, 2),
            Link(1, 5, 3),
            Link(2, 3, 3),
            Link(2, 5, 1),
            Link(2, 6, 1),
            Link(3, 4, 1),
            Link(3, 6, 2),
            Link(3, 7, 2),
            Link(4, 7, 3),
            Link(4, 8, 2),
            Link(5, 6, 5),
            Link(5, 9, 2),
            Link(6, 7, 3),
            Link(6, 9, 2),
            Link(6, 10, 1),
            Link(6, 11, 1),
            Link(7, 8, 2),
            Link(7, 11, 2),
            Link(8, 11, 5),
            Link(8, 12, 1),
            Link(9, 10, 6),
            Link(9, 13, 1),
            Link(9, 14, 1),
            Link(10, 11, 1),
            Link(10, 14, 3),
            Link(11, 12, 1),
            Link(11, 14, 1),
            Link(11, 15, 2),
            Link(12, 15, 5),
            Link(12, 16, 2),
            Link(13, 14, 3),
            Link(14, 15, 2),
            Link(15, 16, 4),
        ]

        router = Router(nodes, links, Node(13), Node(4))
        self.assertListEqual(router.calc_shortest_path().links, [
            links[21],
            links[13],
            links[6],
            links[5],
        ])

        router.set_dst(Node(16))
        self.assertListEqual(router.calc_shortest_path().links, [
            links[21],
            links[22],
            links[26],
            links[25],
            links[29],
        ])


if __name__ == '__main__':
    unittest.main()
