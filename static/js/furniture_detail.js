/**
 * Furniture detail page JavaScript
 * Handles image gallery functionality and product interactions
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeGallery();
    initializeZoom();
    initializeActionButtons();
});

/**
 * Initialize the image gallery with thumbnails
 */
function initializeGallery() {
    try {
        const thumbnails = document.querySelectorAll('.gallery-thumbnail');
        const mainImage = document.getElementById('main-product-image');

        if (!mainImage || thumbnails.length === 0) {
            console.log('Gallery elements not found or no thumbnails available');
            return;
        }

        // Set up error handling for main image
        mainImage.onerror = function () {
            console.error('Failed to load main image');
            this.src = '/static/images/placeholder.jpg'; // Fallback image path
        };

        // Set up thumbnail clicks
        thumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function () {
                const imageSrc = this.getAttribute('data-src');
                if (!imageSrc) return;

                // Update main image
                mainImage.src = imageSrc;

                // Update active state
                thumbnails.forEach(thumb => thumb.classList.remove('active'));
                this.classList.add('active');
            });

            // Add error handling for thumbnails
            thumbnail.onerror = function () {
                console.error('Failed to load thumbnail');
                this.src = '/static/images/placeholder.jpg'; // Fallback image
                this.style.opacity = '0.5'; // Visual indication of error
            };
        });
    } catch (error) {
        console.error('Error initializing gallery:', error);
    }
}

/**
 * Initialize zoom functionality for the main product image
 */
function initializeZoom() {
    try {
        const mainImage = document.getElementById('main-product-image');
        const imageContainer = document.querySelector('.main-image-container');

        if (!mainImage) {
            console.log('Main image element not found');
            return;
        }

        // Toggle zoom class on click
        mainImage.addEventListener('click', function () {
            this.classList.toggle('zoomed');

            // Add/remove a class to the container for styling purposes
            if (imageContainer) {
                imageContainer.classList.toggle('zoomed-container');
            }
        });

        // Remove zoom when clicking outside the image
        document.addEventListener('click', function (event) {
            if (event.target !== mainImage && mainImage.classList.contains('zoomed')) {
                mainImage.classList.remove('zoomed');
                if (imageContainer) {
                    imageContainer.classList.remove('zoomed-container');
                }
            }
        });
    } catch (error) {
        console.error('Error setting up image zoom:', error);
    }
}

/**
 * Initialize action buttons functionality
 */
function initializeActionButtons() {
    try {
        // Initialize action buttons if they exist
        const actionButtons = document.querySelectorAll('.action-button');

        if (actionButtons.length === 0) {
            return;
        }

        actionButtons.forEach(button => {
            // Add click functionality for specific actions
            button.addEventListener('click', function (e) {
                // Handle specific button actions if needed
                if (this.dataset.action === 'contact') {
                    const contactSection = document.getElementById('contact');
                    if (contactSection) {
                        e.preventDefault();
                        contactSection.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            });
        });
    } catch (error) {
        console.error('Error initializing action buttons:', error);
    }
}
