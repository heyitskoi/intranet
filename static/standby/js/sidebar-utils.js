/**
 * Sidebar Utilities and Enhancements
 * Additional functionality for the sidebar component
 */

class SidebarUtils {
    constructor() {
        this.isInitialized = false;
        this.tooltips = new Map();
        this.observers = new Map();
    }

    /**
     * Initialize additional sidebar utilities
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupTooltips();
        this.setupIntersectionObserver();
        this.setupKeyboardShortcuts();
        this.setupPerformanceMonitoring();
        
        this.isInitialized = true;
    }

    /**
     * Setup tooltips for navigation items
     */
    setupTooltips() {
        const navLinks = document.querySelectorAll('.nav-link[data-tooltip]');
        
        navLinks.forEach(link => {
            const tooltip = link.getAttribute('data-tooltip');
            this.tooltips.set(link, tooltip);
            
            // Add tooltip functionality
            link.addEventListener('mouseenter', () => this.showTooltip(link));
            link.addEventListener('mouseleave', () => this.hideTooltip(link));
        });
    }

    /**
     * Show tooltip for navigation item
     */
    showTooltip(element) {
        const tooltip = this.tooltips.get(element);
        if (!tooltip) return;

        // Create tooltip element if it doesn't exist
        let tooltipEl = element.querySelector('.custom-tooltip');
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.className = 'custom-tooltip';
            tooltipEl.style.cssText = `
                position: absolute;
                left: 100%;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 0.5rem 0.75rem;
                border-radius: 6px;
                font-size: 0.875rem;
                white-space: nowrap;
                z-index: 1000;
                margin-left: 1rem;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            element.appendChild(tooltipEl);
        }

        tooltipEl.textContent = tooltip;
        tooltipEl.style.opacity = '1';
    }

    /**
     * Hide tooltip for navigation item
     */
    hideTooltip(element) {
        const tooltipEl = element.querySelector('.custom-tooltip');
        if (tooltipEl) {
            tooltipEl.style.opacity = '0';
        }
    }

    /**
     * Setup intersection observer for performance
     */
    setupIntersectionObserver() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('sidebar-visible');
                    } else {
                        entry.target.classList.remove('sidebar-visible');
                    }
                });
            },
            { threshold: 0.1 }
        );

        observer.observe(sidebar);
        this.observers.set('sidebar', observer);
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Ctrl/Cmd + B to toggle sidebar
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }

            // Alt + 1-4 for quick navigation
            if (e.altKey && ['1', '2', '3', '4'].includes(e.key)) {
                e.preventDefault();
                this.navigateToSection(parseInt(e.key));
            }
        });
    }

    /**
     * Toggle sidebar visibility
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebarToggle');
        
        if (sidebar && sidebarToggle) {
            sidebarToggle.click();
        }
    }

    /**
     * Navigate to specific section
     */
    navigateToSection(sectionNumber) {
        const routes = ['dashboard', 'calendar', 'roster', 'overtime'];
        const route = routes[sectionNumber - 1];
        
        if (route) {
            window.location.href = `/${route}`;
        }
    }

    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        // Monitor sidebar performance
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach((entry) => {
                if (entry.entryType === 'measure' && entry.name.includes('sidebar')) {
                    console.log(`Sidebar performance: ${entry.name} took ${entry.duration}ms`);
                }
            });
        });

        observer.observe({ entryTypes: ['measure'] });
        this.observers.set('performance', observer);
    }

    /**
     * Add notification to navigation item
     */
    addNotification(route, count, type = 'default') {
        const navLink = document.querySelector(`[data-route="${route}"]`);
        if (!navLink) return;

        let badge = navLink.querySelector('.notification-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'notification-badge';
            navLink.appendChild(badge);
        }

        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
        
        // Add type-specific styling
        badge.className = `notification-badge notification-${type}`;
    }

    /**
     * Remove notification from navigation item
     */
    removeNotification(route) {
        const navLink = document.querySelector(`[data-route="${route}"]`);
        if (!navLink) return;

        const badge = navLink.querySelector('.notification-badge');
        if (badge) {
            badge.style.display = 'none';
        }
    }

    /**
     * Update sidebar stats with animation
     */
    updateStatsWithAnimation(elementId, newValue, oldValue) {
        const element = document.getElementById(elementId);
        if (!element) return;

        // Add updating class for animation
        element.classList.add('updating');
        
        // Animate the value change
        const startValue = parseFloat(oldValue) || 0;
        const endValue = parseFloat(newValue) || 0;
        const duration = 1000; // 1 second
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = startValue + (endValue - startValue) * easeOutQuart;
            
            element.textContent = typeof newValue === 'string' ? newValue : currentValue.toFixed(1);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.classList.remove('updating');
            }
        };

        requestAnimationFrame(animate);
    }

    /**
     * Add status indicator to navigation item
     */
    addStatusIndicator(route, status = 'active') {
        const navLink = document.querySelector(`[data-route="${route}"]`);
        if (!navLink) return;

        let indicator = navLink.querySelector('.status-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'status-indicator';
            navLink.appendChild(indicator);
        }

        // Update status
        indicator.className = `status-indicator status-${status}`;
        indicator.style.display = 'block';
    }

    /**
     * Remove status indicator from navigation item
     */
    removeStatusIndicator(route) {
        const navLink = document.querySelector(`[data-route="${route}"]`);
        if (!navLink) return;

        const indicator = navLink.querySelector('.status-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    /**
     * Cleanup resources
     */
    destroy() {
        // Disconnect observers
        this.observers.forEach(observer => {
            if (observer && typeof observer.disconnect === 'function') {
                observer.disconnect();
            }
        });

        // Clear tooltips
        this.tooltips.clear();
        this.observers.clear();
        
        this.isInitialized = false;
    }
}

// Initialize utilities when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sidebarUtils = new SidebarUtils();
    window.sidebarUtils.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.sidebarUtils) {
        window.sidebarUtils.destroy();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SidebarUtils;
} 