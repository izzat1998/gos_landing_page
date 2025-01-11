
// Loading Screen
window.addEventListener('load', () => {
    const loadingScreen = document.querySelector('.loading-screen');
    loadingScreen.classList.add('fade-out');
    setTimeout(() => loadingScreen.remove(), 500);
});

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.2
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

// Observe elements
document.querySelectorAll('.section-header, .collection-item, .about-item, .contact-form').forEach(el => {
    observer.observe(el);
});

// Navbar scroll effect
window.addEventListener('scroll', () => {   
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Dark mode toggle
const darkModeToggle = document.querySelector('.dark-mode-toggle');
if (darkModeToggle) {
    darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const icon = darkModeToggle.querySelector('i');
        icon.classList.toggle('fa-moon');
        icon.classList.toggle('fa-sun');
        
        // Save preference
        const isDarkMode = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDarkMode);
    });

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        darkModeToggle.querySelector('i').classList.replace('fa-moon', 'fa-sun');
    }
}

// Form submission with feedback
const form = document.querySelector('.contact-form');
if (form) {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Add loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        
        // Simulate form submission (replace with actual API call)
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Show success message
        submitBtn.innerHTML = '<i class="fas fa-check"></i> Отправлено!';
        
        // Reset form after delay
        setTimeout(() => {
            submitBtn.innerHTML = originalText;
            form.reset();
        }, 3000);
    });
}

// Cube animations
function createCube() {
    const heroImage = document.querySelector('.hero-image');
    const cube = document.createElement('div');
    cube.classList.add('cube');
    
    const size = Math.random() * 40 + 20;
    cube.style.width = `${size}px`;
    cube.style.height = `${size}px`;
    
    const startPosition = Math.random() * 100;
    cube.style.left = `${startPosition}%`;
    
    const duration = Math.random() * 4 + 4;
    cube.style.animationDuration = `${duration}s`;
    
    const rotation = Math.random() * 360;
    cube.style.transform = `rotate(${rotation}deg)`;
    
    heroImage.appendChild(cube);
    
    setTimeout(() => {
        cube.remove();
    }, duration * 1000);
}

// Create new cube every 300ms
setInterval(createCube, 300);
