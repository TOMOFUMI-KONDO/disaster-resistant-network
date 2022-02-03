import unittest

from router import Router, Node, Link


class RouterTest(unittest.TestCase):
    def test_calc_shortest_path_simple_topology(self):
        """
        n1(src) --1-- n2(dst)
        """
        src = Node("n1")
        dst = Node("n2")
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
        nodes = [Node(f"n{i}") for i in range(1, 17)]
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

        router = Router(nodes, links, Node("n13"), Node("n4"))
        self.assertListEqual(router.calc_shortest_path().links, [
            links[21],
            links[13],
            links[6],
            links[5],
        ])

        router.set_dst(Node("n16"))
        self.assertListEqual(router.calc_shortest_path().links, [
            links[21],
            links[22],
            links[26],
            links[25],
            links[29],
        ])


if __name__ == '__main__':
    unittest.main()
