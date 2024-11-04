import json
import re

def merge_fields(data):
    for instruction in data.values():
        for direction in ['MOSI', 'MISO']:
            if direction in instruction:
                merged = {}
                to_merge = {
                    'CRC': ['CRC0', 'CRC1', 'CRC2', 'CRC3', 'CRC4', 'CRC5', 'CRC6', 'CRC7'],
                    'Adr': ['Adr1', 'Adr2', 'Adr3', 'Adr4', 'Adr5', 'Adr6', 'Adr7'],
                    'CH': ['CH0', 'CH1', 'CH2', 'CH3', 'CH4'],
                    # 'S': ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
                    'SID': ['SID0', 'SID1', 'SID2', 'SID3', 'SID4', 'SID10', 'SID11', 'SID12', 'SID13', 'SID14', 'SID20', 'SID21', 'SID22', 'SID23', 'SID24'],
                    'D': ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'],
                    'OFF': ['OFF0', 'OFF1', 'OFF2', 'OFF3', 'OFF4', 'OFF5', 'OFF6', 'OFF7', 'OFF8', 'OFF9', 'OFF10', 'OFF11', 'OFF12', 'OFF13', 'OFF14', 'OFF15'],
                    'OCL': ['OCL10', 'OCL11', 'OCL12', 'OCL20', 'OCL21', 'OCL22'],
                    'OC': ['OC10', 'OC11', 'OC20', 'OC21'],
                    'CC': ['CC0', 'CC1', 'CC2', 'CC3', 'CC4', 'CC5', 'CC6', 'CC7', 'CC8', 'CC9', 'CC10', 'CC11', 'CC12', 'CC13', 'CC14', 'CC15'],
                    'TMD': ['TMD10', 'TMD11', 'TMD20', 'TMD21'],
                    'LPF': ['LPF10', 'LPF11', 'LPF20', 'LPF21'],
                    'SR': ['SR0', 'SR1', 'SR2', 'SR3', 'SR4', 'SR5', 'SR6', 'SR7', 'SR8', 'SR9', 'SR10', 'SR11', 'SR12', 'SR13', 'SR14', 'SR15'],
                    'EOP': ['EOP0', 'EOP1', 'EOP2', 'EOP3', 'EOP4', 'EOP5', 'EOP6', 'EOP7', 'EOP8', 'EOP9', 'EOP10', 'EOP11', 'EOP12', 'EOP13', 'EOP14', 'EOP15'],
                    'PST': ['PST0', 'PST1', 'PST2', 'PST3', 'PST4', 'PST5', 'PST6', 'PST7'],
                    'NST': ['NST0', 'NST1', 'NST2', 'NST3', 'NST4', 'NST5', 'NST6', 'NST7'],
                    'RAW': ['RAW0', 'RAW1', 'RAW2', 'RAW3', 'RAW4', 'RAW5', 'RAW6', 'RAW7', 'RAW8', 'RAW9', 'RAW10', 'RAW11', 'RAW12', 'RAW13'],
                    'SN': ['SN0', 'SN1', 'SN2', 'SN3', 'SN4', 'SN5', 'SN6', 'SN7', 'SN8', 'SN9', 'SN10', 'SN11', 'SN12', 'SN13', 'SN14', 'SN15',
                           'SN16', 'SN17', 'SN18', 'SN19', 'SN20', 'SN21', 'SN22', 'SN23', 'SN24', 'SN25', 'SN26', 'SN27', 'SN28', 'SN29', 'SN30', 'SN31',
                           'SN32', 'SN33', 'SN34', 'SN35', 'SN36', 'SN37', 'SN38', 'SN39', 'SN40', 'SN41', 'SN42', 'SN43', 'SN44', 'SN45', 'SN46', 'SN47'],
                    'VM': ['VM0', 'VM1', 'VM2', 'VM3'],
                    'EDID': ['EDID0', 'EDID1', 'EDID2', 'EDID3', 'EDID4', 'EDID5', 'EDID6', 'EDID7'],
                    'DID': ['DID0', 'DID1', 'DID2', 'DID3', 'DID4', 'DID5', 'DID6', 'DID7'],
                    # 'MON': ['MON0', 'MON1', 'MON2', 'MON3', 'MON4', 'MON5', 'MON6', 'MON7', 'MON8', 'MON9', 'MON10', 'MON11', 'MON12', 'MON13', 'MON14', 'MON15'],
                }
                
                for new_key, old_keys in to_merge.items():
                    present_keys = [k for k in old_keys if k in instruction[direction]]
                    if present_keys:
                        start = min(instruction[direction][k][0] for k in present_keys)
                        end = max(instruction[direction][k][1] for k in present_keys)
                        merged[new_key] = [start, end]
                        for k in present_keys:
                            instruction[direction].pop(k)
                
                instruction[direction].update(merged)
    return data

def parse_field(field, bits, bit_indices, miso_zip, mosi_zip):
    field_name = field.split('(')[0].strip()
    
    # Extract range if present
    range_match = re.search(r'\((.*?)\)', field)
    if range_match:
        range_str = range_match.group(1)
        range_parts = range_str.split('...')
        
        if len(range_parts) == 2:  # Multi-bit field
            start, end = range_parts
            return parse_multi_bit_field(field_name, start, end, bit_indices, miso_zip, mosi_zip)
        elif len(range_parts) == 1:  # Single-bit field
            return parse_single_bit_field(field_name, range_parts[0], bit_indices, miso_zip, mosi_zip)
    else:  # Field without parentheses
        return parse_single_bit_field(field_name, field_name, bit_indices, miso_zip, mosi_zip)

def parse_multi_bit_field(field_name, start, end, bit_indices, miso_zip, mosi_zip):
    start_index = end_index = None
    for zip_data in [miso_zip, mosi_zip]:
        for bit, value in zip_data:
            if value == start:
                start_index = bit_indices[zip_data.index((bit, value))]
            if value == end:
                end_index = bit_indices[zip_data.index((bit, value))]
            if start_index is not None and end_index is not None:
                return field_name, [min(start_index, end_index), max(start_index, end_index) + 1]
    return None, None

def parse_single_bit_field(field_name, bit_name, bit_indices, miso_zip, mosi_zip):
    for zip_data in [miso_zip, mosi_zip]:
        for bit, value in zip_data:
            if bit == bit_name or value == bit_name:
                bit_index = bit_indices[zip_data.index((bit, value))]
                return field_name, [bit_index, bit_index + 1]
    return None, None

def parse_smi7_instructions(content):
    instructions = {}
    current_instruction = None
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and not line.startswith('Bit'):
            current_instruction = line
            if "RD_MONITOR_I_DATA" == current_instruction:
                pass
            instructions[current_instruction] = {
                'MOSI': {},
                'MISO': {},
                'command_int': None
            }
            i += 1
            continue
        if line.startswith('Bit'):
            bit_indices = []
            mosi_bits = []
            miso_bits = []
            mosi_values = []
            miso_values = []
            
            for _ in range(2):  # Parse both upper and lower parts
                bit_indices.extend([int(b) for b in lines[i].split()[1:]])
                i += 1
                mosi_line = lines[i].split()[1:]
                i += 1
                mosi_value_line = lines[i].split()[1:]
                i += 1
                miso_line = lines[i].split()[1:]
                i += 1
                miso_value_line = lines[i].split()[1:]
                
                mosi_bits.extend(mosi_line)
                mosi_values.extend(mosi_value_line)
                miso_bits.extend(miso_line)
                miso_values.extend(miso_value_line)
                
                if _ == 0:  # Move to next 'Bit' line
                    i += 1
            
            mosi_zip = list(zip(mosi_bits, mosi_values))
            miso_zip = list(zip(miso_bits, miso_values))
            
            for j, (bit, value) in enumerate(mosi_zip):
                if bit != '---':
                    bit_index = bit_indices[j]
                    instructions[current_instruction]['MOSI'][bit] = [bit_index, bit_index + 1]
            
            for j, (bit, value) in enumerate(miso_zip):
                if bit != '---':
                    bit_index = bit_indices[j]
                    instructions[current_instruction]['MISO'][bit] = [bit_index, bit_index + 1]
            
            # Parse additional fields
            while i < len(lines) and not lines[i].startswith('Bit') and lines[i].strip() != '':
                line = lines[i].strip()
                if ':' in line:
                    field, description = line.split(':', 1)
                    field = field.strip()
                    description = description.strip()
                    
                    # Try to parse the field for both MOSI and MISO
                    mosi_field_name, mosi_field_range = parse_field(field, instructions[current_instruction]['MOSI'], bit_indices, mosi_zip, mosi_zip)
                    miso_field_name, miso_field_range = parse_field(field, instructions[current_instruction]['MISO'], bit_indices, miso_zip, miso_zip)
                    
                    if mosi_field_name and mosi_field_range:
                        instructions[current_instruction]['MOSI'][mosi_field_name] = mosi_field_range
                    elif miso_field_name and miso_field_range:
                        instructions[current_instruction]['MISO'][miso_field_name] = miso_field_range
                    else:
                        print(f"Warning: Could not parse field '{field}' in instruction {current_instruction}")
                i += 1
            
            # Calculate command_int
            if all(f'Adr{j}' in instructions[current_instruction]['MOSI'] for j in range(7, 0, -1)):
                command_bits = ''.join([dict(mosi_zip)[f'Adr{j}'] for j in range(7, 0, -1)])
                instructions[current_instruction]['command_int'] = int(command_bits.replace('1/0', '1'), 2)
            elif all(f'CH{j}' in instructions[current_instruction]['MOSI'] for j in range(4, -1, -1)):
                command_bits = ''.join([dict(mosi_zip)[f'CH{j}'] for j in range(4, -1, -1)])
                instructions[current_instruction]['command_int'] = int(command_bits.replace('1/0', '1'), 2)
        else:
            i += 1
    return merge_fields(instructions)
def main():
    input_file = 'smi7_instructions.txt'
    output_file = 'smi7_instructions.json'
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        instructions = parse_smi7_instructions(content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(instructions, f, indent=2, ensure_ascii=False)
        
        print(f"Processing complete. Results saved to {output_file}.")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found. Please ensure the file is in the correct location.")
    except json.JSONDecodeError:
        print("Error: An error occurred while writing JSON. Please check the generated data structure.")
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()