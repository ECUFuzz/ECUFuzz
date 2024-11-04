import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import threading

from Fuzzing_engine.Mutator.spi_fuzz import spi_fuzz
from Fuzzing_engine.Mutator.can_fuzz import can_fuzz


def main():

    # create Threads
    spi = threading.Thread(target=spi_fuzz)
    can = threading.Thread(target=can_fuzz)
    
    # start Threads
    spi.start()
    can.start()

    # wait for end
    spi.join()
    can.join()


if __name__ == "__main__":
    main()
