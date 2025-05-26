// Phone click tracking functionality
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function handlePhoneClick(event, phoneNumber) {
    event.preventDefault();
    
    const visitId = document.getElementById('visit-id-data')?.dataset?.visitId || '';
    const csrftoken = getCookie('csrftoken');

    if (visitId) {
        try {
            const response = await fetch("/record-phone-click/", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ 'visit_id': visitId })
            });
            // Optional: handle response status or log errors
            if (!response.ok) {
                console.error('Failed to record phone click:', response.statusText);
            }
        } catch (error) {
            console.error('Error recording phone click:', error);
        }
    }
    window.location.href = 'tel:' + phoneNumber;
}

// Initialize phone click tracking when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const ctaPhoneButton = document.getElementById('cta-phone-button');
    if (ctaPhoneButton) {
        ctaPhoneButton.addEventListener('click', function (event) {
            handlePhoneClick(event, '+998903564334');
        });
    }

    const textPhoneLink = document.getElementById('text-phone-link');
    if (textPhoneLink) {
        textPhoneLink.addEventListener('click', function (event) {
            handlePhoneClick(event, '+998903564334');
        });
    }
});
