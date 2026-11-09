(function () {
    var overlay = document.getElementById('app-loading');
    if (!overlay) return;

    var showDelay = 250;
    var timer = null;

    function showLoading(event) {
        if (timer !== null) window.clearTimeout(timer);

        timer = window.setTimeout(function () {
            timer = null;
            if (event && event.defaultPrevented) return;
            overlay.hidden = false;
            document.documentElement.setAttribute('aria-busy', 'true');
        }, showDelay);
    }

    function hideLoading() {
        if (timer !== null) {
            window.clearTimeout(timer);
            timer = null;
        }
        overlay.hidden = true;
        document.documentElement.removeAttribute('aria-busy');
    }

    function isSamePageHash(url) {
        return url.origin === window.location.origin
            && url.pathname === window.location.pathname
            && url.search === window.location.search
            && url.hash !== ''
            && url.hash !== window.location.hash;
    }

    document.addEventListener('click', function (event) {
        if (event.defaultPrevented || event.button !== 0
            || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

        var link = event.target.closest('a[href]');
        if (!link || link.hasAttribute('download')
            || (link.target && link.target !== '_self')) return;

        var url;
        try {
            url = new URL(link.href, window.location.href);
        } catch (_error) {
            return;
        }

        if (url.origin !== window.location.origin
            || url.href === window.location.href
            || isSamePageHash(url)) return;

        showLoading(event);
    }, true);

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement) || form.dataset.noLoading === 'true'
            || (form.target && form.target !== '_self')) return;

        var action;
        try {
            action = new URL(form.action || window.location.href, window.location.href);
        } catch (_error) {
            return;
        }

        if (action.origin !== window.location.origin) return;
        showLoading(event);
    }, true);

    window.addEventListener('pageshow', hideLoading);
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !overlay.hidden) hideLoading();
    });
})();
