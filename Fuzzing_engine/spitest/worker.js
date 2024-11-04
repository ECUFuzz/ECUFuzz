
    function generateFrequencyAndIntervalsPlot(data) {
        const freqData = Object.entries(data.instruction_count).sort((a, b) => b[1] - a[1]);
        const intervalData = Object.fromEntries(
            Object.entries(data.avg_intervals).filter(([k, v]) => freqData.some(item => item[0] === k))
        );
        
        const topN = 50;
        const otherFreq = freqData.slice(topN).reduce((sum, item) => sum + item[1], 0);
        const topFreqData = freqData.slice(0, topN).concat([["Other", otherFreq]]);
        
        const traces = [
            {
                x: topFreqData.map(item => item[0]),
                y: topFreqData.map(item => item[1]),
                type: 'bar',
                name: 'Frequency',
                text: topFreqData.map(item => item[1].toLocaleString()),
                textposition: 'auto',
                hoverinfo: 'text',
                hovertext: topFreqData.map(item => `${item[0]}: ${item[1].toLocaleString()}`),
            },
            {
                x: Object.keys(intervalData),
                y: Object.values(intervalData),
                type: 'bar',
                name: 'Avg Interval',
                yaxis: 'y2',
                text: Object.values(intervalData).map(v => v.toFixed(6)),
                textposition: 'auto',
                hoverinfo: 'text',
                hovertext: Object.entries(intervalData).map(([k, v]) => `${k}: ${v.toFixed(6)}`),
            }
        ];
        
        const layout = {
            title: 'Top 50 Instruction Frequency and Average Intervals',
            xaxis: { tickangle: -45 },
            yaxis: { title: 'Frequency' },
            yaxis2: { title: 'Average Interval (s)', overlaying: 'y', side: 'right' },
            barmode: 'group',
            height: 1200,
            showlegend: true,
        };
        
        return { data: traces, layout: layout };
    }

    function generateTransitionProbabilitiesPlot(data) {
        const instructions = Object.keys(data.transition_probabilities).sort();
        const transitionMatrix = instructions.map(instr1 => 
            instructions.map(instr2 => 
                data.transition_probabilities[instr1][instr2] || 0
            )
        );
        
        const trace = {
            z: transitionMatrix,
            x: instructions,
            y: instructions,
            type: 'heatmap',
            colorscale: 'Viridis'
        };
        
        const layout = {
            title: 'Instruction Transition Probabilities',
            xaxis: { tickangle: -90, tickfont: { size: 8 } },
            yaxis: { tickangle: 0, tickfont: { size: 8 } },
            height: 1000,
            margin: { l: 150, r: 50, b: 150, t: 100 },
        };
        
        return { data: [trace], layout: layout };
    }

    function generateTimeSeriesPlot(data) {
        const uniqueInstructions = [...new Set(data.time_series.map(item => item[1]))].sort();
        const traces = uniqueInstructions.map((instr, i) => ({
            x: data.time_series.filter(item => item[1] === instr).map(item => item[0]),
            y: Array(data.time_series.filter(item => item[1] === instr).length).fill(i),
            mode: 'markers',
            name: instr,
            type: 'scatter',
            marker: { size: 5 }
        }));
        
        const layout = {
            title: 'Instruction Time Series',
            xaxis: { title: 'Time' },
            yaxis: {
                title: 'Instruction',
                tickmode: 'array',
                tickvals: Array.from(Array(uniqueInstructions.length).keys()),
                ticktext: uniqueInstructions,
                tickangle: 0
            },
            height: Math.max(600, 20 * uniqueInstructions.length),
        };
        
        return { data: traces, layout: layout };
    }

    self.onmessage = function(e) {
        if (e.data.type === 'processData') {
            const data = e.data.data;
            
            const freqIntervalsPlot = generateFrequencyAndIntervalsPlot(data);
            self.postMessage({
                plotType: 'instruction-frequency-and-intervals',
                plotData: JSON.stringify(freqIntervalsPlot)
            });
            
            const transitionProbPlot = generateTransitionProbabilitiesPlot(data);
            self.postMessage({
                plotType: 'transition-probabilities',
                plotData: JSON.stringify(transitionProbPlot)
            });
            
            const timeSeriesPlot = generateTimeSeriesPlot(data);
            self.postMessage({
                plotType: 'time-series',
                plotData: JSON.stringify(timeSeriesPlot)
            });
        }
    };
    