import csv

def read_csv(file_path):
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        rows = [(row['MOSI'], row['MISO']) for row in csv_reader]
    return rows

def process_data(rows):
    txt_content = []
    i = 0
    n = len(rows)
    
    while i < n:
        current_mosi = [rows[i][0], rows[i+1][0], rows[i+2][0], rows[i+3][0]]
        current_miso = [rows[i][1], rows[i+1][1], rows[i+2][1], rows[i+3][1]]
        
        j = i + 4
        repeat_count = 1
        
        while j < n:
            next_mosi = [rows[j][0], rows[j+1][0], rows[j+2][0], rows[j+3][0]]
            next_miso = [rows[j][1], rows[j+1][1], rows[j+2][1], rows[j+3][1]]
            
            if current_mosi == next_mosi and current_miso == next_miso:
                repeat_count += 1
                j += 4
            else:
                break
        
        if repeat_count > 1:
            txt_content.append(f'{{{", ".join(current_miso)}}, //{repeat_count} Unknown}}')
        else:
            txt_content.append(f'{{{", ".join(current_miso)}}, //1 Unknown}}')
        
        i = j

    return txt_content

def write_txt(file_path, txt_content):
    with open(file_path, mode='w') as file:
        for line in txt_content:
            file.write(line + '\n')

def main():
    input_csv = 'test.csv'  # Input file path
    output_txt = 'output.txt'  # Output file path
    
    rows = read_csv(input_csv)
    txt_content = process_data(rows)
    write_txt(output_txt, txt_content)

if __name__ == "__main__":
    main()
