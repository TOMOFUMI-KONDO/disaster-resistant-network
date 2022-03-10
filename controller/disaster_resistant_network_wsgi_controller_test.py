import json
import subprocess
import unittest
from time import sleep

import requests
from mininet import net, node, topo, link


class DisasterResistantNetworkWsgiControllerTestTopo(topo.Topo):
    def build(self, *args, **params):
        # add switches
        self.addSwitch("s1", dpid="1")
        self.addSwitch("s2", dpid="2")
        self.addLink("s1", "s2", cls=link.TCLink, bw=1000)

        # add hosts
        self.addHost("h1c", ip="10.0.0.1", mac="00:00:00:00:00:01")
        self.addLink("h1c", "s1", cls=link.TCLink, bw=1000)
        self.addHost("h1s", ip="10.0.0.2", mac="00:00:00:00:00:02")
        self.addLink("h1s", "s2", cls=link.TCLink, bw=1000)


class DisasterResistantNetworkWsgiControllerTest(unittest.TestCase):
    __URL = "http://localhost:8080"

    def setUp(self):
        self.__ryu_manager = subprocess.Popen(["ryu-manager", "disaster_resistant_network_controller.py"])
        sleep(5)

        self.__mininet = net.Mininet(
            topo=DisasterResistantNetworkWsgiControllerTestTopo(),
            controller=node.RemoteController("c0", port=6633),
        )
        self.__mininet.start()

    def tearDown(self):
        self.__mininet.stop()
        self.__ryu_manager.kill()

    def testComponents(self):
        # add s1
        res = requests.post(self.__URL + "/switch", data=json.dumps({
            "name": "s1",
            "dpid": 1,
            "neighbors": [{
                "port": 1,
                "name": "s2",
                "bandwidth_mbps": 1000,
                "fail_at_sec": -1,
            }]
        }))
        self.assertEqual(200, res.status_code)

        # add s2
        res = requests.post(self.__URL + "/switch", data=json.dumps({
            "name": "s2",
            "dpid": 2,
            "neighbors": [{
                "port": 1,
                "name": "s1",
                "bandwidth_mbps": 1000,
                "fail_at_sec": -1,
            }]
        }))
        self.assertEqual(200, res.status_code)

        res = requests.get(self.__URL + "/switch")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({
            "result": "success",
            "data": {"switches": ["s1", "s2"]}
        }, json.loads(res.json()))

        res = requests.get(self.__URL + "/link")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({
            "result": "success",
            "data": {"links": [{
                "switch1": "s1",
                "switch2": "s2",
                "bandwidth_mbps": 1000,
                "fail_at_sec": -1,
            }]}
        }, json.loads(res.json()))

        res = requests.get(self.__URL + "/port-to-switch")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({
            "result": "success",
            "data": {"port_to_switch": {
                "1": {"1": "s2"},
                "2": {"1": "s1"}
            }}
        }, json.loads(res.json()))

        # add host pair
        res = requests.post(self.__URL + "/host-pair", data=json.dumps({
            "client": {
                "name": "h1c",
                "neighbor": "s1",
                "fail_at_sec": 100,
                "datasize_gb": 10,
                "ip_address": "10.0.0.1",
                "port": 2
            },
            "server": {
                "name": "h1s",
                "neighbor": "s2",
                "ip_address": "10.0.0.2",
                "port": 2
            }
        }))
        self.assertEqual(200, res.status_code)

        res = requests.get(self.__URL + "/host-pair")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({
            "result": "success",
            "data": {
                "host_pairs": [
                    {
                        "client": {
                            "name": "h1c",
                            "neighbor": "s1",
                            "fail_at_sec": 100,
                            "datasize_gb": 10,
                            "ip_address": "10.0.0.1"
                        },
                        "server": {
                            "name": "h1s",
                            "neighbor": "s2",
                            "ip_address": "10.0.0.2"
                        }
                    }
                ]
            }
        }, json.loads(res.json()))


if __name__ == '__main__':
    unittest.main()
