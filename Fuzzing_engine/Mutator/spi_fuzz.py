import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
import struct
import time
import random
# from spitest.spi_parser import load_json_config, parse_sma760_frame
from Fuzzing_engine.Mutator.spi_mutator import mutation, select_seed, corpus_record
from Fuzzing_engine.Mutator.uds_analyzer import UdsAnalyzer
from ZDCANLib.ZDutility import zd_utility
from ZDCANLib.ZDuds import zd_uds
import lauterbach.trace32.rcl as t32


# Calculate CRC
def sma7drvr_GetCalcRxCrc3(CalcData):
    poly = 0xB  # poly 0b1011
    init = 0x7  # init 0b111
    data_bin = CalcData & 0x07FFFFF8  # data26~3bit|crc
    crc = init
    
    for i in range(27):
        do_xor = (crc & 0x04) >> 2
        crc = ((crc << 1) | (0x01 & (data_bin >> (26 - i)))) & 0x07
        if do_xor:
            crc ^= poly
        crc &= 0x07
    
    return crc


# Extract arbitrary bit segments from bytes
def extract_bits(data, start_bit, end_bit):
    bit_length = end_bit - start_bit
    total_bits = 32
    if start_bit < 0 or end_bit > total_bits:
        raise ValueError("Bit range exceeds the byte array bounds.")
    
    # Convert the entire byte stream into an integer 
    # for convenient bitwise operations.
    total_value = int.from_bytes(data, byteorder='big')
    
    # Extract the bit segment from start_bit to end_bit
    mask = (1 << bit_length) - 1
    extracted_value = (total_value >> (total_bits - end_bit)) & mask
    return extracted_value


# Read last two lines from spilog
def read_last_two_lines(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    return lines[-2:]


# Initialize seed corpus * 2
def process_last_two_lines_and_init_corpus(last_two_lines):
    # Init corpus -- treat a log entry as a seed
    corpus_len16 = {}
    corpus_len28 = {}
    duration_dict = {}

    # Add an initial seed
    for line in last_two_lines:
        line = line.strip().strip('{}')
        data_part, duration_part = line.split(':')

        # Store the byte data of a log entry in a bytearray
        line_data = bytearray()
        data_part = data_part.split(',')
        for x in data_part:
            x = x.strip().rstrip('}')
            if x.startswith('0x'):
                line_data.append(int(x, 16))
            else:
                line_data.append(int(x))
        duration_dict[bytes(line_data)] = int(duration_part.strip())

        if len(data_part) == 16:
            # Convert the bytearray to bytes to ensure the seed is hashable
            corpus_len16[bytes(line_data)] = 1
        elif len(data_part) == 28:
            corpus_len28[bytes(line_data)] = 1
    
    return corpus_len16, corpus_len28, duration_dict
    

# Replace the original position with the mutated data segment
def modify_spi_commands(spi_command, start_bit, end_bit, D):
    if D is None:
        print(type(D), D)
        raise ValueError("D cannot be None. Please provide a valid integer for D.")

    bit_length = end_bit - start_bit
    total_bits = len(spi_command) * 8
    total_value = int.from_bytes(spi_command, 'big')
    
    # Construct a mask for replacing the data segment
    mask = (1 << bit_length) - 1
    mask_shifted = mask << (total_bits - end_bit - 1)

    # Clear the original value and insert the mutated value
    total_value = (total_value & ~mask_shifted) | (D << (total_bits - end_bit - 1))
    
    # Recalculate the CRC
    new_crc = sma7drvr_GetCalcRxCrc3(total_value)

    # Apply the new CRC
    total_value = (total_value & 0xFFFFFFF8) | new_crc

    return total_value.to_bytes(len(spi_command), 'big')


# Initialization Phase
def read_spilog(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    aTxBuffers1 = []
    aTxBuffers2 = []
    sequenceRepeatCounts1 = []
    sequenceRepeatCounts2 = []

    for line in lines[:-2]:
        line = line.strip()
        if line.startswith('{') and '//' in line:
            data_part, comment_part = line.split('//')
            data = [int(x.strip().rstrip('}'), 16) for x in data_part.strip('{}').split(',') if x.strip()]
            repeat_count = int(comment_part.split()[0])
            
            if len(data) == 16:
                aTxBuffers1.append(data)
                sequenceRepeatCounts1.append(repeat_count)
            elif len(data) == 28:
                aTxBuffers2.append(data)
                sequenceRepeatCounts2.append(repeat_count)

    return aTxBuffers1, aTxBuffers2, sequenceRepeatCounts1, sequenceRepeatCounts2


# Mutate periodic spilog
def process_and_modify_periodic_spilog(seed_len16, seed_len28, duration_dict, start_bit=4, end_bit=20):
    duration_len16 = duration_dict[bytes(seed_len16)]
    duration_len28 = duration_dict[bytes(seed_len28)]
    
    # Store the data as a list
    data_list = []
    data_list.append(list(seed_len16))
    data_list.append(list(seed_len28))

    modified_log = bytearray()
    for data in data_list:
        modified_data = bytearray(data)
        # For each log containing multiple 32-bit data segments,
        # mutate one segment and then concatenate
        spi_pos = random.randint(0, len(data)//4 - 1)
        one_data = bytearray()
        for x in data[spi_pos*4:(spi_pos+1)*4]:
            one_data.append(x)

        #### Binding mutation operators to the bit fields of SPI instructions ###
        # Extract the start and end positions of the input/output data fields
        bit_length = end_bit - start_bit
        # Extract the entire data field
        D = extract_bits(one_data, start_bit, end_bit)
        # Mutate the data field (payload)
        mutated_D = mutation(data=D, bit_length=bit_length, min_v=-128, max_v=128)
        # Overwrite the original data field
        modified_command = modify_spi_commands(one_data, start_bit, end_bit, mutated_D)
        # Construct a new log entry
        modified_data = modified_data[:spi_pos*4] + modified_command + modified_data[(spi_pos+1)*4:]
        modified_log += modified_data
        # Pack duration
        if len(data) == 16:
            modified_log += struct.pack('<I', duration_len16)
        elif len(data) == 28:
            modified_log += struct.pack('<I', duration_len28)

    return modified_log


def send_data_over_can(uds, data, is_last_two_lines=False):
    chunk_size = 7  # Reduced to accommodate sequence number
    total_chunks = len(data) // chunk_size + (1 if len(data) % chunk_size else 0)
    
    # Send total number of chunks first
    uds.can.send(0x321, struct.pack('>IB', total_chunks, int(is_last_two_lines)) + b'\x00\x00\x00')
    time.sleep(0.01)

    for seq in range(total_chunks):
        chunk = data[seq*chunk_size:(seq+1)*chunk_size]
        if len(chunk) < chunk_size:
            chunk = chunk.ljust(chunk_size, b'\x00')
        
        message = struct.pack('B', seq % 256) + chunk
        
        # Send chunk and wait for ACK
        retries = 0
        while retries < 3:
            uds.can.send(0x321, message)
            
            # Wait for ACK
            ack = uds.can.recv(0x123, timeout=100)
            if ack and ack.data[0] == seq % 256:
                break
            retries += 1
            time.sleep(0.01)
        
        if retries == 3:
            print(f"Failed to receive ACK for chunk {seq}")
            return False

    return True


# Comprehensive work flow
def fuzz(uds, spilog_file, elf_file):
    last_two_lines = read_last_two_lines(spilog_file)
    # Initialize a seed corpus
    corpus_len16, corpus_len28, duration_dict = process_last_two_lines_and_init_corpus(last_two_lines)
    
    # Initialize a monitor
    monitor = UdsAnalyzer(uds, elf_file)

    # Send periodically
    while True:
        # Select a seed to mutate according to fitness
        seed_len16, seed_len28 = select_seed(corpus_len16, corpus_len28)

        # Mutate
        # select one instruction segment to mutate, 
        # then reassemble into a mutated log
        mutated_spilog = process_and_modify_periodic_spilog(seed_len16, seed_len28, duration_dict)
        
        # Send mutated data
        flag = send_data_over_can(uds, mutated_spilog, is_last_two_lines=True)
        if flag:
            print("Mutated periodic spilog sent complete!!")
        else:
            print("Failed to send.")

        # Monitor
        has_error = monitor.monitor(mutated_spilog)

        # Feedback mechanism
        if has_error:
            # Record the data
            corpus_record(mutated_spilog)

            # Adjust fitness based on feedback
            corpus_len16[seed_len16] = 1 if seed_len16 not in corpus_len16 else 1.1*corpus_len16[seed_len16]
            corpus_len28[seed_len28] = 1 if seed_len28 not in corpus_len28 else 1.1*corpus_len28[seed_len28]
            break
        # time.sleep(0.001)  # Adjust this value to control the sending frequency


def spi_fuzz():
    config = zd_utility.LoadJson("Config/config.json")
    uds = zd_uds(config)

    aTxBuffers1, aTxBuffers2, sequenceRepeatCounts1, sequenceRepeatCounts2 = read_spilog("Config/spilog.txt")
    
    data = b''
    data = struct.pack('<II', len(aTxBuffers1), len(aTxBuffers2))
    for buffer in aTxBuffers1:
        data += struct.pack('16B', *buffer)
    for buffer in aTxBuffers2:
        data += struct.pack('28B', *buffer)
    data += struct.pack(f'{len(sequenceRepeatCounts1)}I', *sequenceRepeatCounts1)
    data += struct.pack(f'{len(sequenceRepeatCounts2)}I', *sequenceRepeatCounts2)

    # Initializing
    if send_data_over_can(uds, data):
        print("Main data transmission complete")
        print("###########################################")
    else:
        print("Main data transmission failed")
        print("###########################################")

    # Fuzzing
    fuzz(uds, "Config/spilog.txt", "Config/symbol_table.sym")


if __name__ == "__main__":
    spi_fuzz()
