from argparse import Namespace, ArgumentParser

from mininet.log import setLogLevel

from enums import Network
from experiment.experiment import Experiment


def main():
    args = parse()
    setLogLevel(args.log)

    for n in [Network.TCP, Network.QUIC]:
        experiment = Experiment(n)
        experiment.run()


def parse() -> Namespace:
    parser = ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


if __name__ == "__main__":
    main()
