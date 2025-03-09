// Declare itemsList to store references to dynamically created items
let itemsList = [];

// Fetch products data from the FastAPI endpoint
async function fetchProducts() {
    try {
        const response = await fetch('/api/form-product-data');
        if (response.ok) {
            const data = await response.json();
            return data.products; // Access the 'products' key to get the list of product objects
        } else {
            console.error('Failed to fetch products');
        }
    } catch (error) {
        console.error('Error fetching products:', error);
    }
}

// Function to initialize product data and set up event listeners
async function init() {
    const products = await fetchProducts();
    if (products && products.length > 0) {
        // Function to add new item
        document.getElementById('add-item-btn').addEventListener('click', function() {
            addItem(products);
        });

        // Add a blank item on page load
        addItem(products);
    }
}

// Function to add a new item to the form
function addItem(products) {
    const itemSection = document.getElementById('items-section');
    const newItem = document.createElement('div');
    newItem.classList.add('item-entry');

    const itemCount = itemsList.length + 1;

    const newItemHTML = `
        <label for="product-${itemCount}">Product</label>
        <select name="product-${itemCount}" id="product-${itemCount}" required>
            <option value="" disabled selected>Select a Product</option>
            ${products.map(product => `<option value="${product.id}">${product.name}</option>`).join('')}
        </select>

        <label for="usage-date-${itemCount}">Usage Date</label>
        <input type="date" id="usage-date-${itemCount}" name="usage-date-${itemCount}" required>

        <button type="button" onclick="removeItem(this)">Remove Item</button>
    `;

    newItem.innerHTML = newItemHTML;
    itemSection.appendChild(newItem);

    // Store the item in the list for later reference
    itemsList.push(newItem);
}

// Function to remove an item
function removeItem(button) {
    const itemSection = document.getElementById('items-section');
    const itemToRemove = button.closest('.item-entry');
    const index = itemsList.indexOf(itemToRemove);
    if (index !== -1) {
        itemsList.splice(index, 1);
    }
    itemSection.removeChild(itemToRemove);
}

// Function to collect form data into a JSON object
function collectFormData() {
    const items = itemsList.map(item => {
        const productSelect = item.querySelector('select');
        const usageDateInput = item.querySelector('input[name^="usage-date"]');

        return {
            product: productSelect.value,  // Send product ID
            usageDate: usageDateInput.value,
        };
    });

    return { items }; // Returning an object with an 'items' key
}

// Function to handle form submission
async function handleSubmit(event) {
    event.preventDefault();  // Prevent the default form submission behavior
    
    const formData = collectFormData();  // Collect the form data
    
    try {
        const response = await fetch('/api/usage-report', { // Updated API endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),  // Send the form data as JSON
        });

        const responseData = await response.json(); // Get the JSON response

        // Check the status from the response
        if (response.ok && responseData.status === 200) {
            console.log('Success:', responseData.message);

            // Reset the form after successful submission
            resetForm();

            // Handle successful response (e.g., display a success message)
            alert("Form submitted successfully!");
        } else {
            // If the status is not 200 or response is not ok, show failure message
            alert("Failed to submit the form. Please try again.");
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        alert("An error occurred. Please try again.");
    }
}


// Function to reset the form after successful submission
async function resetForm() {
    // Clear all select elements (product dropdown)
    const productSelects = document.querySelectorAll('select');
    productSelects.forEach(select => {
        select.selectedIndex = 0; // Reset to the default "Select a Product"
    });

    // Clear all date inputs (usage date)
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.value = ''; // Reset the value
    });

    // Remove all items from the items list
    itemsList = [];

    // Optionally, remove all dynamically added items from the UI
    const itemSection = document.getElementById('items-section');
    itemSection.innerHTML = ''; // Clears all items in the section

    // Fetch products data again and re-add the first blank item
    const products = await fetchProducts();
    addItem(products);  // Add the blank item
}

// Add event listener for the submit button
document.getElementById('submit-btn').addEventListener('click', handleSubmit);

// Initialize on page load
window.onload = init;
