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
document.querySelectorAll('.section-header, .collection-item, .about-item, .contact-form, .feature-item').forEach(el => {
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
        const targetId = this.getAttribute('href');
        // Check if the href is just # or empty
        if (targetId === '#') return;

        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            e.preventDefault();
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
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

// Parallax Effect
const parallaxBackground = document.querySelector('.parallax-background');
const heroContent = document.querySelector('.hero-content');
const floatingElements = document.querySelectorAll('.floating-element');

window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    
    if (parallaxBackground) {
        parallaxBackground.style.transform = `translateY(${scrolled * 0.5}px)`;
    }
    
    if (heroContent) {
        heroContent.style.transform = `translateY(${scrolled * 0.3}px)`;
    }
    
    floatingElements.forEach(element => {
        const speed = element.getAttribute('data-speed');
        element.style.transform = `translateY(${scrolled * speed}px)`;
    });
});

// Mobile Menu Toggle
const mobileMenuButton = document.querySelector('.mobile-menu-button');
const mobileMenuClose = document.querySelector('.mobile-menu-close');
const mobileMenu = document.querySelector('.mobile-menu');
const navbar = document.querySelector('.navbar');

function toggleMobileMenu() {
    mobileMenu.classList.toggle('active');
    navbar.classList.toggle('mobile-menu-open');
    document.body.classList.toggle('menu-open');
}

if (mobileMenuButton && mobileMenuClose) {
    mobileMenuButton.addEventListener('click', toggleMobileMenu);
    mobileMenuClose.addEventListener('click', toggleMobileMenu);
    
    // Close menu when clicking on a link
    const mobileLinks = document.querySelectorAll('.mobile-nav-links a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', () => {
            toggleMobileMenu();
        });
    });
}

// Animation Observer Setup
const animationObserverOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

// Unified Observer for all animations
const animationObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            // Add visible class
            entry.target.classList.add('visible');
            
            // Handle staggered children
            if (entry.target.classList.contains('stagger-fade')) {
                const children = entry.target.children;
                Array.from(children).forEach((child, index) => {
                    setTimeout(() => {
                        child.classList.add('visible');
                    }, index * 100);
                });
            }
            
            // Handle counter animation
            if (entry.target.classList.contains('counter')) {
                startCounter(entry.target);
            }
            
            // Unobserve after animation
            animationObserver.unobserve(entry.target);
        }
    });
}, animationObserverOptions);

// Counter Animation Function
function startCounter(counterElement) {
    const target = parseInt(counterElement.getAttribute('data-target'));
    const duration = 2000; // 2 seconds
    const step = target / (duration / 16); // 60fps
    let current = 0;
    
    counterElement.classList.add('counting');
    
    const updateCounter = () => {
        current += step;
        if (current < target) {
            counterElement.textContent = Math.round(current);
            requestAnimationFrame(updateCounter);
        } else {
            counterElement.textContent = target;
            counterElement.classList.remove('counting');
        }
    };
    
    requestAnimationFrame(updateCounter);
}

// Observe all animated elements
document.querySelectorAll('.scroll-reveal, .fade-up, .stagger-fade > *, .counter').forEach(element => {
    animationObserver.observe(element);
});

// Initialize slide-in animations
const slideInElements = document.querySelectorAll('.slide-in-text');
const slideInObserver = new IntersectionObserver(
    (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                observer.unobserve(entry.target);
            }
        });
    },
    { threshold: 0.1 }
);

slideInElements.forEach(element => {
    element.style.animationPlayState = 'paused';
    slideInObserver.observe(element);
});

// Cube animations
const heroImage = document.querySelector('.hero-image');
if (heroImage) {
    function createCube() {
        // Check if we already have 6 cubes
        const existingCubes = heroImage.querySelectorAll('.cube');
        if (existingCubes.length >= 6) {
            return;
        }

        const cube = document.createElement('div');
        cube.classList.add('cube');

        // Use transform for better performance
        const size = Math.random() * 100 + 15;
        const startPosition = Math.random() * 100;
        const rotation = Math.random() * 360;
        const duration = Math.random() * 1 + 6; // Random duration between 6-7 seconds

        cube.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${startPosition}%;
            animation-duration: ${duration}s;
            transform: rotate(${rotation}deg);
        `;

        heroImage.appendChild(cube);

        // Use requestAnimationFrame for cleanup
        requestAnimationFrame(() => {
            cube.addEventListener('animationend', () => {
                cube.remove();
            }, { once: true });
        });
    }

    // Use requestIdleCallback if available
    const createCubeWrapper = () => {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(createCube);
        } else {
            createCube();
        }
    };

    setInterval(createCubeWrapper, 1500); // Increased interval to account for longer animation duration
}