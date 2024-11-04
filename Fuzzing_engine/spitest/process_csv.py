import csv
from collections import Counter

def read_csv(file_path):
    data = []
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            mosi, miso, command = row
            data.append((int(mosi, 16), int(miso, 16), command))
    return data

def process_data(data):
    result = []
    i = 0
    while i < len(data):
        chunk = data[i:i+4]
        if len(chunk) < 4:
            result.append((chunk, 1))
            break
        
        if chunk[0][2] == 'RD_SENSOR_DATA_CH1':
            count = 1
            while i + count * 4 < len(data) and data[i+count*4][2] == 'RD_SENSOR_DATA_CH1':
                count += 1
            result.append((chunk, count))
            i += count * 4
        else:
            next_chunk = data[i+4:i+8]
            if len(next_chunk) == 4 and all(a == b for a, b in zip(chunk, next_chunk)):
                count = 2
                while i + count * 4 < len(data) and all(a == b for a, b in zip(chunk, data[i+count*4:i+count*4+4])):
                    count += 1
                result.append((chunk, count))
                i += count * 4
            else:
                result.append((chunk, 1))
                i += 4
    return result

def format_output(processed_data):
    output = []
    repeat_counts = []
    for chunk, count in processed_data:
        miso_bytes = []
        commands = []
        for _, miso, command in chunk:
            miso_bytes.extend(miso.to_bytes(4, 'big'))
            commands.append(command)
        hex_str = ', '.join(f'0x{b:02X}' for b in miso_bytes)
        command_str = ' '.join(commands)
        output.append(f"{{{hex_str}}}, //{count} {command_str}")
        repeat_counts.append(count)
    
    # Add the repeat counts as the last line
    repeat_counts_str = ', '.join(map(str, repeat_counts))
    print(len(repeat_counts))
    output.append(f"{{{repeat_counts_str}}}")
    
    return output

def write_txt(file_path, data):
    with open(file_path, 'w') as f:
        for line in data:
            f.write(line + '\n')

def main(input_csv, output_txt):
    data = read_csv(input_csv)
    processed_data = process_data(data)
    formatted_output = format_output(processed_data)
    write_txt(output_txt, formatted_output)

if __name__ == "__main__":
    input_csv = "input.csv"  # Replace with your input CSV file path
    output_txt = "output.txt"  # Replace with your desired output TXT file path
    main(input_csv, output_txt)