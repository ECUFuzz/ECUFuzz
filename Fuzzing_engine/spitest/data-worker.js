
    self.onmessage = function(e) {
        const plots = e.data;
        
        // Process and send back each plot data
        for (const [plotType, plotData] of Object.entries(plots)) {
            try {
                const processedData = JSON.parse(plotData);
                self.postMessage({plotType, plotData: processedData});
            } catch (error) {
                console.error('Error processing ' + plotType + ':', error);
                self.postMessage({plotType, error: error.message});
            }
        }
    };
    