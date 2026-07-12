// Alpine.js 主组件 - 管理应用状态和交互
function novelApp() {
    return {
        // ===== 状态 =====
        projects: [],
        currentProject: null,
        chapters: [],
        currentChapter: null,
        messages: [],
        inputMessage: '',
        isGenerating: false,
        abortController: null,
        llmOnline: false,
        error: '',

        // 模态框状态
        showNewProject: false,
        showNewChapter: false,
        newProjectName: '',
        newProjectGenre: '',
        newChapterTitle: '',

        // ===== 生命周期 =====
        async init() {
            await this.checkLLMHealth();
            await this.loadProjects();
            // 定期检查 LLM 状态
            setInterval(() => this.checkLLMHealth(), 30000);
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
            this.currentChapter = null;
            this.messages = [];
            await this.loadChapters();
            await this.loadMessages();
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
            } catch (e) {
                this.error = '创建项目失败: ' + e;
            }
        },

        // ===== 章节 =====
        async loadChapters() {
            if (!this.currentProject) return;
            this.chapters = await api.listChapters(this.currentProject.id);
        },

        async selectChapter(chapter) {
            this.currentChapter = chapter;
            await this.loadMessages();
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
            } catch (e) {
                this.error = '创建章节失败: ' + e;
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
            this.error = '';
            this.inputMessage = '';
            this.abortController = new AbortController();

            // 添加用户消息
            this.messages.push({ role: 'user', content: msg });
            // 创建 AI 回复占位
            const aiMsg = { role: 'assistant', content: '' };
            this.messages.push(aiMsg);

            const chapterId = this.currentChapter?.id || null;
            await api.chat(this.currentProject.id, msg, chapterId, {
                onChunk: (chunk) => {
                    aiMsg.content += chunk;
                },
                onDone: () => {
                    this.isGenerating = false;
                    this.abortController = null;
                },
                onError: (err) => {
                    this.isGenerating = false;
                    this.abortController = null;
                    this.error = err;
                    if (!aiMsg.content) {
                        aiMsg.content = '[生成失败: ' + err + ']';
                    }
                },
                signal: this.abortController.signal,
            });
        },

        stopGeneration() {
            if (this.abortController) {
                this.abortController.abort();
                this.isGenerating = false;
            }
        },

        async clearMessages() {
            if (!this.currentProject) return;
            if (!confirm('确定清空对话历史？')) return;
            const chapterId = this.currentChapter?.id || null;
            await api.clearMessages(this.currentProject.id, chapterId);
            this.messages = [];
        },

        // 键盘事件：Enter 发送，Shift+Enter 换行
        onKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        },

        // 退出章节对话，回到项目级对话
        backToProjectChat() {
            this.currentChapter = null;
            this.loadMessages();
        },
    };
}
