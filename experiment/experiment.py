from time import sleep

import requests
from mininet.log import info, error
from mininet.net import Mininet
from mininet.node import RemoteController

from disaster_resistant_network_topo import DisasterResistantNetworkTopo
from disaster_scheduler import DisasterScheduler, LinkFailure, HostFailure
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
        self.__host_pairs = [{'client': hosts[i * 2], 'server': hosts[i * 2 + 1]} for i in range(len(hosts) // 2)]

        self.__disaster_scheduler = DisasterScheduler(self.__net.switches)

    def run(self):
        self.__net.start()

        self.__set_stp()
        self.__prepare_backup()
        self.__net.pingAll()

        # assume that a disaster was detected
        self.__start_backup()
        self.__disaster_scheduler.run([
            LinkFailure("s1", 1, "s2", 1, 100),
            HostFailure("h1c", "s4", 3, 220),
            HostFailure("h2c", "s2", 3, 400),
        ])

        # wait until disaster finishes
        sleep(450)

        self.__net.stop()

        # cleanup time
        sleep(10)

    # prepare for back up data
    def __set_stp(self):
        for s in self.__net.switches:
            s.vsctl('set bridge', s, 'stp-enable=true')

        info('*** waiting to set STP...\n')
        sleep(60)

    def __prepare_backup(self):
        network_name = self.__network_name()
        for hp in self.__host_pairs:
            server = hp['server']
            server.cmd(f"./bin/{network_name}/server -v > log/{network_name}/{server.name}.log 2>&1 &")

        info('*** waiting to boot server...\n')
        sleep(5)

    def __start_backup(self):
        info("*** Disaster was predicted and start emergency backup!\n")

        network_name = self.__network_name()
        for hp in self.__host_pairs:
            client = hp['client']
            server = hp['server']
            client.cmd(f"./bin/{network_name}/client -addr {server.IP()}:44300 -chunk {self.__chunk} "
                       f"> log/{network_name}/{client.name}.log 2>&1 &")

        r = requests.post('http://localhost:8080/disaster/notify')
        if r.status_code != 200:
            error("failed to notify disaster to controller: %d %s", r.status_code, r.text)

    def __network_name(self) -> str:
        return self.__network.name.lower()
