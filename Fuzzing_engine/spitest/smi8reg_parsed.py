import json
import re

def merge_fields(data):
    for instruction in data.values():
        for direction in ['MOSI', 'MISO']:
            if direction in instruction:
                merged = {}
                to_merge = {
                    'CRC': ['CRC0', 'CRC1', 'CRC2'],
                    'BADR': ['BADR0', 'BADR1', 'BADR2', 'BADR3', 'BADR4'],
                    'ADR': ['ADR0', 'ADR1', 'ADR2', 'ADR3'],
                    'CAP': ['CAP0', 'CAP1', 'CAP2'],
                    'TRI': ['TRI0', 'TRI1', 'TRI2', 'TRI3', 'TRI4'],
                    'SID': ['SID0', 'SID1', 'SID2', 'SID3', 'SID4'],
                    'D': ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'],
                    'MID': ['MID0', 'MID1', 'MID2'],
                    'PG': ['PG0', 'PG1', 'PG2']
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
                i += 1
                
                mosi_bits.extend(mosi_line)
                mosi_values.extend(mosi_value_line)
                miso_bits.extend(miso_line)
                miso_values.extend(miso_value_line)
            
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
            
            # Calculate command_int for BADR fields
            if all(f'BADR{j}' in instructions[current_instruction]['MOSI'] for j in range(4, -1, -1)):
                command_bits = ''.join([dict(mosi_zip)[f'BADR{j}'] for j in range(4, -1, -1)])
                instructions[current_instruction]['command_int'] = int(command_bits.replace('1/0', '1'), 2)
        else:
            i += 1
    return merge_fields(instructions)

def main():
    input_file = 'smi8_instructions.txt'
    output_file = 'smi8_instructions.json'
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