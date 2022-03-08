import json
import subprocess
import unittest
from time import sleep

import requests


class DisasterResistantNetworkWsgiControllerTest(unittest.TestCase):
    __URL = "http://localhost:8080"

    def setUp(self):
        self.__ryu_manager = subprocess.Popen(["ryu-manager", "disaster_resistant_network_controller.py"])
        sleep(3)

    def tearDown(self):
        self.__ryu_manager.kill()

    def testAddSwitch(self):
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
        self.assertEqual(res.status_code, 200)
        self.assertDictEqual({
            "result": "success",
            "data": {"switches": ["s1", "s2"]}
        }, json.loads(res.json()))

        res = requests.get(self.__URL + "/link")
        self.assertEqual(res.status_code, 200)
        self.assertDictEqual({
            "result": "success",
            "data": {"links": [["s1", "s2"]]}
        }, json.loads(res.json()))

        res = requests.get(self.__URL + "/port-to-switch")
        self.assertEqual(res.status_code, 200)
        self.assertDictEqual({
            "result": "success",
            "data": {"port_to_switch": {
                "1": {"1": "s2"},
                "2": {"1": "s1"}
            }}
        }, json.loads(res.json()))


if __name__ == '__main__':
    unittest.main()
