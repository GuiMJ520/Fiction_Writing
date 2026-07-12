// API 调用封装 - 所有后端接口的统一入口

const api = {
    // ===== 项目 =====
    async listProjects() {
        const r = await fetch('/api/projects');
        return r.json();
    },
    async createProject(data) {
        const r = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return r.json();
    },
    async getProject(id) {
        const r = await fetch(`/api/projects/${id}`);
        return r.json();
    },
    async updateProject(id, data) {
        const r = await fetch(`/api/projects/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return r.json();
    },
    async deleteProject(id) {
        const r = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
        return r.json();
    },

    // ===== 章节 =====
    async listChapters(projectId) {
        const r = await fetch(`/api/projects/${projectId}/chapters`);
        return r.json();
    },
    async createChapter(projectId, data) {
        const r = await fetch(`/api/projects/${projectId}/chapters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return r.json();
    },
    async getChapter(id) {
        const r = await fetch(`/api/chapters/${id}`);
        return r.json();
    },
    async updateChapter(id, data) {
        const r = await fetch(`/api/chapters/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return r.json();
    },
    async deleteChapter(id) {
        const r = await fetch(`/api/chapters/${id}`, { method: 'DELETE' });
        return r.json();
    },
    async reorderChapters(projectId, chapterIds) {
        const r = await fetch(`/api/projects/${projectId}/chapters/reorder`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(chapterIds),
        });
        return r.json();
    },

    // ===== 对话 =====
    async getMessages(projectId, chapterId = null) {
        const url = chapterId
            ? `/api/projects/${projectId}/messages?chapter_id=${chapterId}`
            : `/api/projects/${projectId}/messages`;
        const r = await fetch(url);
        return r.json();
    },
    chat(projectId, message, chapterId, callbacks) {
        return streamSSE(
            `/api/projects/${projectId}/chat`,
            { message, chapter_id: chapterId },
            callbacks
        );
    },
    async clearMessages(projectId, chapterId = null) {
        const url = chapterId
            ? `/api/projects/${projectId}/messages?chapter_id=${chapterId}`
            : `/api/projects/${projectId}/messages`;
        const r = await fetch(url, { method: 'DELETE' });
        return r.json();
    },

    // ===== LLM 状态 =====
    async llmHealth() {
        const r = await fetch('/api/llm/health');
        return r.json();
    },
};
