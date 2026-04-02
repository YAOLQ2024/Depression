(function () {
    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    async function requestJson(url, options = {}) {
        const acceptedCodes = new Set([0, ...(options.acceptedCodes || [])]);
        const { acceptedCodes: _ignoredAcceptedCodes, ...fetchOptions } = options;
        const headers = {
            Accept: "application/json",
            ...(fetchOptions.headers || {}),
        };

        if (fetchOptions.body && !headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }

        const response = await fetch(url, {
            credentials: "same-origin",
            ...fetchOptions,
            headers,
        });

        let payload = null;
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }

        if (!response.ok || !payload || !acceptedCodes.has(payload.code)) {
            const error = new Error(
                payload?.message || `请求失败，状态码 ${response.status}`
            );
            error.status = response.status;
            error.payload = payload;
            throw error;
        }

        return payload;
    }

    function buildQuery(params = {}) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value === undefined || value === null || value === "") return;
            search.set(key, String(value));
        });
        const queryString = search.toString();
        return queryString ? `?${queryString}` : "";
    }

    function buildScaleFormUrl(scaleSlug, flowSessionId = null) {
        return `/scales/${encodeURIComponent(scaleSlug)}${buildQuery({ flow_session_id: flowSessionId })}`;
    }

    function buildScaleResultUrl(recordId, flowSessionId = null) {
        return `/scales/result/${encodeURIComponent(recordId)}${buildQuery({ flow_session_id: flowSessionId })}`;
    }

    function buildFlowResultUrl(flowSessionId) {
        return `/scales/flow-result/${encodeURIComponent(flowSessionId)}`;
    }

    function buildSdsFormUrl(flowSessionId = null) {
        return `/SDS${buildQuery({ flow_session_id: flowSessionId })}`;
    }

    function renderStateMessage(container, type, message) {
        if (!container) return;

        const classMap = {
            info: "bg-slate-50 border-border text-textSecondary",
            success: "bg-emerald-50 border-emerald-200 text-emerald-700",
            warning: "bg-amber-50 border-amber-200 text-amber-700",
            error: "bg-rose-50 border-rose-200 text-rose-700",
        };

        const className = classMap[type] || classMap.info;
        container.className = `rounded-card border px-4 py-3 text-sm ${className}`;
        container.innerHTML = escapeHtml(message);
        container.classList.remove("hidden");
    }

    function hideStateMessage(container) {
        if (!container) return;
        container.classList.add("hidden");
        container.textContent = "";
    }

    function formatDateTime(value) {
        if (!value) return "-";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }
        return date.toLocaleString("zh-CN", { hour12: false });
    }

    window.ScaleAssessmentApi = {
        escapeHtml,
        requestJson,
        buildScaleFormUrl,
        buildScaleResultUrl,
        buildFlowResultUrl,
        buildSdsFormUrl,
        renderStateMessage,
        hideStateMessage,
        formatDateTime,
    };
})();
