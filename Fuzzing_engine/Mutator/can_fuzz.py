import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import cantools
import random
from Fuzzing_engine.Mutator.uds_analyzer import UdsAnalyzer
from ZDCANLib.ZDutility import zd_utility
from ZDCANLib.ZDuds import zd_uds


# Parse DBC files, extracting message configurations 
# including identifiers, signal definitions, and timing parameters.
class CANMutator:
    def __init__(self, uds, dbc_file, elf_file):
        self.db = cantools.database.load_file(dbc_file)
        self.uds = uds
        self.elf_file = elf_file

    def mutate_and_send_messages(self):
        """
        Mutates random signals in each message in the DBC file by adjusting
        their values within the specified min and max ranges.
        """
        monitor = UdsAnalyzer(self.uds, self.elf_file)

        for message in self.db.messages:
            # Mutate a random set of signals within each message
            mutated_signals = self.mutate_random_signals(message)
            encoded_message = self.encode_message(message, mutated_signals)
            
            # Send mutated message
            try:
                self.uds.can.send(message.frame_id, encoded_message)
                print("Send mutated CAN messages successfully.")
            except Exception as e:
                print(f"Failed to send mutated CAN messages with error {e}")
                break

            has_error = monitor.monitor(encoded_message)

            if has_error:
                with open('can_msg_corpus.txt', 'a') as f:
                    f.write(f"{encoded_message}\n")

    def mutate_random_signals(self, message):
        """
        Randomly mutates one or more signals within a CAN message.
        
        Returns:
            dict: The mutated signals as a dictionary of signal names and values.
        """
        mutated_signals = {}
        # Randomly decide the number of signals to mutate (at least one signal)
        num_signals_to_mutate = random.randint(1, len(message.signals))
        signals_to_mutate = random.sample(message.signals, num_signals_to_mutate)
        
        for signal in signals_to_mutate:
            # Mutate each selected signal within its min-max range
            # the min/max are scaled/physical values
            min_val, max_val = signal.minimum, signal.maximum
            if min_val is not None and max_val is not None:
                # Generate a random value within the signal's range
                mutated_value = random.uniform(min_val, max_val)
            else:
                # If no bounds are defined, fallback to a default range (optional)
                mutated_value = random.uniform(0, 1)
                
            # Apply scaling and offset if defined
            mutated_signals[signal.name] = mutated_value

        return mutated_signals

    def encode_message(self, message, mutated_signals) -> bytes:
        """
        Encodes the mutated signals into a CAN message.
        
        Returns:
            bytes: The encoded CAN message as bytes.
        """
        return message.encode(mutated_signals)


def can_fuzz():
    config = zd_utility.LoadJson("Config/config1.json")
    uds = zd_uds(config)

    dbc_file = f"{parent_dir}/Config/Chery_E03_E0Y.dbc"
    elf_file = f"{parent_dir}/Config/symbol_table.sym"
    can_fuzz = CANMutator(uds, dbc_file, elf_file)

    # Fuzzing
    can_fuzz.mutate_and_send_messages()

if __name__ == "__main__":
    can_fuzz()
