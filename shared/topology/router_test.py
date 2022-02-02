import unittest

from shared.topology.router import Router, Node, Link


class RouterTest(unittest.TestCase):
    def test_calc_shortest_path_simple_topology(self):
        """
        n1(src) --1-- n2(dst)
        """
        src = Node("n1")
        dst = Node("n2")
        links = [Link("l1", src.name, dst.name, 1)]

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

        start: n13, dest: n04
        """
        nodes = [Node(f"n{i}") for i in range(1, 17)]
        links = [
            Link("l1", "n1", "n2", 2),
            Link("l2", "n1", "n5", 3),
            Link("l3", "n2", "n3", 3),
            Link("l4", "n2", "n5", 1),
            Link("l5", "n2", "n6", 1),
            Link("l6", "n3", "n4", 1),
            Link("l7", "n3", "n6", 2),
            Link("l8", "n3", "n7", 2),
            Link("l9", "n4", "n7", 3),
            Link("l10", "n4", "n8", 2),
            Link("l11", "n5", "n6", 5),
            Link("l12", "n5", "n9", 2),
            Link("l13", "n6", "n7", 3),
            Link("l14", "n6", "n9", 2),
            Link("l15", "n6", "n10", 1),
            Link("l16", "n6", "n11", 1),
            Link("l17", "n7", "n8", 2),
            Link("l18", "n7", "n11", 2),
            Link("l19", "n8", "n11", 5),
            Link("l20", "n8", "n12", 1),
            Link("l21", "n9", "n10", 6),
            Link("l22", "n9", "n13", 1),
            Link("l23", "n9", "n14", 1),
            Link("l24", "n10", "n11", 1),
            Link("l25", "n10", "n14", 3),
            Link("l26", "n11", "n12", 1),
            Link("l27", "n11", "n14", 1),
            Link("l28", "n11", "n15", 2),
            Link("l29", "n12", "n15", 5),
            Link("l30", "n12", "n16", 2),
            Link("l31", "n13", "n14", 3),
            Link("l32", "n14", "n15", 2),
            Link("l33", "n15", "n16", 4),
        ]

        router = Router(nodes, links, Node("n13"), Node("n4"))
        self.assertListEqual(router.calc_shortest_path().links, [
            Link("l22", "n9", "n13", 1),
            Link("l14", "n6", "n9", 2),
            Link("l7", "n3", "n6", 2),
            Link("l6", "n3", "n4", 1),
        ])


if __name__ == '__main__':
    unittest.main()
