import unittest

from shared.topology.router import Router, Node, Link


class RouterTest(unittest.TestCase):
    def test_calc(self):
        """
        n1(src) --- n2(dst)
        """
        src = Node("n1")
        dst = Node("n2")
        links = [Link("l1", src.name, dst.name, 1)]

        router = Router([src, dst], links, src, dst)
        path = router.calc_shortest_path()

        self.assertListEqual(path.links, links)


if __name__ == '__main__':
    unittest.main()
