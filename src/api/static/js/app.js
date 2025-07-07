// Marcus Pipeline Enhancement Dashboard Application

const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'],  // Change delimiters to avoid conflict with Jinja2
    data() {
        return {
            // Tab management
            activeTab: 'monitor',
            
            // Live Monitor
            dashboard: {
                active_flows: [],
                system_metrics: {},
                health_summary: {},
                alerts: []
            },
            socket: null,
            
            // Pipeline Replay
            replayFlowId: '',
            replaySession: null,
            replayPosition: 0,
            isPlaying: false,
            playInterval: null,
            
            // What-If Analysis
            whatifFlowId: '',
            whatifSession: null,
            modifications: [],
            simulationResults: null,
            
            // Compare Flows
            compareFlowIds: ['', ''],
            comparisonReport: null,
            
            // Recommendations
            recommendFlowId: '',
            recommendations: null,
            similarFlows: null,
            
            // Agent Management
            newAgent: {
                id: '',
                name: '',
                role: ''
            },
            registeredAgents: [],
            taskUpdate: {
                agent_id: '',
                task_id: '',
                status: 'in_progress',
                progress: 0,
                message: ''
            },
            projectStatus: null,
            agentLogs: [],
            
            // Project Management
            newProject: {
                name: '',
                description: ''
            },
            currentProject: null,
            existingProjects: [],
            sampleProjects: [],
            selectedSample: '',
            workflowOptions: {
                auto_assign: true,
                parallel_execution: true,
                continuous_monitoring: true,
                max_agents: 3
            }
        };
    },
    
    mounted() {
        console.log('Vue app mounted, activeTab:', this.activeTab);
        console.log('Dashboard data:', this.dashboard);
        this.initializeWebSocket();
        this.loadDashboard();
        this.refreshProjects();
        this.refreshAgents();
        this.loadSampleProjects();
    },
    
    methods: {
        // Tab management
        switchTab(tabName) {
            console.log('Switching to tab:', tabName);
            this.activeTab = tabName;
        },
        
        // Cost tracking methods
        async fetchProjectCosts(projectId) {
            if (!projectId) return;
            
            try {
                const response = await fetch(`/api/costs/project/${projectId}`);
                const data = await response.json();
                
                if (data.success) {
                    // Update project with real cost data
                    this.currentProject.tokenCosts = data.stats;
                    this.currentProject.costHistory = data.history;
                    this.currentProject.costComparison = data.comparison;
                    
                    // Calculate naive estimate for comparison
                    if (this.currentProject.estimated_hours) {
                        this.currentProject.naive_cost = (this.currentProject.estimated_hours * 150).toFixed(2);
                    }
                }
            } catch (error) {
                console.error('Failed to fetch project costs:', error);
            }
        },
        
        async fetchCostSummary() {
            try {
                const response = await fetch('/api/costs/summary');
                const data = await response.json();
                
                if (data.success) {
                    this.costSummary = data.summary;
                    this.costInsights = data.insights;
                }
            } catch (error) {
                console.error('Failed to fetch cost summary:', error);
            }
        },
        
        // WebSocket Management
        initializeWebSocket() {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('Connected to WebSocket');
            });
            
            this.socket.on('dashboard_update', (data) => {
                this.dashboard = data;
            });
            
            this.socket.on('flow_update', (data) => {
                // Update specific flow in dashboard
                const index = this.dashboard.active_flows.findIndex(f => f.flow_id === data.flow_id);
                if (index !== -1) {
                    this.dashboard.active_flows[index] = data;
                }
            });
        },
        
        // Live Monitor Methods
        async loadDashboard() {
            try {
                const response = await fetch('/api/pipeline/monitor/dashboard');
                const data = await response.json();
                if (data.success) {
                    // Don't overwrite the entire dashboard object
                    this.dashboard.active_flows = data.active_flows || [];
                    this.dashboard.system_metrics = data.system_metrics || {};
                    this.dashboard.health_summary = data.health_summary || {};
                    this.dashboard.alerts = data.alerts || [];
                }
            } catch (error) {
                console.error('Failed to load dashboard:', error);
            }
        },
        
        async viewFlowDetails(flowId) {
            this.replayFlowId = flowId;
            this.activeTab = 'replay';
            await this.startReplay();
        },
        
        // Pipeline Replay Methods
        async startReplay() {
            if (!this.replayFlowId) return;
            
            try {
                const response = await fetch('/api/pipeline/replay/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flow_id: this.replayFlowId })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.replaySession = data;
                    this.replayPosition = data.current_position;
                }
            } catch (error) {
                console.error('Failed to start replay:', error);
            }
        },
        
        async stepForward() {
            try {
                const response = await fetch('/api/pipeline/replay/forward', {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.success) {
                    this.replaySession.state = data.state;
                    this.replayPosition++;
                }
            } catch (error) {
                console.error('Failed to step forward:', error);
            }
        },
        
        async stepBackward() {
            try {
                const response = await fetch('/api/pipeline/replay/backward', {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.success) {
                    this.replaySession.state = data.state;
                    this.replayPosition--;
                }
            } catch (error) {
                console.error('Failed to step backward:', error);
            }
        },
        
        async jumpToPosition() {
            try {
                const response = await fetch('/api/pipeline/replay/jump', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ position: parseInt(this.replayPosition) })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.replaySession.state = data.state;
                }
            } catch (error) {
                console.error('Failed to jump to position:', error);
            }
        },
        
        playPause() {
            if (this.isPlaying) {
                clearInterval(this.playInterval);
                this.isPlaying = false;
            } else {
                this.isPlaying = true;
                this.playInterval = setInterval(async () => {
                    if (this.replayPosition >= this.replaySession.total_events - 1) {
                        this.playPause();
                        return;
                    }
                    await this.stepForward();
                }, 1000);
            }
        },
        
        // What-If Analysis Methods
        async startWhatIf() {
            if (!this.whatifFlowId) return;
            
            try {
                const response = await fetch('/api/pipeline/whatif/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flow_id: this.whatifFlowId })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.whatifSession = data;
                    this.modifications = [];
                }
            } catch (error) {
                console.error('Failed to start what-if analysis:', error);
            }
        },
        
        addModification() {
            this.modifications.push({
                parameter_type: 'requirement',
                parameter_name: '',
                new_value: ''
            });
        },
        
        removeModification(index) {
            this.modifications.splice(index, 1);
        },
        
        async runSimulation() {
            if (!this.modifications.length) return;
            
            try {
                const response = await fetch('/api/pipeline/whatif/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ modifications: this.modifications })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.simulationResults = data.simulation;
                    this.drawWhatIfChart();
                }
            } catch (error) {
                console.error('Failed to run simulation:', error);
            }
        },
        
        drawWhatIfChart() {
            const ctx = document.getElementById('whatifChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['Tasks', 'Complexity', 'Cost', 'Quality'],
                    datasets: [
                        {
                            label: 'Original',
                            data: [
                                this.whatifSession.original_metrics.task_count,
                                this.whatifSession.original_metrics.complexity * 100,
                                this.whatifSession.original_metrics.cost * 10,
                                this.whatifSession.original_metrics.quality * 100
                            ],
                            borderColor: 'rgb(54, 162, 235)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)'
                        },
                        {
                            label: 'Modified',
                            data: [
                                this.simulationResults.predicted_metrics.task_count,
                                this.simulationResults.predicted_metrics.complexity * 100,
                                this.simulationResults.predicted_metrics.cost * 10,
                                this.simulationResults.predicted_metrics.quality * 100
                            ],
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },
        
        // Compare Flows Methods
        addCompareFlow() {
            this.compareFlowIds.push('');
        },
        
        removeCompareFlow(index) {
            this.compareFlowIds.splice(index, 1);
        },
        
        async runComparison() {
            const validFlowIds = this.compareFlowIds.filter(id => id.trim());
            if (validFlowIds.length < 2) return;
            
            try {
                const response = await fetch('/api/pipeline/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flow_ids: validFlowIds })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.comparisonReport = data.report;
                    this.drawComparisonChart();
                }
            } catch (error) {
                console.error('Failed to compare flows:', error);
            }
        },
        
        drawComparisonChart() {
            const ctx = document.getElementById('comparisonChart').getContext('2d');
            
            const labels = this.comparisonReport.flow_summaries.map(f => f.project_name);
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Duration (s)',
                            data: this.comparisonReport.flow_summaries.map(f => f.duration_seconds),
                            backgroundColor: 'rgba(54, 162, 235, 0.5)'
                        },
                        {
                            label: 'Cost ($)',
                            data: this.comparisonReport.flow_summaries.map(f => f.cost),
                            backgroundColor: 'rgba(255, 99, 132, 0.5)'
                        },
                        {
                            label: 'Tasks',
                            data: this.comparisonReport.flow_summaries.map(f => f.task_count),
                            backgroundColor: 'rgba(75, 192, 192, 0.5)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },
        
        // Recommendations Methods
        async getRecommendations() {
            if (!this.recommendFlowId) return;
            
            try {
                const [recResponse, similarResponse] = await Promise.all([
                    fetch(`/api/pipeline/recommendations/${this.recommendFlowId}`),
                    fetch(`/api/pipeline/similar/${this.recommendFlowId}`)
                ]);
                
                const recData = await recResponse.json();
                const similarData = await similarResponse.json();
                
                if (recData.success) {
                    this.recommendations = recData.recommendations;
                }
                
                if (similarData.success) {
                    this.similarFlows = similarData.similar_flows;
                }
            } catch (error) {
                console.error('Failed to get recommendations:', error);
            }
        },
        
        async viewFlow(flowId) {
            this.replayFlowId = flowId;
            this.activeTab = 'replay';
            await this.startReplay();
        },
        
        // Agent Management Methods
        async registerAgent() {
            if (!this.newAgent.id || !this.newAgent.name || !this.newAgent.role) {
                alert('Please fill in all agent fields');
                return;
            }
            
            try {
                const response = await fetch('/api/agents/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        agent_id: this.newAgent.id,
                        name: this.newAgent.name,
                        role: this.newAgent.role,
                        skills: []
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.agentLogs.unshift({
                        timestamp: new Date().toISOString(),
                        agent_id: this.newAgent.id,
                        message: `Agent registered successfully`
                    });
                    
                    // Clear form
                    this.newAgent = { id: '', name: '', role: '' };
                    
                    // Refresh agent list
                    await this.refreshAgents();
                } else {
                    alert(`Failed to register agent: ${data.error}`);
                }
            } catch (error) {
                console.error('Failed to register agent:', error);
                alert('Failed to register agent');
            }
        },
        
        async refreshAgents() {
            try {
                const response = await fetch('/api/agents/list');
                const data = await response.json();
                
                if (data.agents) {
                    this.registeredAgents = data.agents;
                }
            } catch (error) {
                console.error('Failed to refresh agents:', error);
            }
        },
        
        async getAgentStatus(agentId) {
            try {
                const response = await fetch(`/api/agents/${agentId}/status`);
                const data = await response.json();
                
                // Update agent in list
                const index = this.registeredAgents.findIndex(a => a.agent_id === agentId);
                if (index !== -1 && data.status) {
                    this.registeredAgents[index] = {
                        ...this.registeredAgents[index],
                        ...data
                    };
                }
                
                this.agentLogs.unshift({
                    timestamp: new Date().toISOString(),
                    agent_id: agentId,
                    message: `Status: ${data.status} ${data.current_task ? '- Working on: ' + data.current_task.name : ''}`
                });
            } catch (error) {
                console.error('Failed to get agent status:', error);
            }
        },
        
        async requestTaskForAgent(agentId) {
            try {
                const response = await fetch(`/api/agents/${agentId}/request-task`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.task) {
                    this.agentLogs.unshift({
                        timestamp: new Date().toISOString(),
                        agent_id: agentId,
                        message: `Assigned task: ${data.task.name} (${data.task.id})`
                    });
                    
                    // Refresh agent status
                    await this.getAgentStatus(agentId);
                } else {
                    this.agentLogs.unshift({
                        timestamp: new Date().toISOString(),
                        agent_id: agentId,
                        message: data.message || 'No tasks available'
                    });
                }
            } catch (error) {
                console.error('Failed to request task:', error);
            }
        },
        
        async reportProgress() {
            if (!this.taskUpdate.agent_id || !this.taskUpdate.task_id) {
                alert('Please select agent and enter task ID');
                return;
            }
            
            try {
                const response = await fetch('/api/agents/report-progress', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.taskUpdate)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.agentLogs.unshift({
                        timestamp: new Date().toISOString(),
                        agent_id: this.taskUpdate.agent_id,
                        message: `Progress reported: ${this.taskUpdate.status} (${this.taskUpdate.progress}%)`
                    });
                    
                    // Clear form but keep agent selected
                    this.taskUpdate.task_id = '';
                    this.taskUpdate.progress = 0;
                    this.taskUpdate.message = '';
                    
                    // Refresh project status
                    await this.getProjectStatus();
                }
            } catch (error) {
                console.error('Failed to report progress:', error);
            }
        },
        
        async getProjectStatus() {
            try {
                const response = await fetch('/api/agents/project-status');
                const data = await response.json();
                
                if (data.project_state) {
                    this.projectStatus = data.project_state;
                }
            } catch (error) {
                console.error('Failed to get project status:', error);
            }
        },
        
        // Project Management Methods
        async loadSampleProjects() {
            try {
                const response = await fetch('/api/projects/samples');
                const data = await response.json();
                if (data.success) {
                    this.sampleProjects = data.samples;
                }
            } catch (error) {
                console.error('Failed to load sample projects:', error);
            }
        },
        
        loadSampleProject() {
            if (!this.selectedSample) return;
            
            const sample = this.sampleProjects.find(s => s.id === this.selectedSample);
            if (sample) {
                this.newProject.name = sample.name;
                this.newProject.description = sample.description;
            }
        },
        
        async createProject() {
            if (!this.newProject.description) {
                alert('Please provide a project description');
                return;
            }
            
            try {
                const response = await fetch('/api/projects/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newProject)
                });
                
                const data = await response.json();
                if (data.success) {
                    this.currentProject = data.project;
                    if (data.prd_analysis) {
                        this.currentProject.prd_analysis = data.prd_analysis;
                    }
                    
                    // Fetch real-time token-based costs
                    await this.fetchProjectCosts(this.currentProject.id);
                    
                    // Clear form
                    this.newProject = { name: '', description: '' };
                    this.selectedSample = '';
                    
                    // Refresh projects list
                    await this.refreshProjects();
                } else {
                    alert(`Failed to create project: ${data.error}`);
                }
            } catch (error) {
                console.error('Failed to create project:', error);
                alert('Failed to create project');
            }
        },
        
        async addFeature() {
            if (!this.newFeature.title || !this.newFeature.description) {
                alert('Please fill in feature title and description');
                return;
            }
            
            try {
                const feature = {
                    ...this.newFeature,
                    acceptance_criteria: this.newFeature.acceptance_criteria
                        .split(',')
                        .map(c => c.trim())
                        .filter(c => c.length > 0),
                    project_id: this.currentProject.id
                };
                
                const response = await fetch('/api/projects/features/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(feature)
                });
                
                const data = await response.json();
                if (data.success) {
                    this.projectFeatures.push(data.feature);
                    
                    // Clear form
                    this.newFeature = {
                        title: '',
                        description: '',
                        priority: 'medium',
                        acceptance_criteria: ''
                    };
                } else {
                    alert(`Failed to add feature: ${data.error}`);
                }
            } catch (error) {
                console.error('Failed to add feature:', error);
                alert('Failed to add feature');
            }
        },
        
        async removeFeature(featureId) {
            try {
                const response = await fetch(`/api/projects/features/${featureId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                if (data.success) {
                    this.projectFeatures = this.projectFeatures.filter(f => f.id !== featureId);
                }
            } catch (error) {
                console.error('Failed to remove feature:', error);
            }
        },
        
        async startWorkflow() {
            if (!this.currentProject) {
                alert('Please create a project first');
                return;
            }
            
            try {
                const response = await fetch('/api/projects/workflow/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: this.currentProject.id,
                        options: this.workflowOptions
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.currentProject.status = 'running';
                    this.currentProject.flow_id = data.flow_id;
                    
                    // Switch to monitor tab to see the flow
                    this.activeTab = 'monitor';
                    
                    alert(`Workflow started! Flow ID: ${data.flow_id}`);
                } else {
                    alert(`Failed to start workflow: ${data.error}`);
                }
            } catch (error) {
                console.error('Failed to start workflow:', error);
                alert('Failed to start workflow');
            }
        },
        
        async pauseWorkflow() {
            try {
                const response = await fetch('/api/projects/workflow/pause', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: this.currentProject.id
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.currentProject.status = 'paused';
                }
            } catch (error) {
                console.error('Failed to pause workflow:', error);
            }
        },
        
        async stopWorkflow() {
            if (!confirm('Are you sure you want to stop the workflow?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/projects/workflow/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: this.currentProject.id
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    this.currentProject.status = 'stopped';
                }
            } catch (error) {
                console.error('Failed to stop workflow:', error);
            }
        },
        
        async refreshProjects() {
            try {
                const response = await fetch('/api/projects/list');
                const data = await response.json();
                
                if (data.projects) {
                    this.existingProjects = data.projects;
                }
            } catch (error) {
                console.error('Failed to refresh projects:', error);
            }
        },
        
        async selectProject(projectId) {
            try {
                const response = await fetch(`/api/projects/${projectId}`);
                const data = await response.json();
                
                if (data.project) {
                    this.currentProject = data.project;
                    
                    // Calculate estimated cost if we have hours
                    // Fetch real-time costs after creation
                    await this.fetchProjectCosts(this.currentProject.id);
                }
            } catch (error) {
                console.error('Failed to select project:', error);
            }
        },
        
        async viewProjectFlow(projectId) {
            try {
                const response = await fetch(`/api/projects/${projectId}/flow`);
                const data = await response.json();
                
                if (data.flow_id) {
                    this.replayFlowId = data.flow_id;
                    this.activeTab = 'replay';
                    await this.startReplay();
                } else {
                    alert('No flow associated with this project yet');
                }
            } catch (error) {
                console.error('Failed to get project flow:', error);
            }
        }
    }
}).mount('#app');