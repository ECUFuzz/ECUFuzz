import re
import json

def load_common_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def parse_spi_instructions(file_path, common_config):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    instructions = {}
    current_instruction = None
    current_range = None

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('SPI instruction'):
            match = re.match(r'SPI instruction (\w+(?:\d+)?…?\d*)', line)
            if match:
                instruction = match.group(1)
                if '…' in instruction:
                    base_name, range_info = instruction.split('…')
                    if base_name[-1].isdigit():
                        prefix = base_name.rstrip('0123456789')
                        start = int(base_name[len(prefix):])
                    else:
                        prefix = base_name
                        start = 1
                    end = int(range_info)
                    current_range = range(start, end + 1)
                    current_instruction = f"{prefix}{{i}}"
                else:
                    current_instruction = instruction
                    current_range = None

                # Read bit definition line
                i += 1
                bit_line = lines[i] if i < len(lines) else ''

        elif line.startswith('SPI input data') or line.startswith('SPI output data'):
            data_type = "Input Data" if line.startswith('SPI input data') else "Output Data"
            data_line = line

            if current_range:
                for j in current_range:
                    instr = current_instruction.format(i=j)
                    if instr not in instructions:
                        instructions[instr] = {
                            "command_int": common_config['COMMANDS'].get(instr, None),
                            "Additional status bits": common_config['ADDITIONAL_STATUS_BITS'],
                            "General Status": common_config['GENERAL_STATUS'],
                            "Input Data": {},
                            "Output Data": {}
                        }
                    parse_data_line(bit_line, data_line, instructions[instr][data_type])
            else:
                if current_instruction not in instructions:
                    instructions[current_instruction] = {
                        "command_int": common_config['COMMANDS'].get(current_instruction, None),
                        "Additional status bits": common_config['ADDITIONAL_STATUS_BITS'],
                        "General Status": common_config['GENERAL_STATUS'],
                        "Input Data": {},
                        "Output Data": {}
                    }
                parse_data_line(bit_line, data_line, instructions[current_instruction][data_type])

        i += 1

    return instructions

def parse_data_line(bit_line, data_line, data_dict):
    bits = bit_line.split()
    data_parts = data_line.split()[3:]
    
    bit_index = len(bits) - 1  # Start from the highest bit
    for part in data_parts:
        if part == '-' or part == '0':
            bit_index -= 1
            continue
        
        if '[' in part and ']' in part:
            field, bit_count = re.match(r'(\w+)\[(\d+)\]', part).groups()
            bit_count = int(bit_count)
        else:
            field = part
            bit_count = 1
        
        data_dict[field] = [bit_index - bit_count + 1, bit_index + 1]
        bit_index -= bit_count

def main():
    common_config = load_common_config('common.json')
    instructions = parse_spi_instructions('cg9_instructions.txt', common_config)
    with open('cg9_instructions.json', 'w', encoding='utf-8') as f:
        json.dump(instructions, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()