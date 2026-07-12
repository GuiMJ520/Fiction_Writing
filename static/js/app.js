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

        // ===== 生命周期 =====
        async init() {
            await this.checkLLMHealth();
            await this.loadProjects();
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
            await Promise.all([
                this.loadChapters(),
                this.loadMessages(),
                this.loadCharacters(),
                this.loadWorldviews(),
            ]);
        },

        async createProject() {
            if (!this.newProjectName.trim()) return;
            const project = await api.createProject({
                name: this.newProjectName.trim(),
                genre: this.newProjectGenre.trim(),
            });
            this.projects.push(project);
            await this.selectProject(project);
            this.showNewProject = false;
            this.newProjectName = '';
            this.newProjectGenre = '';
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
            const chapter = await api.createChapter(
                this.currentProject.id,
                { title: this.newChapterTitle.trim() }
            );
            this.chapters.push(chapter);
            await this.selectChapter(chapter);
            this.showNewChapter = false;
            this.newChapterTitle = '';
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
                    this.error = err;
                    if (!aiMsg.content) aiMsg.content = '[生成失败: ' + err + ']';
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
            if (!this.currentProject || !confirm('确定清空对话历史？')) return;
            const chapterId = this.currentChapter?.id || null;
            await api.clearMessages(this.currentProject.id, chapterId);
            this.messages = [];
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
                } else {
                    const created = await api.createCharacter(this.currentProject.id, this.charForm);
                    this.characters.push(created);
                }
                this.showCharModal = false;
            } catch (e) {
                this.error = '保存角色失败: ' + e;
            }
        },

        async deleteCharacter(char) {
            if (!confirm(`确定删除角色「${char.name}」？`)) return;
            await api.deleteCharacter(char.id);
            this.characters = this.characters.filter(c => c.id !== char.id);
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
                } else {
                    const created = await api.createWorldview(this.currentProject.id, this.wvForm);
                    this.worldviews.push(created);
                }
                this.showWvModal = false;
            } catch (e) {
                this.error = '保存世界观失败: ' + e;
            }
        },

        async deleteWorldview(wv) {
            if (!confirm(`确定删除「${wv.title}」？`)) return;
            await api.deleteWorldview(wv.id);
            this.worldviews = this.worldviews.filter(w => w.id !== wv.id);
        },
    };
}
