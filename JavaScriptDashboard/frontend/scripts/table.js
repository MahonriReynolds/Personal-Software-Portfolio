document.addEventListener("DOMContentLoaded", function() {
    // Function to fetch the alerts data
    function fetchAlerts() {
        fetch('/api/dashboard-table-data')
            .then(response => response.json()) // Convert response to JSON
            .then(data => {
                populateTable(data.alerts); // Call function to populate the table
            })
            .catch(error => {
                console.error('Error fetching alerts:', error);
            });
    }

    // Function to populate the table with alert data
    function populateTableRecursive(alerts, table) {
        if (alerts.length === 0) return; // Base case
    
        const alert = alerts[0]; // Get the first alert
        const row = document.createElement('tr');
    
        // Function to create and append a table cell
        function createCell(content, className = '') {
            const cell = document.createElement('td');
            cell.textContent = content;
            if (className) cell.classList.add(className);
            return cell;
        }
    
        // Append each cell
        row.appendChild(createCell(alert.urgency, alert.urgency === 'Critical' ? 'critical' : alert.urgency === 'Warning' ? 'warning' : ''));
        row.appendChild(createCell(alert.type));
        row.appendChild(createCell(alert.category));
        row.appendChild(createCell(alert.product));
        row.appendChild(createCell(alert['effective-date']));
    
        table.appendChild(row);
    
        // Recursive call with the remaining alerts
        populateTableRecursive(alerts.slice(1), table);
    }

    function populateTable(alerts) {
        const tableSection = document.getElementById('table-section');
        const table = document.createElement('table');
    
        // Create table header row
        const headerRow = document.createElement('tr');
        const headers = ['Urgency', 'Type', 'Category', 'Product Name', 'Effective Date'];
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            headerRow.appendChild(th);
        });
        table.appendChild(headerRow);
    
        // Clear previous content
        tableSection.innerHTML = '';
    
        // Call recursive function
        populateTableRecursive(alerts, table);
    
        tableSection.appendChild(table);
    }
    
    

    // Fetch the data when the page is ready
    fetchAlerts();
});
