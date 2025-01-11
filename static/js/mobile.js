// Mobile Menu Functionality
document.addEventListener('DOMContentLoaded', () => {
    const mobileButton = document.querySelector('.mobile-menu-button');
    const navLinks = document.querySelector('.nav-links');
    const body = document.querySelector('body');

    if (mobileButton && navLinks) {
        mobileButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            mobileButton.classList.toggle('active');
            navLinks.classList.toggle('active');
            body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
            mobileButton.setAttribute('aria-expanded', mobileButton.classList.contains('active'));
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (navLinks.classList.contains('active') && 
                !navLinks.contains(e.target) && 
                !mobileButton.contains(e.target)) {
                mobileButton.classList.remove('active');
                navLinks.classList.remove('active');
                body.style.overflow = '';
                mobileButton.setAttribute('aria-expanded', 'false');
            }
        });

        // Close menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navLinks.classList.contains('active')) {
                mobileButton.classList.remove('active');
                navLinks.classList.remove('active');
                body.style.overflow = '';
                mobileButton.setAttribute('aria-expanded', 'false');
            }
        });

        // Close menu when clicking on nav links
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                mobileButton.classList.remove('active');
                navLinks.classList.remove('active');
                body.style.overflow = '';
                mobileButton.setAttribute('aria-expanded', 'false');
            });
        });
    }
});