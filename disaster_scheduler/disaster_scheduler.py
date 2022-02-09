from time import sleep

from mininet.log import info


class DisasterScheduler(object):
    def __init__(self, switches):
        self.__switches = switches

    def run(self):
        s = self.__switches[0]

        # time until disaster arrives
        sleep(10)

        # disaster arrives
        info("*** Link between s1 and s2 is being swept by tsunami...\n")
        s.cmd("ovs-vsctl del-port s1-eth1")
        s.cmd("ovs-vsctl del-port s2-eth1")

        sleep(60)
        info("*** Link between s3 and s4 is being swept by tsunami...\n")
        s.cmd("ovs-vsctl del-port s3-eth2")
        s.cmd("ovs-vsctl del-port s4-eth2")
