import { useMemo } from 'react';
import { useVisualizationStore } from '../store/visualizationStore';
import { Message, MessageType } from '../data/mockDataGenerator';
import './ConversationView.css';

const ConversationView = () => {
  const messages = useVisualizationStore((state) => state.getMessagesUpToCurrentTime());
  const data = useVisualizationStore((state) => state.data);
  const selectMessage = useVisualizationStore((state) => state.selectMessage);
  const selectedMessageId = useVisualizationStore((state) => state.selectedMessageId);

  // Group messages by task or general conversation
  const groupedMessages = useMemo(() => {
    const groups: { [key: string]: Message[] } = {
      general: [],
    };

    messages.forEach(msg => {
      if (msg.task_id) {
        if (!groups[msg.task_id]) {
          groups[msg.task_id] = [];
        }
        groups[msg.task_id].push(msg);
      } else {
        groups.general.push(msg);
      }
    });

    return groups;
  }, [messages]);

  const getMessageIcon = (type: MessageType) => {
    switch (type) {
      case MessageType.INSTRUCTION: return '📋';
      case MessageType.QUESTION: return '❓';
      case MessageType.ANSWER: return '✅';
      case MessageType.STATUS_UPDATE: return '📊';
      case MessageType.BLOCKER: return '🚫';
      case MessageType.TASK_REQUEST: return '🙋';
      case MessageType.TASK_ASSIGNMENT: return '📝';
      default: return '💬';
    }
  };

  const getMessageTypeLabel = (type: MessageType) => {
    switch (type) {
      case MessageType.INSTRUCTION: return 'Instruction';
      case MessageType.QUESTION: return 'Question';
      case MessageType.ANSWER: return 'Answer';
      case MessageType.STATUS_UPDATE: return 'Status Update';
      case MessageType.BLOCKER: return 'Blocker';
      case MessageType.TASK_REQUEST: return 'Task Request';
      case MessageType.TASK_ASSIGNMENT: return 'Task Assignment';
      default: return 'Message';
    }
  };

  const getAgentName = (agentId: string) => {
    if (agentId === 'marcus') return 'Marcus';
    const agent = data.agents.find(a => a.id === agentId);
    return agent ? agent.name : agentId;
  };

  const getTaskName = (taskId: string) => {
    const task = data.tasks.find(t => t.id === taskId);
    return task ? task.name : taskId;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const startTime = new Date(data.metadata.start_time);
    const diffMinutes = Math.round((date.getTime() - startTime.getTime()) / 60000);
    return `${diffMinutes}m`;
  };

  return (
    <div className="conversation-view">
      <div className="conversations-container">
        {Object.entries(groupedMessages).map(([taskId, msgs]) => {
          if (msgs.length === 0) return null;

          return (
            <div key={taskId} className="conversation-group">
              <div className="conversation-group-header">
                <h3>
                  {taskId === 'general' ? 'General System Messages' : getTaskName(taskId)}
                </h3>
                <span className="message-count">{msgs.length} messages</span>
              </div>

              <div className="messages-list">
                {msgs.map((msg, idx) => {
                  const isFromMarcus = msg.from === 'marcus';
                  const prevMsg = idx > 0 ? msgs[idx - 1] : null;
                  const isThreaded = msg.parent_message_id === prevMsg?.id;

                  return (
                    <div
                      key={msg.id}
                      className={`message ${isFromMarcus ? 'from-marcus' : 'from-agent'} ${
                        msg.id === selectedMessageId ? 'selected' : ''
                      } ${isThreaded ? 'threaded' : ''}`}
                      onClick={() => selectMessage(msg.id)}
                    >
                      <div className="message-header">
                        <div className="message-sender">
                          <span className="sender-avatar">
                            {isFromMarcus ? '🤖' : '👤'}
                          </span>
                          <span className="sender-name">{getAgentName(msg.from)}</span>
                          <span className="message-arrow">→</span>
                          <span className="receiver-name">{getAgentName(msg.to)}</span>
                        </div>
                        <div className="message-meta">
                          <span className="message-time">{formatTime(msg.timestamp)}</span>
                          <span className="message-type-badge">
                            {getMessageIcon(msg.type)} {getMessageTypeLabel(msg.type)}
                          </span>
                        </div>
                      </div>

                      <div className="message-body">
                        {msg.message}
                      </div>

                      {msg.metadata && Object.keys(msg.metadata).length > 0 && (
                        <div className="message-metadata">
                          {msg.metadata.blocking && (
                            <span className="meta-badge blocking">Blocking</span>
                          )}
                          {msg.metadata.requires_response && (
                            <span className="meta-badge requires-response">Requires Response</span>
                          )}
                          {msg.metadata.progress !== undefined && (
                            <span className="meta-badge progress">Progress: {msg.metadata.progress}%</span>
                          )}
                          {msg.metadata.response_time && (
                            <span className="meta-badge response-time">
                              Response: {msg.metadata.response_time}s
                            </span>
                          )}
                          {msg.metadata.resolves_blocker && (
                            <span className="meta-badge resolves">Resolves Blocker</span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ConversationView;
