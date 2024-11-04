import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from typing import List, Dict ,Tuple

def generate_interactive_plots(scheduling_analysis: Dict) -> Dict:
    plots = {}
    
    # Instruction frequency and average intervals plot
    freq_data = sorted(scheduling_analysis['instruction_count'].items(), key=lambda x: x[1], reverse=True)
    interval_data = {k: v for k, v in scheduling_analysis['avg_intervals'].items() if k in dict(freq_data)}
    
    top_n = len(freq_data)
    other_freq = sum(item[1] for item in freq_data[top_n:])
    top_freq_data = freq_data[:top_n] + [("Other", other_freq)]
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=(f'Top {top_n} Instruction Frequency', f'Average Intervals for Top {top_n} Instructions (seconds)'))
    
    fig.add_trace(go.Bar(
        x=[item[0] for item in top_freq_data],
        y=[item[1] for item in top_freq_data],
        name='Frequency',
        text=[f"{item[1]:,}" for item in top_freq_data],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{item[0]}: {item[1]:,}" for item in top_freq_data]
    ), row=1, col=1)
    
    top_interval_data = {k: v for k, v in interval_data.items() if k in dict(top_freq_data)}
    fig.add_trace(go.Bar(
        x=list(top_interval_data.keys()),
        y=list(top_interval_data.values()),
        name='Avg Interval',
        text=[f"{v:.6f}" for v in top_interval_data.values()],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{k}: {v:.6f}" for k, v in top_interval_data.items()]
    ), row=2, col=1)
    
    fig.update_layout(
        height=1200,
        showlegend=False,
        xaxis=dict(tickangle=-45),
        xaxis2=dict(tickangle=-45),
        yaxis=dict(title='Frequency'),
        yaxis2=dict(title='Average Interval (s)'),
        dragmode='pan',
    )
    
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                x=0.57,
                y=1.2,
                buttons=list([
                    dict(label="Linear Scale",
                         method="update",
                         args=[{"visible": [True, True]},
                               {"yaxis": {"type": "linear", "title": "Frequency"}}]),
                    dict(label="Log Scale",
                         method="update",
                         args=[{"visible": [True, True]},
                               {"yaxis": {"type": "log", "title": "Log10(Frequency)"}}]),
                ]),
            )
        ]
    )
    
    plots['instruction_frequency_and_intervals'] = json.dumps(fig.to_dict())

    # Transition probabilities heatmap
    transition_matrix = []
    instructions = sorted(scheduling_analysis['transition_probabilities'].keys())
    for instr1 in instructions:
        row = []
        for instr2 in instructions:
            row.append(scheduling_analysis['transition_probabilities'][instr1].get(instr2, 0))
        transition_matrix.append(row)
    
    heatmap = go.Heatmap(
        z=transition_matrix,
        x=instructions,
        y=instructions,
        colorscale='Viridis'
    )
    heatmap_layout = go.Layout(
        title='Instruction Transition Probabilities',
        xaxis=dict(tickangle=-90, tickfont=dict(size=8)),
        yaxis=dict(tickangle=0, tickfont=dict(size=8)),
        height=1000,
        margin=dict(l=150, r=50, b=150, t=100),
        dragmode='pan',
    )
    heatmap_fig = go.Figure(data=[heatmap], layout=heatmap_layout)
    plots['transition_probabilities'] = json.dumps(heatmap_fig.to_dict())

    # Time series plot
    time_series_data = scheduling_analysis['time_series']
    unique_instructions = sorted(set(item[1] for item in time_series_data))
    traces = []
    for i, instr in enumerate(unique_instructions):
        instr_data = [(time, inst) for time, inst in time_series_data if inst == instr]
        trace = go.Scatter(
            x=[item[0] for item in instr_data],
            y=[i] * len(instr_data),
            mode='markers',
            name=instr,
            marker=dict(size=5)
        )
        traces.append(trace)
    
    time_series_layout = go.Layout(
        title='Instruction Time Series',
        xaxis_title='Time (ms)',
        yaxis=dict(
            title='Instruction',
            tickmode='array',
            tickvals=list(range(len(unique_instructions))),
            ticktext=unique_instructions,
            tickangle=0
        ),
        margin=dict(l=250),
        height=max(600, 20 * len(unique_instructions)),
        dragmode='pan',
    )
    time_series_fig = go.Figure(data=traces, layout=time_series_layout)
    plots['time_series'] = json.dumps(time_series_fig.to_dict())

    return plots

def generate_html(plots: Dict, output_file: str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instruction Timing Analysis</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.0/papaparse.min.js"></script>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                user-select: text;
                -webkit-user-select: text;
                -moz-user-select: text;
                -ms-user-select: text;
            }}
            .plot-container {{         width: 100%;
        margin-bottom: 20px;
        position: relative;
        user-select: text; /* Ensure all text is selectable */
        -webkit-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text; }}
            #instruction-frequency-and-intervals {{ height: 1200px; }}
            #transition-probabilities {{ height: 1000px; }}
            #time-series {{ height: 800px; }}
            .data-table {{ display: none; width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .data-table th {{ background-color: #f2f2f2; }}
            .toggle-view {{ margin-bottom: 10px; }}
            .annotation-form {{ margin-top: 10px; }}
            .annotation-form input, .annotation-form button {{ margin-right: 5px; }}
        </style>
    </head>
    <body>
        <h1>Instruction Timing Analysis</h1>
        <div id="instruction-frequency-and-intervals" class="plot-container">
            <button class="toggle-view">Toggle Table View</button>
            <div class="plot"></div>
            <table class="data-table"></table>
            <div class="annotation-form">
                <input type="text" placeholder="X-axis value">
                <input type="text" placeholder="Y-axis value">
                <input type="text" placeholder="Annotation text">
                <button onclick="addAnnotation('instruction-frequency-and-intervals')">Add Annotation</button>
            </div>
        </div>
        <div id="transition-probabilities" class="plot-container">
            <button class="toggle-view">Toggle Table View</button>
            <div class="plot"></div>
            <table class="data-table"></table>
            <div class="annotation-form">
                <input type="text" placeholder="X-axis value">
                <input type="text" placeholder="Y-axis value">
                <input type="text" placeholder="Annotation text">
                <button onclick="addAnnotation('transition-probabilities')">Add Annotation</button>
            </div>
        </div>
        <div id="time-series" class="plot-container">
            <button class="toggle-view">Toggle Table View</button>
            <div class="plot"></div>
            <table class="data-table"></table>
            <div class="annotation-form">
                <input type="text" placeholder="X-axis value">
                <input type="text" placeholder="Y-axis value">
                <input type="text" placeholder="Annotation text">
                <button onclick="addAnnotation('time-series')">Add Annotation</button>
            </div>
        </div>

        <script>
        const plotData = {plots};

        function createWorker(workerFunction) {{
            const blob = new Blob(['(' + workerFunction.toString() + ')()'], {{ type: 'application/javascript' }});
            return new Worker(URL.createObjectURL(blob));
        }}

        const worker = createWorker(function() {{
            self.onmessage = function(e) {{
                const plotData = e.data;
                const processedData = {{
                    'instruction-frequency-and-intervals': JSON.parse(plotData['instruction_frequency_and_intervals']),
                    'transition-probabilities': JSON.parse(plotData['transition_probabilities']),
                    'time-series': JSON.parse(plotData['time_series'])
                }};
                self.postMessage(processedData);
            }};
        }});

        function createPlotWithWebGL(plotId, plotData, layout) {{
            const config = {{
                scrollZoom: true,
                displayModeBar: true,
                responsive: true,
                toImageButtonOptions: {{
                    format: 'svg',
                    filename: plotId,
                    height: 1000,
                    width: 1500,
                    scale: 1
                }}
            }};

            if (plotData.some(trace => trace.type === 'scatter' || trace.type === 'scattergl')) {{
                config.renderer = 'webgl';
                plotData = plotData.map(trace => {{
                    if (trace.type === 'scatter') {{
                        return {{...trace, type: 'scattergl'}};
                    }}
                    return trace;
                }});
            }}

            Plotly.newPlot(plotId, plotData, layout, config);

            const plot = document.getElementById(plotId);
            plot.on('plotly_click', function(data) {{
                if (data.points.length > 0) {{
                    const point = data.points[0];
                    alert(`Clicked point:\\nX: ${{point.x}}\\nY: ${{point.y}}`);
                }}
            }});
        }}

        function monitorPerformance(plotId) {{
            const plot = document.getElementById(plotId);
            plot.on('plotly_afterplot', function() {{
                console.log(`Render time for ${{plotId}}: ${{performance.now() - window.renderStartTime}}ms`);
            }});
        }}

        function toggleTableView(plotId) {{
            const container = document.getElementById(plotId);
            const plot = container.querySelector('.plot');
            const table = container.querySelector('.data-table');
            
            if (plot.style.display === 'none') {{
                plot.style.display = 'block';
                table.style.display = 'none';
            }} else {{
                plot.style.display = 'none';
                table.style.display = 'block';
                if (table.rows.length === 0) {{
                    populateTable(plotId);
                }}
            }}
        }}

        function populateTable(plotId) {{
            const container = document.getElementById(plotId);
            const table = container.querySelector('.data-table');
            const plotData = Plotly.getData(plotId);
            
            // Clear existing table content
            table.innerHTML = '';
            
            // Create table header
            const header = table.createTHead();
            const headerRow = header.insertRow();
            headerRow.insertCell().textContent = 'X';
            headerRow.insertCell().textContent = 'Y';
            
            // Create table body
            const body = table.createTBody();
            plotData.forEach(trace => {{
                trace.x.forEach((x, i) => {{
                    const row = body.insertRow();
                    row.insertCell().textContent = x;
                    row.insertCell().textContent = trace.y[i];
                }});
            }});
        }}

        function addAnnotation(plotId) {{
            const container = document.getElementById(plotId);
            const inputs = container.querySelectorAll('.annotation-form input');
            const x = inputs[0].value;
            const y = inputs[1].value;
            const text = inputs[2].value;
            
            if (x && y && text) {{
                Plotly.relayout(plotId, {{
                    annotations: [
                        {{
                            x: x,
                            y: y,
                            xref: 'x',
                            yref: 'y',
                            text: text,
                            showarrow: true,
                            arrowhead: 7,
                            ax: 0,
                            ay: -40
                        }}
                    ]
                }});
                
                // Clear input fields after adding annotation
                inputs.forEach(input => input.value = '');
            }}
        }}

        worker.onmessage = function(e) {{
            const processedData = e.data;
            window.renderStartTime = performance.now();
            Object.keys(processedData).forEach(plotId => {{
                const plotData = processedData[plotId];
                createPlotWithWebGL(plotId, plotData.data, plotData.layout);
                monitorPerformance(plotId);
                
                // Add event listener for toggle button
                const container = document.getElementById(plotId);
                const toggleButton = container.querySelector('.toggle-view');
                toggleButton.addEventListener('click', () => toggleTableView(plotId));
            }});
        }};

        worker.postMessage(plotData);
        </script>
    </body>
    </html>
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def write_scheduling_analysis(analysis: Dict, output_file: str):
    with open(output_file, 'w') as f:
        f.write("Instruction Scheduling Analysis\n")
        f.write("===============================\n\n")

        # Overall Statistics
        f.write("1. Overall Statistics\n")
        f.write("---------------------\n")
        f.write(f"Total Instructions: {analysis['total_instructions']}\n")
        f.write(f"Unique Instructions: {analysis['unique_instructions']}\n")
        f.write("\n")

        # Instruction Count
        f.write("2. Instruction Frequency\n")
        f.write("------------------------\n")
        for instr, count in analysis['instruction_count'].items():
            f.write(f"{instr}: {count}\n")
        f.write("\n")

        # Instruction Distribution
        f.write("3. Instruction Distribution\n")
        f.write("---------------------------\n")
        for instr, percentage in analysis['instruction_distribution'].items():
            f.write(f"{instr}: {percentage:.2%}\n")
        f.write("\n")

        # Average Intervals
        f.write("4. Average Intervals Between Instructions (seconds)\n")
        f.write("--------------------------------------------------\n")
        for instr, avg in analysis['avg_intervals'].items():
            f.write(f"{instr}: {avg:.6f}\n")
        f.write("\n")

        # Common Bigrams
        f.write("5. Common Instruction Bigrams\n")
        f.write("------------------------------\n")
        for seq, count in analysis['common_bigrams']:
            f.write(f"{' -> '.join(seq)}: {count}\n")
        f.write("\n")

        # Common Trigrams
        f.write("6. Common Instruction Trigrams\n")
        f.write("-------------------------------\n")
        for seq, count in analysis['common_trigrams']:
            f.write(f"{' -> '.join(seq)}: {count}\n")
        f.write("\n")

        # Transition Probabilities
        f.write("7. Instruction Transition Probabilities\n")
        f.write("---------------------------------------\n")
        for current_instr, next_instrs in analysis['transition_probabilities'].items():
            f.write(f"From {current_instr}:\n")
            for next_instr, prob in next_instrs.items():
                f.write(f"  To {next_instr}: {prob:.2f}\n")
        f.write("\n")

        # Periodic Patterns
        f.write("8. Periodic Patterns\n")
        f.write("--------------------\n")
        for pattern in analysis['periodic_patterns']:
            f.write(f"Pattern: {' -> '.join(pattern['pattern'])}\n")
            f.write(f"  Length: {pattern['length']}\n")
            f.write(f"  Count: {pattern['count']}\n")
            f.write(f"  Coverage: {pattern['coverage']:.2f}\n")
            f.write("\n")

    print(f"Scheduling analysis written to {output_file}")

def analyze_instruction_scheduling(parsed_data: List[Dict]) -> Dict:
    instruction_count = defaultdict(int)
    instruction_intervals = defaultdict(list)
    last_instruction_time = {}
    instruction_sequence = []
    time_series = []
    total_instructions = 0

    for frame in parsed_data:
        instruction = frame['instruction']
        current_time = frame['time'] * 1000
        
        # Count instructions
        instruction_count[instruction] += 1
        total_instructions += 1
        
        # Build instruction sequence
        instruction_sequence.append(instruction)
        
        # Calculate intervals
        if instruction in last_instruction_time:
            interval = current_time - last_instruction_time[instruction]
            instruction_intervals[instruction].append(interval)
        
        last_instruction_time[instruction] = current_time

        # Build time series
        time_series.append((current_time, instruction))

    # Calculate average intervals
    avg_intervals = {instr: sum(intervals) / len(intervals) 
                     for instr, intervals in instruction_intervals.items()}

    # Identify common instruction sequences (bigrams and trigrams)
    bigram_counts = defaultdict(int)
    trigram_counts = defaultdict(int)
    for i in range(len(instruction_sequence) - 2):
        bigram = tuple(instruction_sequence[i:i+2])
        trigram = tuple(instruction_sequence[i:i+3])
        bigram_counts[bigram] += 1
        trigram_counts[trigram] += 1

    common_bigrams = sorted(bigram_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    common_trigrams = sorted(trigram_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Calculate instruction transition probabilities
    transitions = defaultdict(lambda: defaultdict(int))
    for i in range(len(instruction_sequence) - 1):
        current_instr = instruction_sequence[i]
        next_instr = instruction_sequence[i+1]
        transitions[current_instr][next_instr] += 1

    transition_probs = {}
    for current_instr, next_instrs in transitions.items():
        total = sum(next_instrs.values())
        transition_probs[current_instr] = {next_instr: count/total for next_instr, count in next_instrs.items()}

    # Identify periodic patterns
    periodic_patterns = identify_periodic_patterns(instruction_sequence)

    # Calculate overall statistics
    unique_instructions = len(instruction_count)
    instruction_distribution = {instr: count / total_instructions for instr, count in instruction_count.items()}

    return {
        'total_instructions': total_instructions,
        'unique_instructions': unique_instructions,
        'instruction_count': dict(instruction_count),
        'instruction_distribution': instruction_distribution,
        'avg_intervals': avg_intervals,
        'common_bigrams': common_bigrams,
        'common_trigrams': common_trigrams,
        'transition_probabilities': transition_probs,
        'periodic_patterns': periodic_patterns,
        'time_series': time_series
    }

def identify_periodic_patterns(sequence: List[str], max_length: int = 10) -> List[Dict]:
    patterns = []
    sequence_length = len(sequence)

    for pattern_length in range(2, max_length + 1):
        pattern_counts = defaultdict(int)
        
        for i in range(sequence_length - pattern_length + 1):
            pattern = tuple(sequence[i:i+pattern_length])
            pattern_counts[pattern] += 1
        
        # Consider patterns that appear more than once and cover a significant portion of the sequence
        significant_patterns = [
            pattern for pattern, count in pattern_counts.items()
            if count > 1 and (count * len(pattern) / sequence_length) > 0.01
        ]
        
        for pattern in significant_patterns:
            patterns.append({
                'pattern': pattern,
                'length': len(pattern),
                'count': pattern_counts[pattern],
                'coverage': pattern_counts[pattern] * len(pattern) / sequence_length
            })

    # Sort patterns by coverage (descending)
    return sorted(patterns, key=lambda x: x['coverage'], reverse=True)

def load_json_config(file_path: str) -> Dict:
    with open(file_path, 'r') as f:
        return json.load(f)

def parse_hex(hex_str: str) -> int:
    return int(hex_str, 16)

def extract_bits(value: int, start: int, end: int) -> int:
    mask = (1 << (end - start + 1)) - 1
    return (value >> start) & mask

def calculate_time_delta(current_time: float, previous_time: float) -> float:
    return (current_time - previous_time) * 1000  # Convert to milliseconds

def calculate_inter_packet_time(current_time: float, previous_time: float) -> float:
    return (current_time - previous_time) * 1e6  # Convert to microseconds

def process_sensor_data(data: List[Tuple[int, int, str]], sensor_type: str) -> List[Tuple[List[Tuple[int, int, str]], int]]:
    result = []
    i = 0
    while i < len(data):
        if sensor_type == 'SMA760':
            chunk_size = 4
            is_same_chunk = lambda x, y: all(a == b for a, b in zip(x, y))
        elif sensor_type == 'SMI860':
            chunk_size = 7
            is_same_chunk = lambda x, y: all(a[0] == b[0] and a[2] == b[2] for a, b in zip(x, y))
        else:
            raise ValueError(f"Unknown sensor type: {sensor_type}")

        chunk = data[i:i+chunk_size]
        if len(chunk) < chunk_size:
            result.append((chunk, 1))
            break

        if sensor_type == 'SMA760' and chunk[0][2] == 'RD_SENSOR_DATA_CH1':
            count = 1
            while i + count * chunk_size < len(data) and data[i+count*chunk_size][2] == 'RD_SENSOR_DATA_CH1':
                count += 1
            result.append((chunk, count))
            i += count * chunk_size
        else:
            next_chunk = data[i+chunk_size:i+2*chunk_size]
            if len(next_chunk) == chunk_size and is_same_chunk(chunk, next_chunk):
                count = 2
                while i + count * chunk_size < len(data) and is_same_chunk(chunk, data[i+count*chunk_size:i+(count+1)*chunk_size]):
                    count += 1
                result.append((chunk, count))
                i += count * chunk_size
            else:
                result.append((chunk, 1))
                i += chunk_size

    return result

def format_sensor_output(processed_data: List[Tuple[List[Tuple[int, int, str]], int]], sensor_type: str) -> List[str]:
    output = []
    repeat_counts = []

    for chunk, count in processed_data:
        if sensor_type == 'SMA760':
            miso_bytes = [b for _, miso, _ in chunk for b in miso.to_bytes(4, 'big')]
        elif sensor_type == 'SMI860':
            miso_bytes = [b for _, miso, _ in chunk for b in miso.to_bytes(4, 'big')]
        else:
            raise ValueError(f"Unknown sensor type: {sensor_type}")

        hex_str = ', '.join(f'0x{b:02X}' for b in miso_bytes)
        command_str = ' '.join(command for _, _, command in chunk)
        output.append(f"{{{hex_str}}}, //{count} {command_str}")
        repeat_counts.append(count)

    repeat_counts_str = ', '.join(map(str, repeat_counts))
    output.append(f"{{{repeat_counts_str}}}")
    print(len(repeat_counts))

    # Convert repeat counts to hexadecimal
    # repeat_counts_hex = ', '.join(f'0x{count:02X}' for count in repeat_counts)
    # output.append(f"{{{repeat_counts_hex}}}")
    # print(len(repeat_counts))    

    return output

def write_sensor_output(file_path: str, data: List[str]):
    with open(file_path, 'w') as f:
        for line in data:
            f.write(line + '\n')

def process_and_write_sensor_data(parsed_data: List[Tuple[int, int, str]], sensor_type: str):
    processed_data = process_sensor_data(parsed_data, sensor_type)
    formatted_output = format_sensor_output(processed_data, sensor_type)
    write_sensor_output(f"output{sensor_type.lower()}_txt", formatted_output)

def parse_spi_frame(mosi: str, miso: str, config: Dict) -> Dict:
    mosi_int = parse_hex(mosi)
    miso_int = parse_hex(miso)
    instruction = extract_bits(mosi_int, 22, 31)
    
    result = {
        'instruction': 'Unknown',
        'pe': extract_bits(mosi_int, 21, 21),
        'input_data': {},
        'output_data': {},
        'additional_status': {},
        'general_status': {},
        'crc_in': extract_bits(mosi_int, 2, 4),
        'crc_out': extract_bits(miso_int, 0, 2),
        'sensor_data_flag': extract_bits(miso_int, 26, 26),
        'global_status_flag': extract_bits(miso_int, 3, 3),
        'raw_mosi': mosi,
        'raw_miso': miso
    }
    
    for cmd, cmd_config in config.items():
        if cmd_config['command_int'] == instruction:
            result['instruction'] = cmd
            
            if 'Input Data' in cmd_config:
                input_data = extract_bits(mosi_int, 5, 20)
                for field, (start, end) in cmd_config['Input Data'].items():
                    result['input_data'][field] = extract_bits(input_data, start, end - 1)
            
            if 'Output Data' in cmd_config:
                output_data = extract_bits(miso_int, 4, 19)
                for field, (start, end) in cmd_config['Output Data'].items():
                    result['output_data'][field] = extract_bits(output_data, start, end - 1)
            
            for field, (start, end) in cmd_config['Additional status bits'].items():
                result['additional_status'][field] = extract_bits(miso_int, start, end - 1)
            
            for field, (start, end) in cmd_config['General Status'].items():
                result['general_status'][field] = extract_bits(miso_int, start, end - 1)
            
            break
    
    return result

def parse_sma760_frame(mosi: str, miso: str, config: Dict) -> Dict:
    mosi_int = parse_hex(mosi)
    miso_int = parse_hex(miso)
    
    result = {
        'instruction': 'Unknown',
        'general_status': {},
        'global_status_flag': {},
        'sensor_data_flag': {},
        'additional_status': {},
        'input_data': {},
        'output_data': {},
        'raw_mosi': mosi,
        'raw_miso': miso
    }
    
    # Check if SEN bit is 1
    sen_bit = extract_bits(mosi_int, 31, 31)
    
    if sen_bit == 1:
        # This is a data frame, use 'CH' to parse instruction
        for cmd, cmd_config in config.items():
            if 'MOSI' in cmd_config and 'CH' in cmd_config['MOSI']:
                ch_start, ch_end = cmd_config['MOSI']['CH']
                instruction = extract_bits(mosi_int, ch_start, ch_end - 1)
                if cmd_config['command_int'] == instruction:
                    result['instruction'] = cmd
                    break
    else:
        # This is a command frame, use 'Adr' to parse instruction
        for cmd, cmd_config in config.items():
            if 'MOSI' in cmd_config and 'Adr' in cmd_config['MOSI']:
                adr_start, adr_end = cmd_config['MOSI']['Adr']
                instruction = extract_bits(mosi_int, adr_start, adr_end - 1)
                if cmd_config['command_int'] == instruction:
                    result['instruction'] = cmd
                    break
    
    # Parse the rest of the data
    if result['instruction'] != 'Unknown':
        cmd_config = config[result['instruction']]
        
        if 'MOSI' in cmd_config:
            for field, (start, end) in cmd_config['MOSI'].items():
                if field not in ['CH', 'Adr']:  # Skip these as they've been used for instruction
                    result['input_data'][field] = extract_bits(mosi_int, start, end - 1)
        
        if 'MISO' in cmd_config:
            for field, (start, end) in cmd_config['MISO'].items():
                if field == "GS":
                    result['global_status_flag'] = extract_bits(miso_int, start, end - 1)
                elif field == "SEN":
                    result['sensor_data_flag'] = extract_bits(miso_int, start, end - 1)
                elif field == "SID":
                    result['additional_status'] = extract_bits(miso_int, start, end - 1)     
                elif field in  ["TFF","TST","EOP","0(not_used)","TF","PF"]:
                    result['general_status'][field] = extract_bits(miso_int, start, end - 1)  
                else:                                     
                    result['output_data'][field] = extract_bits(miso_int, start, end - 1)
    
    return result

def parse_smi860_frame(mosi: str, miso: str, config: Dict) -> Dict:
    mosi_int = parse_hex(mosi)
    miso_int = parse_hex(miso)
    
    result = {
        'instruction': 'Unknown',
        'input_data': {},
        'output_data': {},
        'additional_status': {},
        'sensor_data_flag': {},
        'raw_mosi': mosi,
        'raw_miso': miso
    }

    # Parse instruction
    for cmd, cmd_config in config.items():
        if 'MOSI' in cmd_config and 'BADR' in cmd_config['MOSI']:
            badr_start, badr_end = cmd_config['MOSI']['BADR']
            instruction = extract_bits(mosi_int, badr_start, badr_end - 1)
            if cmd_config['command_int'] == instruction:
                result['instruction'] = cmd
                break
    
    # Parse the rest of the data
    if result['instruction'] != 'Unknown':
        cmd_config = config[result['instruction']]
        
        if 'MOSI' in cmd_config:
            for field, (start, end) in cmd_config['MOSI'].items():
                result['input_data'][field] = extract_bits(mosi_int, start, end - 1)
        
        if 'MISO' in cmd_config:
            for field, (start, end) in cmd_config['MISO'].items():
                if field == "SD":
                    result['sensor_data_flag'] = extract_bits(miso_int, start, end - 1)
                elif field == "SID":
                    result['additional_status'] = extract_bits(miso_int, start, end - 1)     
                else:                                     
                    result['output_data'][field] = extract_bits(miso_int, start, end - 1)                
    
    return result

def parse_csv_log(csv_file: str, config: Dict, file_type: str) -> List[Dict]:
    parsed_data = []
    previous_time = 0
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip the header
        for row in reader:
            try:
                time, packet_id, mosi, miso = row
                current_time = float(time)
                if file_type in ['Master', 'Slave', 'CSMon']:
                    parsed_frame = parse_spi_frame(mosi, miso, config)
                elif file_type == 'SMA760':
                    parsed_frame = parse_sma760_frame(mosi, miso, config)
                elif file_type == 'SMI860':
                    parsed_frame = parse_smi860_frame(mosi, miso, config)
                else:
                    parsed_frame = {
                        'raw_mosi': mosi,
                        'raw_miso': miso
                    }
                parsed_frame['time'] = current_time
                parsed_frame['packet_id'] = int(packet_id)
                parsed_frame['time_delta'] = calculate_time_delta(current_time, previous_time) if previous_time else 0
                parsed_frame['inter_packet_time'] = calculate_inter_packet_time(current_time, previous_time) if previous_time else 0
                parsed_frame['file_source'] = file_type
                parsed_data.append(parsed_frame)
                previous_time = current_time
            except ValueError as e:
                print(f"Error parsing row in {file_type}: {row}. Error: {e}")         

    return parsed_data

def merge_parsed_data(parsed_data_list: List[List[Dict]]) -> List[Dict]:
    merged_data = [item for sublist in parsed_data_list for item in sublist]
    return sorted(merged_data, key=lambda x: x['time'])

def write_csv_output(parsed_data: List[Dict], output_file: str):
    fieldnames = [
        'Time [ms]', 'Time Delta [ms]', 'File Source',
        'MOSI', 'MISO', 'Command Name', 'PE', 'Input Data Details',
        'General Status', 'Sensor Data Flag', 'SID / add. Status',
        'Output Data Details', 'Global Status Flag',
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for frame in parsed_data:
            row = {
                'Time [ms]': frame['time'] * 1000,
                'Time Delta [ms]': frame['time_delta'],
                'File Source': frame['file_source'],
                'MOSI': frame['raw_mosi'],
                'MISO': frame['raw_miso'],
                'Command Name': frame.get('instruction', ''),
                'PE': frame.get('pe', ''),
                'Input Data Details': json.dumps(frame.get('input_data', {})),
                'General Status': json.dumps(frame.get('general_status', {})),
                'Sensor Data Flag': frame.get('sensor_data_flag', ''),
                'SID / add. Status': json.dumps(frame.get('additional_status', {})),
                'Output Data Details': json.dumps(frame.get('output_data', {})),
                'Global Status Flag': frame.get('global_status_flag', ''),
            }
            writer.writerow(row)

def main():
    if len(sys.argv) != 5:
        print("Usage: python spi_parser.py <Master_csv> <Slave_csv> <SMA760_csv> <SMI860_csv>")
        print("Use 'n' as a placeholder if a file is not needed.")
        sys.exit(1)

    cg9_config = load_json_config('cg9_instructions.json')
    sma760_config = load_json_config('smi7_instructions.json')
    smi860_config = load_json_config('smi8_instructions.json')
    
    file_types = {
        'Master': sys.argv[1],
        'Slave': sys.argv[2],
        'SMA760': sys.argv[3],
        'SMI860': sys.argv[4]
    }
    
    parsed_data_list = []
    for file_type, file_name in file_types.items():
        if file_name.lower() != 'n':
            if file_type in ['Master', 'Slave']:
                config = cg9_config
            elif file_type == 'SMA760':
                config = sma760_config
            elif file_type == 'SMI860':
                config = smi860_config
            parsed_data = parse_csv_log(file_name, config, file_type)
            parsed_data_list.append(parsed_data)
            
            parsed_sma760 = None
            parsed_smi860 = None
            if file_type == 'SMA760' and file_name != 'n':
                parsed_sma760 = [(int(frame['raw_mosi'], 16), int(frame['raw_miso'], 16), frame['instruction']) for frame in parsed_data]
            elif file_type == 'SMI860' and file_name != 'n':
                parsed_smi860 = [(int(frame['raw_mosi'], 16), int(frame['raw_miso'], 16), frame['instruction']) for frame in parsed_data]    

    if parsed_sma760 != None:
        process_and_write_sensor_data(parsed_sma760, 'SMA760')
    if parsed_smi860 != None:
        process_and_write_sensor_data(parsed_smi860, 'SMI860')

    merged_data = merge_parsed_data(parsed_data_list)
    scheduling_analysis = analyze_instruction_scheduling(merged_data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'combined_output_{timestamp}.csv'
    analysis_file = f'scheduling_analysis_{timestamp}.txt'
    html_file = f'analysis_report_{timestamp}.html'
    
    write_csv_output(merged_data, output_file)
    write_scheduling_analysis(scheduling_analysis, analysis_file)
    
    plots = generate_interactive_plots(scheduling_analysis)
    generate_html(plots, html_file)
    
    print(f"Parsing complete. Merged results written to {output_file}")
    print(f"Scheduling analysis results have been written to {analysis_file}")
    print(f"Interactive analysis report has been generated: {html_file}")
    print(f"Please open {html_file} in your browser to view the interactive charts.")

if __name__ == "__main__":
    main()