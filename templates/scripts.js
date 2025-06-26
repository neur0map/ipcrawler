// Modern ipcrawler Report JavaScript - Enhanced UX Features

class ReportController {
    constructor() {
        this.searchTimeout = null;
        this.isSearchActive = false;
        this.collapsibleSections = [];
        this.init();
    }

    init() {
        // Initialize all functionality when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
    }

    setupUI() {
        this.setupCollapsibleSections();
        this.setupSearch();
        this.setupKeyboardShortcuts();
        this.setupScrollEnhancements();
        this.setupTableEnhancements();
        this.setupAccessibility();
        this.setupThemeToggle();
        this.autoExpandCriticalSections();
    }

    // Enhanced collapsible sections with better animations
    setupCollapsibleSections() {
        this.collapsibleSections = Array.from(document.getElementsByClassName('collapsible'));
        
        this.collapsibleSections.forEach((collapsible, index) => {
            // Add icons for better UX
            const icon = document.createElement('span');
            icon.className = 'collapsible-icon';
            icon.innerHTML = '▼';
            collapsible.appendChild(icon);

            // Add click handler with improved animation
            collapsible.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleCollapsible(collapsible);
            });

            // Store reference for keyboard navigation
            collapsible.setAttribute('data-index', index);
        });
    }

    toggleCollapsible(collapsible) {
        const isActive = collapsible.classList.contains('active');
        const content = collapsible.nextElementSibling;
        
        if (!content || !content.classList.contains('content')) return;

        if (isActive) {
            // Collapse
            collapsible.classList.remove('active');
            content.classList.remove('active');
            content.style.maxHeight = '0px';
            
            // Update ARIA attributes
            collapsible.setAttribute('aria-expanded', 'false');
        } else {
            // Expand
            collapsible.classList.add('active');
            content.classList.add('active');
            
            // Calculate dynamic height
            const scrollHeight = content.scrollHeight;
            content.style.maxHeight = scrollHeight + 'px';
            
            // Update ARIA attributes
            collapsible.setAttribute('aria-expanded', 'true');
            
            // Smooth scroll to section if it's below the fold
            setTimeout(() => {
                const rect = collapsible.getBoundingClientRect();
                if (rect.top < 0) {
                    collapsible.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start',
                        inline: 'nearest'
                    });
                }
            }, 300);
        }
    }

    // Enhanced search functionality
    setupSearch() {
        // Create search container if it doesn't exist
        let searchContainer = document.querySelector('.search-container');
        if (!searchContainer) {
            searchContainer = this.createSearchContainer();
            const summarySection = document.querySelector('.section');
            if (summarySection) {
                summarySection.insertAdjacentElement('afterend', searchContainer);
            }
        }

        const searchInput = searchContainer.querySelector('.search-input');
        if (!searchInput) return;

        // Real-time search with debouncing
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value.trim());
            }, 300);
        });

        // Clear search on Escape
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                this.clearSearch();
            }
        });
    }

    createSearchContainer() {
        const container = document.createElement('div');
        container.className = 'section search-container';
        container.innerHTML = `
            <div style="position: relative;">
                <span class="search-icon">🔍</span>
                <input 
                    type="text" 
                    class="search-input" 
                    placeholder="Search reports, services, vulnerabilities..."
                    aria-label="Search report content"
                >
            </div>
            <div class="search-results" style="display: none; margin-top: 1rem;">
                <div class="search-stats"></div>
                <div class="search-matches"></div>
            </div>
        `;
        return container;
    }

    performSearch(query) {
        const resultsContainer = document.querySelector('.search-results');
        const statsContainer = document.querySelector('.search-stats');
        const matchesContainer = document.querySelector('.search-matches');
        
        if (!query) {
            this.clearSearch();
            return;
        }

        this.isSearchActive = true;
        const sections = document.querySelectorAll('.target-section, .quick-access-item');
        let matchCount = 0;
        let matches = [];

        sections.forEach((section) => {
            const text = section.textContent.toLowerCase();
            const hasMatch = text.includes(query.toLowerCase());
            
            if (hasMatch) {
                matchCount++;
                section.style.display = 'block';
                section.classList.add('search-match');
                
                // Highlight matching text
                this.highlightText(section, query);
                
                // Extract match context
                const context = this.extractMatchContext(section, query);
                if (context) {
                    matches.push(context);
                }
            } else {
                section.style.display = 'none';
                section.classList.remove('search-match');
                this.removeHighlights(section);
            }
        });

        // Update search results
        if (resultsContainer && statsContainer) {
            resultsContainer.style.display = 'block';
            statsContainer.innerHTML = `Found ${matchCount} matches for "${query}"`;
            
            if (matchesContainer && matches.length > 0) {
                matchesContainer.innerHTML = matches.slice(0, 5).map(match => 
                    `<div class="search-match-item" onclick="document.getElementById('${match.id}')?.scrollIntoView({behavior: 'smooth'})">
                        <strong>${match.title}</strong>: ${match.context}
                    </div>`
                ).join('');
            }
        }

        // Auto-expand sections with matches
        this.expandMatchingSections();
    }

    clearSearch() {
        this.isSearchActive = false;
        const sections = document.querySelectorAll('.target-section, .quick-access-item');
        const resultsContainer = document.querySelector('.search-results');
        
        sections.forEach((section) => {
            section.style.display = 'block';
            section.classList.remove('search-match');
            this.removeHighlights(section);
        });

        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
    }

    highlightText(element, query) {
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            if (node.textContent.toLowerCase().includes(query.toLowerCase())) {
                textNodes.push(node);
            }
        }

        textNodes.forEach(textNode => {
            const text = textNode.textContent;
            const regex = new RegExp(`(${query})`, 'gi');
            const highlightedText = text.replace(regex, '<mark class="search-highlight">$1</mark>');
            
            if (highlightedText !== text) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = highlightedText;
                const parent = textNode.parentNode;
                
                while (tempDiv.firstChild) {
                    parent.insertBefore(tempDiv.firstChild, textNode);
                }
                parent.removeChild(textNode);
            }
        });
    }

    removeHighlights(element) {
        const highlights = element.querySelectorAll('.search-highlight');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });
    }

    extractMatchContext(section, query) {
        const title = section.querySelector('.target-title, h4')?.textContent || 'Unknown';
        const text = section.textContent.toLowerCase();
        const index = text.indexOf(query.toLowerCase());
        
        if (index === -1) return null;
        
        return {
            id: section.id || `section-${Math.random().toString(36).substr(2, 9)}`,
            title: title,
            context: text.substr(Math.max(0, index - 50), 100) + '...'
        };
    }

    expandMatchingSections() {
        const matchingSections = document.querySelectorAll('.search-match');
        matchingSections.forEach(section => {
            const collapsibles = section.querySelectorAll('.collapsible:not(.active)');
            collapsibles.forEach(collapsible => {
                this.toggleCollapsible(collapsible);
            });
        });
    }

    // Keyboard shortcuts for better accessibility
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + F for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Ctrl/Cmd + K for search (alternative)
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Arrow keys for collapsible navigation
            if (e.target.classList.contains('collapsible')) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigateCollapsibles('down', e.target);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigateCollapsibles('up', e.target);
                } else if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleCollapsible(e.target);
                }
            }
        });
    }

    navigateCollapsibles(direction, current) {
        const currentIndex = parseInt(current.getAttribute('data-index'));
        let nextIndex;

        if (direction === 'down') {
            nextIndex = currentIndex + 1;
        } else {
            nextIndex = currentIndex - 1;
        }

        const nextCollapsible = document.querySelector(`[data-index="${nextIndex}"]`);
        if (nextCollapsible) {
            nextCollapsible.focus();
        }
    }

    // Enhanced scroll behavior
    setupScrollEnhancements() {
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Scroll to top button
        this.createScrollToTopButton();
    }

    createScrollToTopButton() {
        const button = document.createElement('button');
        button.className = 'scroll-to-top';
        button.innerHTML = '↑';
        button.setAttribute('aria-label', 'Scroll to top');
        button.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background: var(--primary-color);
            color: white;
            border: none;
            font-size: 1.2rem;
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;

        document.body.appendChild(button);

        // Show/hide based on scroll position
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                button.style.opacity = '1';
                button.style.visibility = 'visible';
            } else {
                button.style.opacity = '0';
                button.style.visibility = 'hidden';
            }
        });

        button.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Table enhancements
    setupTableEnhancements() {
        const tables = document.querySelectorAll('.table');
        tables.forEach(table => {
            // Make tables more responsive
            this.makeTableResponsive(table);
            
            // Add sorting if headers are clickable
            this.addTableSorting(table);
        });
    }

    makeTableResponsive(table) {
        const wrapper = table.closest('.table-container');
        if (!wrapper) return;

        // Add scroll indicators
        const scrollIndicator = document.createElement('div');
        scrollIndicator.className = 'table-scroll-indicator';
        scrollIndicator.style.cssText = `
            position: absolute;
            top: 0;
            right: 0;
            width: 20px;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.1));
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        wrapper.style.position = 'relative';
        wrapper.appendChild(scrollIndicator);

        wrapper.addEventListener('scroll', () => {
            const isScrollable = wrapper.scrollWidth > wrapper.clientWidth;
            const isAtEnd = wrapper.scrollLeft >= wrapper.scrollWidth - wrapper.clientWidth - 10;
            
            scrollIndicator.style.opacity = (isScrollable && !isAtEnd) ? '1' : '0';
        });
    }

    addTableSorting(table) {
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            header.addEventListener('click', () => {
                this.sortTable(table, index);
            });
        });
    }

    sortTable(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isNumeric = this.isNumericColumn(rows, columnIndex);
        const isAscending = !table.dataset.sortOrder || table.dataset.sortOrder === 'desc';

        rows.sort((a, b) => {
            const aText = a.cells[columnIndex]?.textContent.trim() || '';
            const bText = b.cells[columnIndex]?.textContent.trim() || '';

            if (isNumeric) {
                const aNum = parseFloat(aText) || 0;
                const bNum = parseFloat(bText) || 0;
                return isAscending ? aNum - bNum : bNum - aNum;
            } else {
                return isAscending ? 
                    aText.localeCompare(bText) : 
                    bText.localeCompare(aText);
            }
        });

        // Update DOM
        rows.forEach(row => tbody.appendChild(row));
        
        // Update sort order
        table.dataset.sortOrder = isAscending ? 'asc' : 'desc';
        
        // Update header indicators
        const headers = table.querySelectorAll('th');
        headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        headers[columnIndex].classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    }

    isNumericColumn(rows, columnIndex) {
        const sample = rows.slice(0, 5);
        let numericCount = 0;
        
        sample.forEach(row => {
            const text = row.cells[columnIndex]?.textContent.trim();
            if (text && !isNaN(parseFloat(text))) {
                numericCount++;
            }
        });
        
        return numericCount > sample.length / 2;
    }

    // Enhanced accessibility
    setupAccessibility() {
        // Add ARIA attributes to collapsibles
        this.collapsibleSections.forEach((collapsible, index) => {
            const content = collapsible.nextElementSibling;
            const contentId = `content-${index}`;
            
            collapsible.setAttribute('aria-expanded', 'false');
            collapsible.setAttribute('aria-controls', contentId);
            collapsible.setAttribute('role', 'button');
            collapsible.setAttribute('tabindex', '0');
            
            if (content) {
                content.setAttribute('id', contentId);
                content.setAttribute('role', 'region');
            }
        });

        // Improve table accessibility
        const tables = document.querySelectorAll('.table');
        tables.forEach((table, index) => {
            table.setAttribute('role', 'table');
            table.setAttribute('aria-label', `Data table ${index + 1}`);
            
            const headers = table.querySelectorAll('th');
            headers.forEach((header, headerIndex) => {
                header.setAttribute('scope', 'col');
                header.setAttribute('role', 'columnheader');
            });
        });
    }

    // Theme toggle functionality
    setupThemeToggle() {
        const themeToggle = document.createElement('button');
        themeToggle.className = 'theme-toggle';
        themeToggle.innerHTML = '🌙';
        themeToggle.setAttribute('aria-label', 'Toggle theme');
        themeToggle.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background: var(--bg-elevated);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        `;

        document.body.appendChild(themeToggle);

        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            themeToggle.innerHTML = document.body.classList.contains('light-theme') ? '☀️' : '🌙';
            
            // Save preference
            localStorage.setItem('ipcrawler-theme', 
                document.body.classList.contains('light-theme') ? 'light' : 'dark'
            );
        });

        // Load saved theme
        const savedTheme = localStorage.getItem('ipcrawler-theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
            themeToggle.innerHTML = '☀️';
        }
    }

    // Auto-expand critical findings
    autoExpandCriticalSections() {
        const criticalSections = document.querySelectorAll('.collapsible[data-critical="true"]');
        criticalSections.forEach(section => {
            if (!section.classList.contains('active')) {
                this.toggleCollapsible(section);
            }
        });

        // Also expand sections with vulnerabilities
        const vulnSections = document.querySelectorAll('.collapsible');
        vulnSections.forEach(section => {
            const content = section.nextElementSibling;
            if (content && content.querySelector('.vulnerability, .critical, [class*="vuln"]')) {
                if (!section.classList.contains('active')) {
                    this.toggleCollapsible(section);
                }
            }
        });
    }
}

// Performance monitoring
class PerformanceMonitor {
    constructor() {
        this.startTime = performance.now();
        this.markLoadComplete();
    }

    markLoadComplete() {
        window.addEventListener('load', () => {
            const loadTime = performance.now() - this.startTime;
            console.log(`Report loaded in ${loadTime.toFixed(2)}ms`);
            
            // Add performance indicator
            this.addPerformanceIndicator(loadTime);
        });
    }

    addPerformanceIndicator(loadTime) {
        const indicator = document.createElement('div');
        indicator.style.cssText = `
            position: fixed;
            bottom: 1rem;
            left: 1rem;
            background: var(--bg-elevated);
            color: var(--text-tertiary);
            padding: 0.5rem 1rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            border: 1px solid var(--border-color);
            z-index: 1000;
            opacity: 0.7;
        `;
        indicator.textContent = `Loaded in ${loadTime.toFixed(0)}ms`;
        document.body.appendChild(indicator);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            indicator.style.opacity = '0';
            setTimeout(() => indicator.remove(), 300);
        }, 3000);
    }
}

// Initialize everything
const reportController = new ReportController();
const performanceMonitor = new PerformanceMonitor();

// Export for potential external use
window.ReportController = ReportController;