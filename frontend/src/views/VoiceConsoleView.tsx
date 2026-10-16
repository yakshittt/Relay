import React, { useState, useEffect, useRef } from 'react';
import { simulateVoice, fetchBolnaSchemas } from '../api';
import {
  Radio,
  Send,
  Terminal,
  Copy,
  Check,
  Code2,
  Loader2,
} from 'lucide-react';

interface Message {
  sender: 'user' | 'agent';
  text: string;
  toolCall?: any;
  time: string;
}

export const VoiceConsoleView: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'agent',
      text: "Hello! I am RELAY, your voice incident response assistant. When a location has a technology problem, describe it in plain English. I'll inspect the evidence from real network probes and recommend a safe fix.",
      time: new Date().toLocaleTimeString(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [agentState, setAgentState] = useState<'IDLE' | 'PROCESSING' | 'SPEAKING'>('IDLE');
  const [bolnaSchemas, setBolnaSchemas] = useState<any | null>(null);
  const [showSchemas, setShowSchemas] = useState(false);
  const [copied, setCopied] = useState(false);
  const [lastIncidentId, setLastIncidentId] = useState<number | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchBolnaSchemas()
      .then((res) => setBolnaSchemas(res.tools))
      .catch((err) => console.error('Failed to load Bolna schemas', err));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentState]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || agentState !== 'IDLE') return;

    const userMsg: Message = {
      sender: 'user',
      text,
      time: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setAgentState('PROCESSING');

    try {
      const res = await simulateVoice(text, 'jio-lab', lastIncidentId);
      if (res.incident_id) {
        setLastIncidentId(res.incident_id);
      }

      setAgentState('SPEAKING');

      // Speech synthesis if available in browser
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(res.spoken_response);
        utterance.rate = 1.05;
        utterance.onend = () => setAgentState('IDLE');
        window.speechSynthesis.speak(utterance);
      } else {
        setTimeout(() => setAgentState('IDLE'), 2000);
      }

      const agentMsg: Message = {
        sender: 'agent',
        text: res.spoken_response,
        toolCall: res.tool_call,
        time: new Date().toLocaleTimeString(),
      };

      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: `Diagnostic execution failed: ${err.message}`,
          time: new Date().toLocaleTimeString(),
        },
      ]);
      setAgentState('IDLE');
    }
  };

  const handleCopySchemas = () => {
    if (!bolnaSchemas) return;
    navigator.clipboard.writeText(JSON.stringify(bolnaSchemas, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const samplePrompts = [
    'The billing application is not loading.',
    'Is the Jio router gateway reachable?',
    'What is the current health of the site?',
    'Yes, I approve the recovery action.',
  ];

  return (
    <div>
      {/* Header */}
      <div className="section-header">
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={20} style={{ color: 'var(--accent-indigo)' }} />
            Voice AI Operations Console (Bolna Integration)
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.84rem' }}>
            Voice-first incident reporting. Understands problems, collects real probe evidence, and requests authorization before taking disruptive action.
          </p>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={() => setShowSchemas(!showSchemas)}>
          <Code2 size={14} />
          {showSchemas ? 'Hide Bolna Schemas' : 'View Bolna Tool JSON'}
        </button>
      </div>

      {/* Bolna Schema Drawer */}
      {showSchemas && (
        <div className="card" style={{ backgroundColor: 'var(--bg-input)', border: '1px solid var(--accent-indigo)' }}>
          <div className="card-header">
            <div className="card-title">
              <Terminal size={16} style={{ color: 'var(--accent-indigo)' }} />
              Bolna Custom Function Tool Schemas (Ready to Paste)
            </div>
            <button className="btn btn-secondary btn-sm" onClick={handleCopySchemas}>
              {copied ? <Check size={14} style={{ color: 'var(--status-healthy)' }} /> : <Copy size={14} />}
              {copied ? 'Copied JSON!' : 'Copy Schemas'}
            </button>
          </div>
          <pre
            style={{
              maxHeight: 240,
              overflowY: 'auto',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              padding: '12px',
              backgroundColor: '#05070c',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            {JSON.stringify(bolnaSchemas, null, 2)}
          </pre>
        </div>
      )}

      {/* Main Console Box */}
      <div className="card" style={{ minHeight: '520px', display: 'flex', flexDirection: 'column' }}>
        {/* Agent Status Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '12px',
            marginBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor:
                  agentState === 'SPEAKING'
                    ? 'var(--accent-indigo)'
                    : agentState === 'PROCESSING'
                    ? 'var(--status-degraded)'
                    : 'var(--status-healthy)',
                boxShadow: agentState !== 'IDLE' ? '0 0 10px var(--accent-indigo)' : 'none',
              }}
            />
            <span style={{ fontWeight: 600, fontSize: '0.86rem' }}>
              Agent State: <strong style={{ color: 'var(--text-primary)' }}>{agentState}</strong>
            </span>
          </div>

          {/* Visualizer bars */}
          {agentState !== 'IDLE' && (
            <div className="visualizer-container">
              <div className="wave-bar" />
              <div className="wave-bar" />
              <div className="wave-bar" />
              <div className="wave-bar" />
              <div className="wave-bar" />
              <div className="wave-bar" />
              <div className="wave-bar" />
            </div>
          )}
        </div>

        {/* Conversation Stream */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '75%',
                  backgroundColor: msg.sender === 'user' ? 'var(--accent-blue)' : 'var(--bg-card-subtle)',
                  color: '#fff',
                  border: msg.sender === 'user' ? 'none' : '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '12px 16px',
                  fontSize: '0.9rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '4px', fontSize: '0.72rem', color: msg.sender === 'user' ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}>
                  <strong>{msg.sender === 'user' ? 'OPERATOR' : 'RELAY VOICE AGENT'}</strong>
                  <span>{msg.time}</span>
                </div>
                <div>{msg.text}</div>

                {/* Tool Invocation Trace */}
                {msg.toolCall && (
                  <div
                    style={{
                      marginTop: '10px',
                      padding: '8px 12px',
                      backgroundColor: 'rgba(0,0,0,0.3)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.75rem',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ color: 'var(--accent-purple)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Terminal size={12} />
                      Tool Executed: {msg.toolCall.name}
                    </div>
                    <div className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginTop: '2px' }}>
                      params: {JSON.stringify(msg.toolCall.parameters)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Sample Voice Inputs */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
          {samplePrompts.map((prompt, i) => (
            <button
              key={i}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.75rem', padding: '4px 8px' }}
              onClick={() => handleSendMessage(prompt)}
              disabled={agentState !== 'IDLE'}
            >
              "{prompt}"
            </button>
          ))}
        </div>

        {/* Message Input Box */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            className="input"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message or voice query..."
            disabled={agentState !== 'IDLE'}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSendMessage()}
            disabled={agentState !== 'IDLE' || !inputText.trim()}
          >
            {agentState === 'PROCESSING' ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
