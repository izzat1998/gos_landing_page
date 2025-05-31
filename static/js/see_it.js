document.addEventListener('DOMContentLoaded', () => {
    const roomImageUpload = document.getElementById('roomImageUpload');
    const roomDisplay = document.getElementById('roomDisplay');
    // const roomPlaceholderText = roomDisplay ? roomDisplay.querySelector('.sir-placeholder-text') : null; // Replaced by getRoomPlaceholderText
    const furnitureSelector = document.getElementById('furnitureSelector');
    const furnitureItemTemplate = document.getElementById('furnitureItemTemplate'); // Added

    // Robust way to get placeholder, as roomDisplay might not be found initially if there's an HTML error.
    const getRoomPlaceholderText = () => roomDisplay ? roomDisplay.querySelector('.sir-placeholder-text') : null;

    if (!roomImageUpload || !roomDisplay || !furnitureSelector || !furnitureItemTemplate) { // Modified
        console.error('SIR Feature: Essential HTML elements not found. Check IDs: roomImageUpload, roomDisplay, furnitureSelector, furnitureItemTemplate. Also ensure .sir-placeholder-text exists in roomDisplay if used.');
        // Note: roomPlaceholderText itself is not checked here as it's dynamically fetched and checked by getRoomPlaceholderText()
        return;
    }

    roomImageUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                roomDisplay.style.backgroundImage = `url('${e.target.result}')`;
                const placeholder = getRoomPlaceholderText();
                if (placeholder) placeholder.style.display = 'none';
                clearFurnitureFromRoom();
            };
            reader.onerror = () => {
                console.error('SIR Feature: Error reading file.');
                alert('Error loading image. Please try another file.');
                roomDisplay.style.backgroundImage = 'none';
                const placeholder = getRoomPlaceholderText();
                if (placeholder) placeholder.style.display = 'flex';
            };
            reader.readAsDataURL(file);
        }
    });

    function clearFurnitureFromRoom() {
        const existingFurniture = roomDisplay.querySelectorAll('.sir-furniture-item');
        existingFurniture.forEach(item => item.remove());
        console.log('SIR Feature: Furniture cleared from room display.');
        if (window.sirActiveFurniture) {
            deselectFurniture(window.sirActiveFurniture); // Deselect if active
            window.sirActiveFurniture = null;
        }
    }

    async function loadFurnitureCatalog() {
        if (!furnitureSelector) return;

        try {
            const response = await fetch('/static/furniture_data.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const furnitureItems = await response.json();

            furnitureSelector.innerHTML = '';

            if (furnitureItems.length === 0) {
                furnitureSelector.innerHTML = '<p>No furniture items available.</p>';
                return;
            }

            furnitureItems.forEach(itemData => { // Renamed item to itemData to avoid conflict
                const thumb = document.createElement('img');
                thumb.src = itemData.thumbnail_url;
                thumb.alt = itemData.name;
                thumb.title = itemData.name;
                thumb.dataset.itemId = itemData.id;
                thumb.dataset.imageUrl = itemData.image_url;

                thumb.addEventListener('click', () => addFurnitureToRoom(itemData)); // Modified: Call addFurnitureToRoom

                furnitureSelector.appendChild(thumb);
            });

        } catch (error) {
            console.error('SIR Feature: Could not load furniture catalog:', error);
            if (furnitureSelector) {
                furnitureSelector.innerHTML = '<p>Error loading furniture. Please try again later.</p>';
            }
        }
    }

    loadFurnitureCatalog();

    window.sirActiveFurniture = null;

    // --- New Functionality: Add Furniture to Room ---
    function addFurnitureToRoom(itemData) {
        if (!roomDisplay || !furnitureItemTemplate) {
            console.error("SIR Feature: roomDisplay or furnitureItemTemplate not found.");
            return;
        }

        // Clone the template for the furniture item
        const templateContent = furnitureItemTemplate.content.cloneNode(true);
        const newFurniture = templateContent.querySelector('.sir-furniture-item');

        if (!newFurniture) {
            console.error("SIR Feature: .sir-furniture-item not found in template.");
            return;
        }

        newFurniture.src = itemData.image_url;
        newFurniture.alt = itemData.name;
        newFurniture.dataset.itemId = itemData.id; // Keep track of which item it is

        // Set initial position (e.g., top-left or centered)
        newFurniture.style.left = '10px';
        newFurniture.style.top = '10px';
        // Initial size relies on CSS max-width: 100px for .sir-furniture-item.

        // Add event listeners for manipulation (drag, select, etc.)
        newFurniture.addEventListener('mousedown', onFurnitureMouseDown);
        // newFurniture.addEventListener('touchstart', onFurnitureMouseDown, { passive: false }); // For touch

        roomDisplay.appendChild(newFurniture);

        // Automatically select the newly added item
        selectFurniture(newFurniture);
    }
    // --- End New Functionality ---

    // --- Selection and Manipulation ---
    function selectFurniture(element) {
        if (window.sirActiveFurniture && window.sirActiveFurniture !== element) {
            deselectFurniture(window.sirActiveFurniture);
        }
        if (element) {
            element.classList.add('selected');
            // Bring to front (simple z-index management)
            const allFurniture = roomDisplay.querySelectorAll('.sir-furniture-item');
            let maxZ = 0;
            allFurniture.forEach(f => {
                const currentZ = parseInt(f.style.zIndex, 10) || 0;
                if (currentZ > maxZ) maxZ = currentZ;
            });
            // Ensure the new item is above others, even if it's the only one or maxZ was 0
            element.style.zIndex = maxZ + 1;


            window.sirActiveFurniture = element;
            // Future: Add resize/rotate handles here
            console.log('SIR Feature: Selected', element.alt);
        }
    }

    function deselectFurniture(element) {
        if (element) {
            element.classList.remove('selected');
            // Future: Remove resize/rotate handles here
            console.log('SIR Feature: Deselected', element.alt);
        }
        // Only nullify if the element being deselected is indeed the active one.
        if (window.sirActiveFurniture === element) {
            window.sirActiveFurniture = null;
        }
    }

    function onFurnitureMouseDown(event) {
        event.preventDefault(); // Prevent text selection, image dragging ghost
        const item = event.currentTarget;
        selectFurniture(item); // Select the item on mousedown

        item.style.cursor = 'grabbing';

        // Dragging logic will be added here in the next step
        console.log('SIR Feature: Mouse down on', item.alt);

        // To prevent roomDisplay's mousedown from firing and deselecting immediately
        event.stopPropagation();
    }

    // Click on room display to deselect any active furniture
    if (roomDisplay) {
        roomDisplay.addEventListener('mousedown', (event) => {
            // Only deselect if the click is directly on roomDisplay and not on a child that might handle its own mousedown (like a furniture item)
            if (event.target === roomDisplay && window.sirActiveFurniture) {
                deselectFurniture(window.sirActiveFurniture);
            }
        });
    }

    // Other SIR feature logic will go here...
});
