/**
 * Calendar Utility Functions
 * Helper functions for the standby calendar
 */

class CalendarUtils {
    constructor() {
        this.today = new Date().toISOString().split('T')[0];
        this.currentView = 'dayGridMonth';
    }

    /**
     * Format date for display
     */
    formatDate(date, format = 'long') {
        const d = new Date(date);
        const options = {
            short: { month: 'short', day: 'numeric' },
            long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' },
            month: { month: 'long', year: 'numeric' }
        };
        return d.toLocaleDateString('en-US', options[format] || options.long);
    }

    /**
     * Get status for a date
     */
    getDateStatus(date) {
        if (date === this.today) return 'Current';
        if (date < this.today) return 'Completed';
        return 'Upcoming';
    }

    /**
     * Export calendar data to CSV
     */
    exportToCSV(events, title) {
        let csvContent = 'data:text/csv;charset=utf-8,';
        csvContent += 'Person,Date,Status,Day of Week\n';
        
        events.forEach(event => {
            const person = event.title;
            const date = event.start.toISOString().split('T')[0];
            const status = this.getDateStatus(date);
            const dayOfWeek = new Date(date).toLocaleDateString('en-US', { weekday: 'long' });
            
            csvContent += `${person},${date},${status},${dayOfWeek}\n`;
        });
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `standby_schedule_${title.replace(/\s+/g, '_')}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Debounce function for performance
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Check if device is mobile
     */
    isMobile() {
        return window.innerWidth < 768;
    }

    /**
     * Get current month and year from URL or current date
     */
    getCurrentMonthYear() {
        const urlParams = new URLSearchParams(window.location.search);
        const year = parseInt(urlParams.get('year')) || new Date().getFullYear();
        const month = parseInt(urlParams.get('month')) || new Date().getMonth() + 1;
        return { year, month };
    }

    /**
     * Update URL with current month/year
     */
    updateURL(year, month) {
        const url = new URL(window.location);
        url.searchParams.set('year', year);
        url.searchParams.set('month', month);
        window.history.replaceState({}, '', url);
    }

    /**
     * Load calendar data from API
     */
    async loadCalendarData(year, month) {
        try {
            const response = await fetch(`/api/calendar/${year}/${month}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to load calendar data:', error);
            throw error;
        }
    }

    /**
     * Generate legend HTML
     */
    generateLegendHTML(events, personColors) {
        const uniquePeople = [...new Set(events.map(event => event.title))];
        return uniquePeople.map(person => {
            const color = personColors[person] || '#6c757d';
            const isToday = events.some(event => 
                event.title === person && 
                event.start === this.today
            );
            
            return `
                <div class="col-md-3 col-sm-6 mb-2">
                    <div class="d-flex align-items-center">
                        <div class="me-2" style="width: 16px; height: 16px; background-color: ${color}; border-radius: 3px;"></div>
                        <span class="small">${person}</span>
                        ${isToday ? '<span class="badge bg-warning text-dark ms-2">Today</span>' : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Initialize keyboard shortcuts
     */
    initKeyboardShortcuts(calendar) {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch(e.key) {
                case 'ArrowLeft':
                    calendar.prev();
                    break;
                case 'ArrowRight':
                    calendar.next();
                    break;
                case 't':
                case 'T':
                    calendar.today();
                    break;
                case 'm':
                case 'M':
                    calendar.changeView('dayGridMonth');
                    break;
                case 'w':
                case 'W':
                    calendar.changeView('timeGridWeek');
                    break;
            }
        });
    }

    /**
     * Show keyboard shortcuts help
     */
    showKeyboardHelp() {
        const shortcuts = document.getElementById('keyboardShortcuts');
        if (shortcuts) {
            shortcuts.classList.add('show');
            setTimeout(() => {
                shortcuts.classList.remove('show');
            }, 3000);
        }
    }

    /**
     * Initialize responsive behavior
     */
    initResponsive(calendar) {
        const handleResize = this.debounce(() => {
            if (this.isMobile()) {
                calendar.setOption('headerToolbar', {
                    left: 'prev,next',
                    center: 'title',
                    right: 'dayGridMonth'
                });
            } else {
                calendar.setOption('headerToolbar', {
                    left: 'prev,next',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek'
                });
            }
        }, 250);

        window.addEventListener('resize', handleResize);
        handleResize(); // Initial call
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CalendarUtils;
} else {
    window.CalendarUtils = CalendarUtils;
} 