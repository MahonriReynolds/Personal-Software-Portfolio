// Function to fetch data from the API
async function fetchChartData() {
  try {
    const response = await fetch('/api/dashboard-chart-data');
    const data = await response.json();
    processChartData(data);
  } catch (error) {
    console.error('Error fetching chart data:', error);
  }
}

// Function to process the received data
function processChartData(data) {
  const months = getLast12Months(data.charts);

  data.charts.forEach((chartData, index) => {
    const chartContainer = document.getElementById('charts-section');
    
    // Create a wrapper div for each chart
    const chartWrapper = document.createElement('div');
    chartWrapper.style.marginTop = '10px';
    chartWrapper.style.marginBottom = '100px';
    chartWrapper.style.marginLeft = '30px';
    chartWrapper.style.marginRight = '30px';

    // Add a title for the chart based on the category
    const title = document.createElement('h3');
    title.innerText = chartData.category;
    title.style.color = '#ccc';  // Optionally, style the title
    chartWrapper.appendChild(title);  // Append the title to the wrapper

    // Dynamically create a new canvas element for each chart
    const canvas = document.createElement('canvas');
    canvas.id = `chart${index + 1}`;
    canvas.height = 250;  // Set height of each chart to 250px
    chartWrapper.appendChild(canvas);  // Append canvas to the wrapper

    chartContainer.appendChild(chartWrapper);  // Append the wrapper to the container

    const ctx = canvas.getContext('2d');
    const formattedData = formatDataForChart(chartData.data, months);
    createChart(ctx, formattedData, 'Purchase Frequency', 'Usage Frequency', '#25bac3', 'rgba(255, 179, 0, 0.7)', months);
  });
}

// Function to get the last 12 months based on the data
function getLast12Months(charts) {
  // Get the latest month across all categories
  const latestMonth = charts.reduce((latest, chart) => {
    const chartMonths = chart.data.map(item => item.month);
    const maxMonth = Math.max(...chartMonths.map(month => {
      const [year, monthStr] = month.split('-');
      const monthNum = parseInt(monthStr, 10) - 1; // Months are 0-based in Date
      return new Date(year, monthNum).getTime(); // Get the timestamp
    }));
    return maxMonth > latest ? maxMonth : latest;
  }, 0); // Default start to 0

  // Get the previous 12 months starting from the latest month
  const last12Months = [];
  let currentMonth = new Date(latestMonth);

  for (let i = 0; i < 12; i++) {
    last12Months.unshift(currentMonth.toISOString().slice(0, 7)); // Format as 'YYYY-MM'
    currentMonth.setMonth(currentMonth.getMonth() - 1);
  }

  return last12Months;
}


// Function to format the data for the chart
function formatDataForChart(chartData, months) {
  // For each month in the last 12 months, either get the data or return 0 if not present
  return months.map(month => {
    const dataForMonth = chartData.find(item => item.month === month);
    return {
      purchased: dataForMonth ? dataForMonth.orders : 0,
      used: dataForMonth ? dataForMonth.usages : 0
    };
  });
}



// Chart creation function
function createChart(ctx, data, label1, label2, color1, color2, months) {
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: months, // Use the months array as x-axis labels
      datasets: [
        {
          label: label1,
          data: data.map(d => d.purchased),
          backgroundColor: color1,
          borderColor: '#ccc',
          borderWidth: 1,
          fill: false
        },
        {
          label: label2,
          data: data.map(d => d.used),
          backgroundColor: color2,
          borderColor: '#ccc',
          borderWidth: 1,
          fill: false
        }
      ]
    },
    options: {
      scales: {
        x: {
          ticks: {
            autoSkip: false, // Disable auto-skip to show every month
            maxRotation: 45,
            minRotation: 45,
            color: '#ccc'  // Set label color to #ccc
          },
          grid: {
            display: true
          }
        },
        y: {
          ticks: {
            stepSize: 1,
            beginAtZero: true,
            color: '#ccc'
          },
          grid: {
            display: false
          }
        }
      },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#ccc'
          }
        }
      }
    }
  });
}


// Call the function to fetch data and create charts
fetchChartData();
