
    self.onmessage = function(e) {
      const data = e.data;
      
      // Process instruction frequency and intervals data
      const freqData = processFrequencyData(data.instruction_count);
      const intervalData = processIntervalData(data.avg_intervals, freqData);
      
      // Process transition probability data
      const transitionData = processTransitionData(data.transition_probabilities);
      
      // Process time series data
      const timeSeriesData = processTimeSeriesData(data.time_series);
      
      self.postMessage({
        freqData: freqData,
        intervalData: intervalData,
        transitionData: transitionData,
        timeSeriesData: timeSeriesData
      });
    };

    function processFrequencyData(instructionCount) {
      return Object.entries(instructionCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50);
    }

    function processIntervalData(avgIntervals, freqData) {
      return freqData.reduce((acc, [instruction]) => {
        if (instruction in avgIntervals) {
          acc[instruction] = avgIntervals[instruction];
        }
        return acc;
      }, {});
    }

    function processTransitionData(transitionProbabilities) {
      const instructions = Object.keys(transitionProbabilities).sort();
      return instructions.map(instr1 => 
        instructions.map(instr2 => 
          transitionProbabilities[instr1][instr2] || 0
        )
      );
    }

    function processTimeSeriesData(timeSeries) {
      const uniqueInstructions = [...new Set(timeSeries.map(item => item[1]))].sort();
      return uniqueInstructions.map((instr, i) => ({
        x: timeSeries.filter(item => item[1] === instr).map(item => item[0]),
        y: Array(timeSeries.filter(item => item[1] === instr).length).fill(i),
        mode: 'markers',
        name: instr,
        marker: {size: 5}
      }));
    }
    