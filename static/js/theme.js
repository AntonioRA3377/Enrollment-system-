(function () {
    if (window.__ENROLLSYS_UI_LOADED__) return;
    window.__ENROLLSYS_UI_LOADED__ = true;

    const THEME_KEY = 'enrollment_system_theme';
    const NAV_MODE_KEY = 'enrollment_nav_mode';

    function getPreferredTheme() {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved === 'dark' || saved === 'light') return saved;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function getPreferredNavMode() {
        const saved = localStorage.getItem(NAV_MODE_KEY);
        return (saved === 'sidebar' || saved === 'dock') ? saved : 'dock';
    }

    function isBrightColor(rgbStr) {
        if (!rgbStr || rgbStr === 'transparent' || rgbStr === 'rgba(0, 0, 0, 0)') return false;
        const m = rgbStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
        if (!m) return false;
        if (m[4] !== undefined && parseFloat(m[4]) === 0) return false;
        const r = parseInt(m[1], 10), g = parseInt(m[2], 10), b = parseInt(m[3], 10);
        return ((r * 299 + g * 587 + b * 114) / 1000) > 195;
    }

    function adaptSurfaces(theme) {
        if (theme !== 'dark') {
            document.querySelectorAll('[data-dark-surface]').forEach(el => el.removeAttribute('data-dark-surface'));
            return;
        }

        document.querySelectorAll('div, section, main, article, header, form, a, button').forEach(el => {
            if (el.closest('.app-bottom-dock') || el.closest('.dock-more-sheet') ||
                el.closest('.app-system-sidebar') || el.closest('.app-mobile-topbar') ||
                el.classList.contains('app-sidebar-backdrop') ||
                el.classList.contains('badge') || el.classList.contains('action-btn')) return;

            if (el.hasAttribute('data-dark-surface')) return;

            const style = window.getComputedStyle(el);
            if (isBrightColor(style.backgroundColor)) {
                const tag = el.tagName.toLowerCase();
                if (tag === 'a' || tag === 'button' || el.classList.contains('btn')) {
                    el.setAttribute('data-dark-surface', 'btn');
                } else if (el.parentElement === document.body || el.classList.contains('main-content') || el.classList.contains('content')) {
                    el.setAttribute('data-dark-surface', 'bg');
                } else {
                    el.setAttribute('data-dark-surface', 'card');
                }
            }
        });
    }

    function closeAllMobileMenus() {
        const sheet = document.getElementById('dockMoreSheet');
        const moreBtn = document.getElementById('dockMoreBtn');
        const sidebar = document.getElementById('appSystemSidebar');
        const backdrop = document.getElementById('appSidebarBackdrop');
        if (sheet) sheet.classList.remove('open');
        if (moreBtn) moreBtn.classList.remove('active');
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('open');
    }

    function updateControlLabels() {
        const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const navMode = document.documentElement.getAttribute('data-nav-mode') || 'dock';

        document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
            const isSheet = btn.classList.contains('dock-sheet-item');
            if (theme === 'dark') {
                btn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i><span>' + (isSheet ? 'Switch to Light Mode' : 'Light') + '</span>';
            } else {
                btn.innerHTML = '<i class="bi bi-moon-stars-fill text-primary"></i><span>' + (isSheet ? 'Switch to Dark Mode' : 'Dark') + '</span>';
            }
        });

        document.querySelectorAll('[data-nav-toggle]').forEach(btn => {
            const isSheet = btn.classList.contains('dock-sheet-item');
            if (navMode === 'sidebar') {
                btn.innerHTML = '<i class="bi bi-dock-bottom"></i><span>' + (isSheet ? 'Use Bottom Dock' : 'Bottom Dock') + '</span>';
            } else {
                btn.innerHTML = '<i class="bi bi-layout-sidebar"></i><span>' + (isSheet ? 'Use Left Sidebar' : 'Sidebar') + '</span>';
            }
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateControlLabels();
        requestAnimationFrame(() => adaptSurfaces(theme));
    }

    function applyNavMode(mode) {
        closeAllMobileMenus();
        document.documentElement.setAttribute('data-nav-mode', mode);
        localStorage.setItem(NAV_MODE_KEY, mode);
        updateControlLabels();
        const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        requestAnimationFrame(() => adaptSurfaces(theme));
    }

    window.toggleSystemTheme = function () {
        const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
        applyTheme(current === 'dark' ? 'light' : 'dark');
    };

    window.toggleNavigationMode = function () {
        const current = document.documentElement.getAttribute('data-nav-mode') || 'dock';
        applyNavMode(current === 'sidebar' ? 'dock' : 'sidebar');
    };

    function makeLayoutsResponsive() {
        document.querySelectorAll('table').forEach(table => {
            if (!table.parentElement.classList.contains('table-responsive-wrap') &&
                !table.parentElement.classList.contains('table-responsive')) {
                const wrap = document.createElement('div');
                wrap.className = 'table-responsive-wrap';
                table.parentNode.insertBefore(wrap, table);
                wrap.appendChild(table);
            }
        });

        document.querySelectorAll('div, form, header').forEach(el => {
            if (el.closest('.app-bottom-dock') || el.closest('.app-system-sidebar') || el.closest('table')) return;
            const style = window.getComputedStyle(el);
            if (style.display === 'flex' && style.flexWrap === 'nowrap') {
                el.classList.add('responsive-flex-wrap');
            }
        });
    }

    function enhanceActionButtons() {
        const buttonRules = [
            { match: /^view$/i, cls: 'action-btn-view', icon: 'bi-eye-fill', label: 'View' },
            { match: /^enroll$/i, cls: 'action-btn-enroll', icon: 'bi-plus-circle-fill', label: 'Enroll' },
            { match: /^soa$/i, cls: 'action-btn-soa', icon: 'bi-receipt-cutoff', label: 'SOA' },
            { match: /^(cor|my cor)$/i, cls: 'action-btn-cor', icon: 'bi-patch-check-fill', label: null },
            { match: /^edit$/i, cls: 'action-btn-edit', icon: 'bi-pencil-square', label: 'Edit' },
            { match: /^delete$/i, cls: 'action-btn-delete', icon: 'bi-trash3-fill', label: 'Delete' }
        ];

        const candidates = document.querySelectorAll('table td a, table td button, .action-links a, .action-links button');
        const processedParents = new Set();

        candidates.forEach(el => {
            if (el.closest('.app-bottom-dock') || el.closest('.app-system-sidebar')) return;
            const rawText = (el.textContent || '').trim();
            const rule = buttonRules.find(r => r.match.test(rawText));
            if (!rule) return;

            el.classList.remove('btn-info', 'btn-warning', 'btn-secondary', 'btn-light', 'btn-outline-primary', 'btn-outline-info', 'btn-outline-dark');
            el.classList.add('action-btn', rule.cls);

            if (!el.querySelector('i')) {
                const textLabel = rule.label || rawText;
                el.innerHTML = '<i class="bi ' + rule.icon + '"></i><span>' + textLabel + '</span>';
            }

            const parent = el.parentElement;
            if (parent && !processedParents.has(parent)) {
                processedParents.add(parent);
                if (!parent.classList.contains('action-btn-group')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'action-btn-group';
                    while (parent.firstChild) {
                        const child = parent.firstChild;
                        if (child.nodeType === Node.TEXT_NODE && !child.textContent.trim()) {
                            parent.removeChild(child);
                        } else {
                            wrapper.appendChild(child);
                        }
                    }
                    parent.appendChild(wrapper);
                }
            }
        });
    }

    function buildDualNavigation() {
        const path = window.location.pathname;
        if (path === '/login' || path === '/register') return false;

        // Clean any prior injected nodes to guarantee a single clean DOM instance
        document.querySelectorAll('.app-bottom-dock, .dock-more-sheet, .app-system-sidebar, .app-mobile-topbar, .app-sidebar-backdrop').forEach(n => n.remove());

        const meta = document.querySelector('meta[name="app-session"]');
        let role = meta ? (meta.getAttribute('data-role') || '').trim() : '';
        let studentId = meta ? (meta.getAttribute('data-student-id') || '').trim() : '';

        if (!role) {
            if (path.startsWith('/student/dashboard') || path.startsWith('/enrollment/confirmation') || path.includes('/soa')) {
                role = 'student';
            } else {
                role = 'admin';
            }
        }

        const adminNav = [
            { href: '/admin/dashboard', icon: 'bi-speedometer2', label: 'Dashboard', primary: true },
            { href: '/students', icon: 'bi-people-fill', label: 'Students', primary: true },
            { href: '/courses', icon: 'bi-journal-bookmark-fill', label: 'Courses', primary: true },
            { href: '/course_offerings', icon: 'bi-calendar3', label: 'Offerings', primary: true },
            { href: '/reports/enrollment_summary', icon: 'bi-bar-chart-fill', label: 'Summary', primary: false },
            { href: '/reports/student_enrollment', icon: 'bi-file-earmark-check-fill', label: 'Reports', primary: false }
        ];

        const sid = studentId || '1';
        const studentNav = [
            { href: '/student/dashboard', icon: 'bi-grid-1x2-fill', label: 'Dashboard', primary: true },
            { href: '/enrollment/confirmation/' + sid, icon: 'bi-patch-check-fill', label: 'My COR', primary: true },
            { href: '/student/' + sid + '/soa', icon: 'bi-receipt-cutoff', label: 'My SOA', primary: true }
        ];

        const links = role === 'student' ? studentNav : adminNav;
        document.body.classList.add('has-system-nav');

        // 1. Bottom Dock
        const dock = document.createElement('nav');
        dock.className = 'app-bottom-dock no-print';
        dock.setAttribute('aria-label', 'Bottom Navigation');

        const dockLinksHtml = links.map(item => {
            const isActive = path === item.href || (item.href !== '/' && path.startsWith(item.href));
            const secClass = item.primary ? '' : ' dock-secondary';
            return '<a href="' + item.href + '" class="dock-item' + secClass + (isActive ? ' active' : '') + '">' +
                   '<i class="bi ' + item.icon + '"></i><span>' + item.label + '</span></a>';
        }).join('');

        dock.innerHTML =
            '<a href="/dashboard" class="dock-brand">' +
                '<span class="dock-brand-badge"><i class="bi bi-mortarboard-fill"></i></span>' +
                '<span class="dock-brand-text">EnrollSys</span>' +
            '</a>' +
            '<div class="dock-divider"></div>' +
            '<div class="dock-links">' +
                dockLinksHtml +
                '<button type="button" class="dock-item dock-more-btn" id="dockMoreBtn" aria-label="More Options">' +
                    '<i class="bi bi-three-dots"></i><span>More</span>' +
                '</button>' +
            '</div>' +
            '<div class="dock-divider"></div>' +
            '<span class="dock-role-pill">' + role + '</span>' +
            '<button type="button" class="dock-item dock-desktop-ctrl" data-nav-toggle="true"></button>' +
            '<button type="button" class="dock-item dock-desktop-ctrl" data-theme-toggle="true"></button>' +
            '<a href="/logout" class="dock-item dock-logout dock-desktop-ctrl" title="Sign Out">' +
                '<i class="bi bi-box-arrow-right"></i><span>Logout</span>' +
            '</a>';

        // 2. Upward "More" Sheet for Phone / Narrow Mode
        const moreSheet = document.createElement('div');
        moreSheet.className = 'dock-more-sheet no-print';
        moreSheet.id = 'dockMoreSheet';

        const secondaryLinksHtml = links.filter(l => !l.primary).map(item => {
            const isActive = path === item.href || (item.href !== '/' && path.startsWith(item.href));
            return '<a href="' + item.href + '" class="dock-sheet-item' + (isActive ? ' active' : '') + '">' +
                   '<i class="bi ' + item.icon + '"></i><span>' + item.label + '</span></a>';
        }).join('');

        moreSheet.innerHTML =
            (secondaryLinksHtml ? secondaryLinksHtml + '<div class="dock-sheet-divider"></div>' : '') +
            '<button type="button" class="dock-sheet-item" data-nav-toggle="true"></button>' +
            '<button type="button" class="dock-sheet-item" data-theme-toggle="true"></button>' +
            '<div class="dock-sheet-divider"></div>' +
            '<a href="/logout" class="dock-sheet-item text-danger">' +
                '<i class="bi bi-box-arrow-right"></i><span>Logout (' + role + ')</span>' +
            '</a>';

        // 3. Left Sidebar + Mobile Drawer & Hamburger Topbar
        const backdrop = document.createElement('div');
        backdrop.className = 'app-sidebar-backdrop no-print';
        backdrop.id = 'appSidebarBackdrop';

        const mobileBar = document.createElement('div');
        mobileBar.className = 'app-mobile-topbar no-print';
        mobileBar.innerHTML =
            '<div class="d-flex align-items-center gap-2">' +
                '<button type="button" class="sidebar-ctrl-btn" id="openSidebarDrawerBtn" aria-label="Open Navigation Menu">' +
                    '<i class="bi bi-list fs-5"></i>' +
                '</button>' +
                '<a href="/dashboard" class="dock-brand p-0">' +
                    '<span class="dock-brand-badge"><i class="bi bi-mortarboard-fill"></i></span>' +
                    '<span>EnrollSys</span>' +
                '</a>' +
            '</div>' +
            '<div class="d-flex align-items-center gap-2">' +
                '<button type="button" class="sidebar-ctrl-btn" data-nav-toggle="true"></button>' +
                '<button type="button" class="sidebar-ctrl-btn" data-theme-toggle="true"></button>' +
            '</div>';

        const sidebar = document.createElement('aside');
        sidebar.className = 'app-system-sidebar no-print';
        sidebar.id = 'appSystemSidebar';
        sidebar.setAttribute('aria-label', 'Sidebar Navigation');

        const sideLinksHtml = links.map(item => {
            const isActive = path === item.href || (item.href !== '/' && path.startsWith(item.href));
            return '<a href="' + item.href + '" class="sidebar-nav-item ' + (isActive ? 'active' : '') + '">' +
                   '<i class="bi ' + item.icon + '"></i><span>' + item.label + '</span></a>';
        }).join('');

        sidebar.innerHTML =
            '<div class="sidebar-header">' +
                '<a href="/dashboard" class="dock-brand p-0">' +
                    '<span class="dock-brand-badge"><i class="bi bi-mortarboard-fill"></i></span>' +
                    '<span>EnrollSys</span>' +
                '</a>' +
                '<div class="d-flex align-items-center gap-2">' +
                    '<span class="dock-role-pill">' + role + '</span>' +
                    '<button type="button" class="sidebar-close-btn" id="closeSidebarDrawerBtn" aria-label="Close Menu">' +
                        '<i class="bi bi-x-lg"></i>' +
                    '</button>' +
                '</div>' +
            '</div>' +
            '<div class="sidebar-nav-list">' + sideLinksHtml + '</div>' +
            '<div class="sidebar-footer">' +
                '<div class="sidebar-control-row">' +
                    '<button type="button" class="sidebar-ctrl-btn" data-nav-toggle="true"></button>' +
                    '<button type="button" class="sidebar-ctrl-btn" data-theme-toggle="true"></button>' +
                '</div>' +
                '<a href="/logout" class="sidebar-logout-btn">' +
                    '<i class="bi bi-box-arrow-right"></i><span>Logout</span>' +
                '</a>' +
            '</div>';

        document.body.appendChild(moreSheet);
        document.body.appendChild(dock);
        document.body.appendChild(backdrop);
        document.body.appendChild(mobileBar);
        document.body.appendChild(sidebar);

        return true;
    }

    // Global delegated click handler for Hamburger, More tab, Theme & Nav toggles
    document.addEventListener('click', function (e) {
        const moreBtn = e.target.closest('#dockMoreBtn');
        if (moreBtn) {
            e.preventDefault();
            e.stopPropagation();
            const sheet = document.getElementById('dockMoreSheet');
            if (sheet) {
                const isOpen = sheet.classList.toggle('open');
                moreBtn.classList.toggle('active', isOpen);
            }
            return;
        }

        const openDrawerBtn = e.target.closest('#openSidebarDrawerBtn');
        if (openDrawerBtn) {
            e.preventDefault();
            e.stopPropagation();
            const sb = document.getElementById('appSystemSidebar');
            const bd = document.getElementById('appSidebarBackdrop');
            if (sb) sb.classList.add('open');
            if (bd) bd.classList.add('open');
            return;
        }

        if (e.target.closest('#closeSidebarDrawerBtn') || e.target.closest('#appSidebarBackdrop')) {
            e.preventDefault();
            closeAllMobileMenus();
            return;
        }

        if (e.target.closest('[data-theme-toggle]')) {
            e.preventDefault();
            window.toggleSystemTheme();
            return;
        }

        if (e.target.closest('[data-nav-toggle]')) {
            e.preventDefault();
            window.toggleNavigationMode();
            return;
        }

        // Dismiss "More" sheet when tapping anywhere outside it
        const sheet = document.getElementById('dockMoreSheet');
        if (sheet && sheet.classList.contains('open') && !e.target.closest('#dockMoreSheet')) {
            sheet.classList.remove('open');
            const mb = document.getElementById('dockMoreBtn');
            if (mb) mb.classList.remove('active');
        }
    });

    document.addEventListener('DOMContentLoaded', function () {
        const currentTheme = getPreferredTheme();
        const currentNavMode = getPreferredNavMode();

        makeLayoutsResponsive();
        enhanceActionButtons();
        const hasNav = buildDualNavigation();

        if (!hasNav) {
            const floatBtn = document.createElement('button');
            floatBtn.type = 'button';
            floatBtn.className = 'floating-theme-toggle no-print';
            floatBtn.setAttribute('data-theme-toggle', 'true');
            document.body.appendChild(floatBtn);
        }

        applyNavMode(currentNavMode);
        applyTheme(currentTheme);
    });
})();
