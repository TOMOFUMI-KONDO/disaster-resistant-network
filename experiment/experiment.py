from time import sleep

import requests
from mininet.log import info, error
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from disaster_scheduler import DisasterScheduler, Failure
from enums import Network


class Experiment(object):
    def __init__(self, network: Network, chunk: int):
        self.__network = network
        self.__chunk = chunk

        self.__net = Mininet(
            topo=DisasterResistantNetworkTopo(),
            controller=RemoteController("c0", port=6633),
        )
        hosts = self.__net.hosts
        self.__receiver, self.__sender = hosts[0], hosts[1]

        self.__disaster_scheduler = DisasterScheduler(self.__net.switches)

    def run(self):
        self.__net.start()

        self.__set_stp()
        self.__prepare_backup()
        self.__net.pingAll()

        # assume that a disaster was detected
        self.__start_backup()
        self.__disaster_scheduler.run([
            Failure("s1", 1, "s2", 1, 100),
            Failure("s3", 2, "s4", 2, 220)
        ])

        sleep(250)

        self.__net.stop()

    # prepare for back up data
    def __set_stp(self):
        for s in self.__net.switches:
            s.vsctl('set bridge', s, 'stp-enable=true')

        info('*** waiting to set STP...\n')
        sleep(60)

    def __prepare_backup(self):
        network_name = self.__network_name()
        self.__receiver.cmd(f"./bin/{network_name}/server -v > log/server_{network_name}.log 2>&1 &")
        # receiver.cmd(f"./bin/server -v > server/{datetime.now().strftime('%Y%m%d_%H%M%S')}.log &")

        info('*** waiting to boot server...\n')
        sleep(5)

    def __start_backup(self):
        info("*** Disaster was predicted and start emergency backup!\n")

        network_name = self.__network_name()
        self.__sender.cmd(f"./bin/{network_name}/client -addr {self.__receiver.IP()}:44300 -chunk {self.__chunk} "
                          f"> log/client_{network_name}.log 2>&1 &")

        r = requests.post('http://localhost:8080/disaster/notify')
        if r.status_code != 200:
            error("failed to notify disaster to controller: %d %s", r.status_code, r.text)

    def __network_name(self) -> str:
        return self.__network.name.lower()
