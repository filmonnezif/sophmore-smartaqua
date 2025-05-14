// dashboard.js - Hydroponics monitoring dashboard logic

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all visualizations
    initWaterLevelChart();
    initPHBar();
    initPlantHealthMonitor();
    
    // Fetch initial data
    fetchCurrentData();
    fetchHistoricalData(24); // Default to 24 hours

    // Set up refresh interval (every 30 seconds)
    setInterval(fetchCurrentData, 30000);
    initWebcam();  
    console.log("Webcam initialized");
    
    // Set up time control buttons
    document.querySelectorAll('.time-button').forEach(button => {
        button.addEventListener('click', function() {
            document.querySelectorAll('.time-button').forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            fetchHistoricalData(parseInt(this.dataset.hours));
        });
    });

    const now = new Date();
    const yesterday = new Date(now.getTime() - (24 * 60 * 60 * 1000));
    
    document.getElementById('end-date').value = now.toISOString().slice(0, 16);
    document.getElementById('start-date').value = yesterday.toISOString().slice(0, 16);
    
    // Set up custom range button
    document.getElementById('apply-custom-range').addEventListener('click', function() {
        document.querySelectorAll('.time-button').forEach(btn => btn.classList.remove('active'));
        fetchCustomRangeData();
    });
});

function initWebcam() {
    const container = document.querySelector('.video-container');
    container.innerHTML = ''; 
  
    // Create a <video> element for the client webcam
    const video = document.createElement('video');
    video.id = 'client-webcam';
    video.autoplay = true;
    video.playsInline = true;
    video.style.width = '100%';
    video.style.height = 'auto';
    container.appendChild(video);
  
    // Request camera access
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
          video.srcObject = stream;
        })
        .catch(err => {
          console.error('Error accessing webcam:', err);
          handleVideoError(container, 'Unable to access webcam');
        });
    } else {
      console.error('getUserMedia not supported');
    }
  }
  

// Helper function to display video errors
// function handleVideoError(container, message) {
//     console.error("Video error:", message);
//     container.innerHTML = `
//         <div class="video-error">
//             <i class="fas fa-exclamation-triangle"></i>
//             <p>${message}</p>
//             <small>Please check server camera connection</small>
//         </div>
//     `;
// }

async function fetchCustomRangeData() {
    const startDate = new Date(document.getElementById('start-date').value);
    const endDate = new Date(document.getElementById('end-date').value);
    
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
        alert('Please enter valid dates');
        return;
    }
    
    if (startDate >= endDate) {
        alert('Start date must be before end date');
        return;
    }
    
    try {
        const response = await fetch(`/api/sensors/custom-range?start=${startDate.toISOString()}&end=${endDate.toISOString()}`);
        const data = await response.json();
        
        if (data.length === 0) {
            alert('No data available for the selected time range');
            return;
        }
        
        // Process data for Chart.js (same code as in fetchHistoricalData)
        const timestamps = data.map(item => new Date(item.timestamp).toLocaleString());
        const datasets = [
            // Same datasets as in fetchHistoricalData
            {
                label: 'Temperature (°C)',
                data: data.map(item => item.temperature),
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-temperature'
            },
            // Include other datasets...
            {
                label: 'Humidity (%)',
                data: data.map(item => item.humidity),
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-humidity'
            },
            {
                label: 'pH Level',
                data: data.map(item => item.ph_level),
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-ph'
            },
            {
                label: 'Water Level (%)',
                data: data.map(item => item.water_level),
                borderColor: 'rgba(153, 102, 255, 1)',
                backgroundColor: 'rgba(153, 102, 255, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-water'
            }
        ];
        
        // Update the chart
        updateHistoryChart(timestamps, datasets);
        
    } catch (error) {
        console.error('Error fetching custom range data:', error);
        alert('Error fetching data: ' + error.message);
    }
}
function initPlantHealthMonitor() {
    // Add styles for the health bar
    const style = document.createElement('style');
    style.textContent = `
        .plant-health-container {
            margin-top: 15px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }
        .plant-health-container h3 {
            margin-bottom: 10px;
            font-size: 1.1rem;
            color: #2c3e50;
        }
        .health-bar-container {
            position: relative;
            width: 100%;
            height: 25px;
            margin-bottom: 10px;
        }
        .health-bar-background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #e9ecef;
            border-radius: 5px;
            overflow: hidden;
        }
        .health-bar-fill {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background: linear-gradient(to right, #28a745, #20c997);
            border-radius: 5px;
            transition: width 0.5s ease;
            width: 0%;
        }
        .health-percentage {
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
            margin: 10px 0;
        }
        .health-status {
            text-align: center;
            padding: 5px 10px;
            border-radius: 15px;
            background-color: #d4edda;
            color: #155724;
            display: inline-block;
            margin: 0 auto;
            font-weight: 500;
        }
    `;
    document.head.appendChild(style);
    
    // Start monitoring plant health
    updatePlantHealth();
    // Update health status every 30 seconds
    setInterval(updatePlantHealth, 30000);
}

// Function to update plant health status with random values
function updatePlantHealth() {
    // Generate random health percentage between 85 and 97
    const healthPercentage = Math.floor(Math.random() * (97 - 85 + 1)) + 85;
    
    // Update the health bar
    const healthBar = document.getElementById('health-bar');
    healthBar.style.width = `${healthPercentage}%`;
    
    // Update the percentage text
    document.getElementById('health-percentage').textContent = `${healthPercentage}%`;
    
    // Update health status text based on percentage
    const healthStatus = document.getElementById('health-status');
    if (healthPercentage >= 95) {
        healthStatus.textContent = 'Excellent';
        healthStatus.style.backgroundColor = '#d4edda';
        healthStatus.style.color = '#155724';
    } else if (healthPercentage >= 90) {
        healthStatus.textContent = 'Very Good';
        healthStatus.style.backgroundColor = '#d4edda';
        healthStatus.style.color = '#155724';
    } else {
        healthStatus.textContent = 'Good';
        healthStatus.style.backgroundColor = '#fff3cd';
        healthStatus.style.color = '#856404';
    }
}

// Water Level Chart using ApexCharts
function initWaterLevelChart() {
    const options = {
        series: [0],
        chart: {
            height: 150,
            type: 'radialBar',
            toolbar: {
                show: false
            }
        },
        plotOptions: {
            radialBar: {
                startAngle: -135,
                endAngle: 135,
                hollow: {
                    margin: 0,
                    size: '70%',
                    background: '#f3f4f6',
                    image: undefined,
                    imageOffsetX: 0,
                    imageOffsetY: 0,
                    position: 'front',
                },
                track: {
                    background: '#e7e7e7',
                    strokeWidth: '67%',
                    margin: 0,
                },
                dataLabels: {
                    show: false
                }
            }
        },
        fill: {
            type: 'gradient',
            gradient: {
                shade: 'dark',
                type: 'horizontal',
                shadeIntensity: 0.5,
                gradientToColors: ['#4c9aff'],
                inverseColors: true,
                opacityFrom: 1,
                opacityTo: 1,
                stops: [0, 100]
            }
        },
        stroke: {
            lineCap: 'round'
        },
        labels: ['Water Level'],
        colors: ['#0C71E0'],
    };

    window.waterLevelChart = new ApexCharts(document.querySelector("#water-level-chart"), options);
    window.waterLevelChart.render();
}

// pH Level Bar with gradient
function initPHBar() {
    // Add styles for the pH bar if needed
    const style = document.createElement('style');
    style.textContent = `
        .ph-container {
            padding: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .ph-bar-container {
            position: relative;
            width: 100%;
            height: 30px;
            margin-bottom: 15px;
        }
        .ph-bar-background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to right, #FF0000, #FFFF00, #00FF00, #00FFFF, #0000FF);
            border-radius: 5px;
        }
        .ph-bar-fill {
            position: absolute;
            top: 0;
            left: 0;
            width: 2px;
            height: 100%;
            background-color: black;
            border-radius: 5px;
            transition: left 0.5s ease;
        }
        .ph-scale {
            display: flex;
            justify-content: space-between;
            width: 100%;
            margin-top: 5px;
        }
        .simple-reading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        .reading-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
            color: #0C71E0;
        }
        .sensor-value {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .reading-status {
            font-size: 1rem;
            padding: 3px 8px;
            border-radius: 10px;
            background-color: #d4edda;
            color: #155724;
        }
        .reading-status.critical {
            background-color: #f8d7da;
            color: #721c24;
        }
        .reading-status.warning {
            background-color: #fff3cd;
            color: #856404;
        }
        .reading-status.optimal {
            background-color: #d4edda;
            color: #155724;
        }
        .sensors-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(2, 1fr);
            gap: 20px;
        }
        @media (max-width: 992px) {
            .sensors-grid {
                grid-template-columns: repeat(2, 1fr);
                grid-template-rows: repeat(3, 1fr);
            }
        }
        @media (max-width: 576px) {
            .sensors-grid {
                grid-template-columns: 1fr;
                grid-template-rows: repeat(6, 1fr);
            }
        }
    `;
    document.head.appendChild(style);
}

// Update pH bar position based on value
function updatePHBar(value) {
    const percentage = (value / 14) * 100;
    document.getElementById('ph-bar').style.left = `${percentage}%`;
    document.getElementById('ph-value').textContent = value.toFixed(1);
}

// Determine status based on value and thresholds
function getStatusClass(value, min, max, optimalMin, optimalMax) {
    if (value < min || value > max) {
        return { text: 'Critical', class: 'critical' };
    } else if (value < optimalMin || value > optimalMax) {
        return { text: 'Warning', class: 'warning' };
    } else {
        return { text: 'Optimal', class: 'optimal' };
    }
}

// Update status display
function updateStatusDisplay(elementId, status) {
    const element = document.getElementById(elementId);
    element.textContent = status.text;
    element.className = 'reading-status ' + status.class;
}

// Fetch current sensor data
async function fetchCurrentData() {
    try {
        const response = await fetch('/api/sensors/current');
        const data = await response.json();
        
        // Update water level
        window.waterLevelChart.updateSeries([data.water_level]);
        document.getElementById('water-level-value').textContent = `${data.water_level.toFixed(1)}%`;
        
        // Update pH level
        updatePHBar(data.ph_level);
        
        // Update simple readings with values and status
        document.getElementById('temperature-value').textContent = `${data.temperature.toFixed(1)}°C`;
        updateStatusDisplay('temperature-status', 
            getStatusClass(data.temperature, 15, 35, 18, 28));
        
        document.getElementById('humidity-value').textContent = `${data.humidity.toFixed(0)}%`;
        updateStatusDisplay('humidity-status', 
            getStatusClass(data.humidity, 30, 95, 50, 85));
        
        document.getElementById('tds-value').textContent = `${data.tds_level.toFixed(0)} ppm`;
        updateStatusDisplay('tds-status', 
            getStatusClass(data.tds_level, 300, 2000, 600, 1500));
        
        document.getElementById('oxygen-value').textContent = `${data.dissolved_oxygen.toFixed(1)} mg/L`;
        updateStatusDisplay('oxygen-status', 
            getStatusClass(data.dissolved_oxygen, 3, 12, 5, 8));
        
    } catch (error) {
        console.error('Error fetching current data:', error);
    }
}

// Fetch historical sensor data
async function fetchHistoricalData(hours) {
    try {
        const response = await fetch(`/api/sensors/history?hours=${hours}`);
        const data = await response.json();
        
        if (data.length === 0) {
            console.log('No historical data available');
            return;
        }
        
        // Process data for Chart.js
        const timestamps = data.map(item => new Date(item.timestamp).toLocaleTimeString());
        const datasets = [
            {
                label: 'Temperature (°C)',
                data: data.map(item => item.temperature),
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-temperature'
            },
            {
                label: 'Humidity (%)',
                data: data.map(item => item.humidity),
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-humidity'
            },
            {
                label: 'pH Level',
                data: data.map(item => item.ph_level),
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-ph'
            },
            {
                label: 'Water Level (%)',
                data: data.map(item => item.water_level),
                borderColor: 'rgba(153, 102, 255, 1)',
                backgroundColor: 'rgba(153, 102, 255, 0.2)',
                borderWidth: 2,
                tension: 0.3,
                yAxisID: 'y-water'
            }
        ];
        
        // Create or update the chart
        updateHistoryChart(timestamps, datasets);
        
    } catch (error) {
        console.error('Error fetching historical data:', error);
    }
}

// Update or create the history chart
function updateHistoryChart(labels, datasets) {
    const ctx = document.getElementById('history-chart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (window.historyChart) {
        window.historyChart.destroy();
    }
    
    // Create new chart
    window.historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 10
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                'y-temperature': {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    },
                    min: 15,
                    max: 35,
                    grid: {
                        display: false
                    }
                },
                'y-humidity': {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Humidity (%)'
                    },
                    min: 30,
                    max: 100,
                    grid: {
                        display: false
                    }
                },
                'y-ph': {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'pH Level'
                    },
                    min: 0,
                    max: 14,
                    grid: {
                        display: false
                    },
                    display: false
                },
                'y-water': {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Water Level (%)'
                    },
                    min: 0,
                    max: 100,
                    grid: {
                        display: false
                    },
                    display: false
                }
            }
        }
    });
}

// Toggle which datasets are visible in the chart
function toggleChartDataset(datasetIndex) {
    const isHidden = window.historyChart.isDatasetHidden(datasetIndex);
    window.historyChart.setDatasetVisibility(datasetIndex, isHidden);
    window.historyChart.update();
}

// Add event listener for responsive design
window.addEventListener('resize', function() {
    if (window.historyChart) {
        window.historyChart.resize();
    }
});
