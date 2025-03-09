// script.js

// Function to set the active link in the sidebar
function setActiveLink() {
    // Get all the links in the sidebar
    const links = document.querySelectorAll('.sidepanel a');
    
    // Get the current page's path (no .html extension)
    const currentPage = window.location.pathname.split('/').pop();
  
    // Loop through each link and remove the 'active' class
    links.forEach(link => {
      link.classList.remove('active');
    });
  
    // Find the link that matches the current page and add the 'active' class
    const activeLink = document.querySelector(`#${currentPage}-link`);
    if (activeLink) {
      activeLink.classList.add('active');
    }
  }
  
  // Call the function when the page loads
  window.addEventListener('DOMContentLoaded', setActiveLink);
  