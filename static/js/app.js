// Alpine.js 主组件 - 管理应用状态和交互
function novelApp() {
    return {
        // ===== 状态 =====
        projects: [],
        currentProject: null,
        selectedProjectId: null,
        chapters: [],
        currentChapter: null,
        messages: [],
        inputMessage: '',
        isGenerating: false,
        abortController: null,
        llmOnline: false,
        contextWindow: 20,  // 滑动窗口：最近 N 条消息作为上下文
        contextInfo: { message_count: 0, compress_threshold: 30, has_summary: false },
        isCompressing: false,
        // 章节正文编辑
        editorMode: 'chat',  // 'chat' | 'edit'
        chapterContent: '',
        saveStatus: 'saved',  // 'saved' | 'saving' | 'unsaved'
        saveTimer: null,

        // 设定面板
        activePanel: 'characters',  // 'characters' | 'worldviews'
        characters: [],
        worldviews: [],

        // 模态框状态
        showNewProject: false,
        showNewChapter: false,
        newProjectName: '',
        newProjectGenre: '',
        newChapterTitle: '',

        // 角色编辑
        showCharModal: false,
        editingChar: null,
        charForm: { name: '', role: '', description: '', personality: '', background: '', appearance: '', keywords: '' },

        // 世界观编辑
        showWvModal: false,
        editingWv: null,
        wvForm: { category: '其他', title: '', content: '', keywords: '' },

        // 主题与通知
        darkMode: false,
        toasts: [],
        toastSeq: 0,

        // ===== 生命周期 =====
        async init() {
            this.initTheme();
            // 监听消息变化，自动滚动到底部
            this.$watch('messages', () => this.$nextTick(() => this.scrollToBottom()));
            await this.checkLLMHealth();
            await this.loadProjects();
            setInterval(() => this.checkLLMHealth(), 30000);
        },

        scrollToBottom() {
            const area = this.$refs.chatArea;
            if (area) area.scrollTop = area.scrollHeight;
        },

        // ===== 主题 =====
        initTheme() {
            const saved = localStorage.getItem('novel-theme');
            if (saved === 'dark') {
                this.darkMode = true;
                document.documentElement.dataset.theme = 'dark';
            } else if (saved === 'light') {
                this.darkMode = false;
                document.documentElement.dataset.theme = 'light';
            } else {
                // 跟随系统偏好
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                this.darkMode = prefersDark;
                document.documentElement.dataset.theme = prefersDark ? 'dark' : 'light';
            }
        },
        toggleTheme() {
            this.darkMode = !this.darkMode;
            document.documentElement.dataset.theme = this.darkMode ? 'dark' : 'light';
            localStorage.setItem('novel-theme', this.darkMode ? 'dark' : 'light');
        },

        // ===== Toast 通知 =====
        showToast(message, type = 'info', duration = 4000) {
            const id = ++this.toastSeq;
            const iconMap = { error: '✕', warning: '!', info: 'i', success: '✓' };
            this.toasts.push({ id, message, type, icon: iconMap[type] || 'i' });
            if (duration > 0) {
                setTimeout(() => this.removeToast(id), duration);
            }
        },
        removeToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        },

        // ===== LLM 状态 =====
        async checkLLMHealth() {
            try {
                const data = await api.llmHealth();
                this.llmOnline = data.online;
            } catch {
                this.llmOnline = false;
            }
        },

        // ===== 项目 =====
        async loadProjects() {
            this.projects = await api.listProjects();
            if (this.projects.length > 0 && !this.currentProject) {
                await this.selectProject(this.projects[0]);
            }
        },

        async selectProject(project) {
            this.currentProject = project;
            this.selectedProjectId = project?.id || null;
            this.currentChapter = null;
            this.messages = [];
            await Promise.all([
                this.loadChapters(),
                this.loadMessages(),
                this.loadCharacters(),
                this.loadWorldviews(),
            ]);
            await this.loadContextInfo();
        },

        async onProjectSelect() {
            const project = this.projects.find(p => p.id === this.selectedProjectId);
            if (project) await this.selectProject(project);
        },

        async createProject() {
            if (!this.newProjectName.trim()) return;
            try {
                const project = await api.createProject({
                    name: this.newProjectName.trim(),
                    genre: this.newProjectGenre.trim(),
                });
                this.projects.push(project);
                await this.selectProject(project);
                this.showNewProject = false;
                this.newProjectName = '';
                this.newProjectGenre = '';
                this.showToast('项目已创建', 'success');
            } catch (e) {
                this.showToast('创建项目失败: ' + e, 'error');
            }
        },

        // ===== 章节 =====
        async loadChapters() {
            if (!this.currentProject) return;
            this.chapters = await api.listChapters(this.currentProject.id);
        },

        async selectChapter(chapter) {
            this.currentChapter = chapter;
            this.editorMode = 'chat';
            this.chapterContent = chapter.content || '';
            this.saveStatus = 'saved';
            await this.loadMessages();
            await this.loadContextInfo();
        },

        async createChapter() {
            if (!this.currentProject || !this.newChapterTitle.trim()) return;
            try {
                const chapter = await api.createChapter(
                    this.currentProject.id,
                    { title: this.newChapterTitle.trim() }
                );
                this.chapters.push(chapter);
                await this.selectChapter(chapter);
                this.showNewChapter = false;
                this.newChapterTitle = '';
                this.showToast('章节已创建', 'success');
            } catch (e) {
                this.showToast('创建章节失败: ' + e, 'error');
            }
        },

        // ===== 对话 =====
        async loadMessages() {
            if (!this.currentProject) return;
            const chapterId = this.currentChapter?.id || null;
            this.messages = await api.getMessages(this.currentProject.id, chapterId);
        },

        async sendMessage() {
            const msg = this.inputMessage.trim();
            if (!msg || this.isGenerating || !this.currentProject) return;

            this.isGenerating = true;
            this.inputMessage = '';
            this.abortController = new AbortController();

            this.messages.push({ role: 'user', content: msg });
            const aiMsg = { role: 'assistant', content: '' };
            this.messages.push(aiMsg);

            const chapterId = this.currentChapter?.id || null;
            await api.chat(this.currentProject.id, msg, chapterId, {
                onChunk: (chunk) => { aiMsg.content += chunk; },
                onDone: () => {
                    this.isGenerating = false;
                    this.abortController = null;
                },
                onError: (err) => {
                    this.isGenerating = false;
                    this.abortController = null;
                    this.showToast(err, 'error');
                    if (!aiMsg.content) aiMsg.content = '[生成失败: ' + err + ']';
                },
                signal: this.abortController.signal,
            }, this.contextWindow);
            await this.loadContextInfo();
        },

        stopGeneration() {
            if (this.abortController) {
                this.abortController.abort();
                this.isGenerating = false;
            }
        },

        async clearMessages() {
            if (!this.currentProject || !confirm('确定清空对话历史？')) return;
            const chapterId = this.currentChapter?.id || null;
            await api.clearMessages(this.currentProject.id, chapterId);
            this.messages = [];
            await this.loadContextInfo();
        },

        onKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        },

        backToProjectChat() {
            this.currentChapter = null;
            this.loadMessages();
            this.loadContextInfo();
        },

        // ===== 上下文管理 =====
        async loadContextInfo() {
            if (!this.currentProject) return;
            const chapterId = this.currentChapter?.id || null;
            try {
                this.contextInfo = await api.getContextInfo(this.currentProject.id, chapterId);
            } catch {}
        },

        async compressContext() {
            if (!this.currentProject || this.isCompressing) return;
            this.isCompressing = true;
            try {
                const chapterId = this.currentChapter?.id || null;
                const result = await api.compressContext(this.currentProject.id, chapterId);
                if (result.compressed) {
                    this.showToast('上下文已压缩', 'success');
                    await this.loadMessages();
                    await this.loadContextInfo();
                } else {
                    this.showToast(result.message, 'warning');
                }
            } catch (e) {
                this.showToast('压缩失败: ' + e, 'error');
            } finally {
                this.isCompressing = false;
            }
        },

        // ===== 章节正文编辑 =====
        get chapterWordCount() {
            return this.chapterContent ? this.chapterContent.length : 0;
        },

        switchToEdit() {
            this.editorMode = 'edit';
            if (this.currentChapter) {
                this.chapterContent = this.currentChapter.content || '';
            }
        },

        onContentInput() {
            this.saveStatus = 'unsaved';
            if (this.saveTimer) clearTimeout(this.saveTimer);
            this.saveTimer = setTimeout(() => this.saveChapterContent(), 2000);
        },

        async saveChapterContent() {
            if (!this.currentChapter) return;
            this.saveStatus = 'saving';
            try {
                const updated = await api.updateChapter(
                    this.currentChapter.id,
                    { content: this.chapterContent }
                );
                this.currentChapter = updated;
                this.saveStatus = 'saved';
                await this.loadChapters();
            } catch (e) {
                this.saveStatus = 'unsaved';
                this.showToast('保存失败: ' + e, 'error');
            }
        },

        // ===== 导出 =====
        exportChapter() {
            if (!this.currentChapter) return;
            const fmt = 'txt';
            window.open(
                `/api/chapters/${this.currentChapter.id}/export?format=${fmt}`,
                '_blank'
            );
        },

        exportProject() {
            if (!this.currentProject) return;
            window.open(
                `/api/projects/${this.currentProject.id}/export?format=md`,
                '_blank'
            );
        },

        // ===== 角色 =====
        async loadCharacters() {
            if (!this.currentProject) return;
            this.characters = await api.listCharacters(this.currentProject.id);
        },

        openCharModal(char = null) {
            this.editingChar = char;
            if (char) {
                this.charForm = { ...char };
            } else {
                this.charForm = { name: '', role: '', description: '', personality: '', background: '', appearance: '', keywords: '' };
            }
            this.showCharModal = true;
        },

        async saveCharacter() {
            if (!this.charForm.name.trim()) return;
            try {
                if (this.editingChar) {
                    const updated = await api.updateCharacter(this.editingChar.id, this.charForm);
                    const idx = this.characters.findIndex(c => c.id === this.editingChar.id);
                    if (idx >= 0) this.characters[idx] = updated;
                    this.showToast('角色已更新', 'success');
                } else {
                    const created = await api.createCharacter(this.currentProject.id, this.charForm);
                    this.characters.push(created);
                    this.showToast('角色已添加', 'success');
                }
                this.showCharModal = false;
            } catch (e) {
                this.showToast('保存角色失败: ' + e, 'error');
            }
        },

        async deleteCharacter(char) {
            if (!confirm(`确定删除角色「${char.name}」？`)) return;
            try {
                await api.deleteCharacter(char.id);
                this.characters = this.characters.filter(c => c.id !== char.id);
                this.showToast('角色已删除', 'info');
            } catch (e) {
                this.showToast('删除失败: ' + e, 'error');
            }
        },

        // ===== 世界观 =====
        async loadWorldviews() {
            if (!this.currentProject) return;
            this.worldviews = await api.listWorldviews(this.currentProject.id);
        },

        openWvModal(wv = null) {
            this.editingWv = wv;
            if (wv) {
                this.wvForm = { ...wv };
            } else {
                this.wvForm = { category: '其他', title: '', content: '', keywords: '' };
            }
            this.showWvModal = true;
        },

        async saveWorldview() {
            if (!this.wvForm.title.trim() || !this.wvForm.content.trim()) return;
            try {
                if (this.editingWv) {
                    const updated = await api.updateWorldview(this.editingWv.id, this.wvForm);
                    const idx = this.worldviews.findIndex(w => w.id === this.editingWv.id);
                    if (idx >= 0) this.worldviews[idx] = updated;
                    this.showToast('世界观已更新', 'success');
                } else {
                    const created = await api.createWorldview(this.currentProject.id, this.wvForm);
                    this.worldviews.push(created);
                    this.showToast('世界观已添加', 'success');
                }
                this.showWvModal = false;
            } catch (e) {
                this.showToast('保存世界观失败: ' + e, 'error');
            }
        },

        async deleteWorldview(wv) {
            if (!confirm(`确定删除「${wv.title}」？`)) return;
            try {
                await api.deleteWorldview(wv.id);
                this.worldviews = this.worldviews.filter(w => w.id !== wv.id);
                this.showToast('已删除', 'info');
            } catch (e) {
                this.showToast('删除失败: ' + e, 'error');
            }
        },
    };
}
