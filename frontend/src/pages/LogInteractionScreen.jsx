import React, { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  MessageSquare,
  FileText,
  History,
  Save,
  Check,
  Edit3,
  Plus,
  Trash2,
  Calendar,
  Mic,
  Send,
  Info,
  RefreshCw,
  Sun,
  Moon
} from 'lucide-react';
import {
  fetchHCPs,
  fetchProducts,
  fetchInteractions,
  fetchAuditLogs,
  setView
} from '../features/interactions/interactionsSlice';
import {
  sendChatMessage,
  addChatMessage,
  confirmChatDraft
} from '../features/chat/chatSlice';

export default function LogInteractionScreen() {
  const dispatch = useDispatch();

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('crm-theme') || 'dark';
  });

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
    localStorage.setItem('crm-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const getSplitDateTime = (isoString) => {
    if (!isoString) return { date: '', time: '' };
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return { date: '', time: '' };
      const pad = (num) => String(num).padStart(2, '0');
      const datePart = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
      const timePart = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
      return { date: datePart, time: timePart };
    } catch {
      return { date: '', time: '' };
    }
  };

  const {
    hcps,
    products,
    interactions,
    auditLogs,
    activeView
  } = useSelector((state) => state.interactions);

  const {
    chatHistory,
    chatLoading
  } = useSelector((state) => state.chat);

  const [chatInput, setChatInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTimeout, setRecordingTimeout] = useState(null);
  
  // Local state for inline-editing preview cards
  const [editingCardId, setEditingCardId] = useState(null);
  const [editingCardData, setEditingCardData] = useState(null);
  const [expandedAudits, setExpandedAudits] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Derive the active draft from the latest chat message that has a preview card
  const latestMessageWithCard = [...chatHistory].reverse().find(m => m.preview_card);
  let activeDraft = latestMessageWithCard ? latestMessageWithCard.preview_card : null;

  // Sync activeDraft with inline card edits in real-time
  if (editingCardId && editingCardData && activeDraft) {
    activeDraft = {
      ...activeDraft,
      ...editingCardData,
      products: products.filter(p => editingCardData.product_ids.includes(p.id)).map(p => p.name),
      samples: editingCardData.samples
    };
  }

  
  // Searchable HCP Dropdown states (Inline Card Edit mode)
  const [cardHcpSearchText, setCardHcpSearchText] = useState('');
  const [isCardHcpDropdownOpen, setIsCardHcpDropdownOpen] = useState(false);
  const cardDropdownRef = useRef(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    dispatch(fetchHCPs());
    dispatch(fetchProducts());
    dispatch(fetchInteractions());
  }, [dispatch]);

  // Click outside to close searchable dropdowns
  useEffect(() => {
    function handleClickOutside(event) {
      if (cardDropdownRef.current && !cardDropdownRef.current.contains(event.target)) {
        setIsCardHcpDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, chatLoading]);

  const handleSendChat = (textToSend) => {
    const text = textToSend || chatInput;
    if (!text.trim()) return;

    const userMsg = {
      id: Date.now().toString(),
      sender: 'user',
      text: text,
      timestamp: new Date().toISOString()
    };
    dispatch(addChatMessage(userMsg));
    setChatInput('');

    const apiHistory = chatHistory.map(m => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text
    }));

    dispatch(sendChatMessage({ message: text, history: apiHistory }));
  };

  const handleToggleMic = () => {
    if (isRecording) {
      setIsRecording(false);
      if (recordingTimeout) clearTimeout(recordingTimeout);
    } else {
      setIsRecording(true);
      const timeout = setTimeout(() => {
        setIsRecording(false);
        setChatInput(
          "Met Dr. Ananya Sharma today, we discussed CardioX and she asked for more trial data. Sentiment was very positive. I gave her 3 boxes of CardioX and scheduled a follow up in 2 weeks to review results."
        );
      }, 3000);
      setRecordingTimeout(timeout);
    }
  };


  // Confirm chat draft by posting to /api/chat/confirm
  const handleConfirmPreview = (previewCard) => {
    if (!previewCard.hcp_id) {
      showToast("HCP must be resolved before confirmation.", "error");
      return;
    }

    dispatch(confirmChatDraft({ previewCard, sessionId: 'default' })).then((res) => {
      if (!res.error) {
        showToast("Interaction confirmed and logged successfully!", "success");
        dispatch(setView('history'));
      }
    });
  };

  const handleStartEditCard = (msgId, card) => {
    setEditingCardId(msgId);
    setEditingCardData({
      ...card,
      product_ids: products.filter(p => card.products.includes(p.name)).map(p => p.id),
      samples: card.samples.map(s => ({ ...s }))
    });
    setCardHcpSearchText(card.hcp_name || '');
  };

  const handleInlineCardFieldChange = (fields) => {
    setEditingCardData(prev => ({ ...prev, ...fields }));
  };

  const handleInlineAddSample = () => {
    const available = products.find(p => !editingCardData.samples.some(s => s.product_id === p.id));
    if (!available) return;
    setEditingCardData(prev => ({
      ...prev,
      samples: [...prev.samples, { product_id: available.id, product_name: available.name, quantity: 1 }]
    }));
  };

  const handleInlineRemoveSample = (index) => {
    setEditingCardData(prev => ({
      ...prev,
      samples: prev.samples.filter((_, i) => i !== index)
    }));
  };

  const handleInlineSampleChange = (index, field, value) => {
    const updated = editingCardData.samples.map((s, i) => {
      if (i === index) {
        if (field === 'product_id') {
          const matched = products.find(p => p.id === parseInt(value));
          return { ...s, product_id: matched.id, product_name: matched.name };
        }
        return { ...s, [field]: parseInt(value) || value };
      }
      return s;
    });
    setEditingCardData(prev => ({ ...prev, samples: updated }));
  };

  const handleInlineProductToggle = (productId) => {
    const current = editingCardData.product_ids;
    let next;
    if (current.includes(productId)) {
      next = current.filter(id => id !== productId);
    } else {
      next = [...current, productId];
    }
    
    setEditingCardData(prev => ({
      ...prev,
      product_ids: next,
      products: products.filter(p => next.includes(p.id)).map(p => p.name)
    }));
  };

  const handleSaveInlineCardEdits = (msgId) => {
    const baseCard = chatHistory.find(m => m.id === msgId)?.preview_card;
    if (!baseCard) return;

    const metaFields = { ...baseCard.metadata_fields };
    const checkFieldEdit = (fieldName, newVal, oldVal) => {
      if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
        metaFields[fieldName] = { source: 'manual', confidence: 1.0 };
      }
    };

    checkFieldEdit('hcp_id', editingCardData.hcp_id, baseCard.hcp_id);
    checkFieldEdit('type', editingCardData.type, baseCard.type);
    checkFieldEdit('sentiment', editingCardData.sentiment, baseCard.sentiment);
    checkFieldEdit('discussion_notes', editingCardData.discussion_notes, baseCard.discussion_notes);
    checkFieldEdit('product_ids', editingCardData.product_ids, products.filter(p => baseCard.products.includes(p.name)).map(p => p.id));
    checkFieldEdit('samples', editingCardData.samples, baseCard.samples);
    checkFieldEdit('follow_up_required', editingCardData.follow_up_required, baseCard.follow_up_required);
    checkFieldEdit('follow_up_date', editingCardData.follow_up_date, baseCard.follow_up_date);
    checkFieldEdit('follow_up_notes', editingCardData.follow_up_notes, baseCard.follow_up_notes);
    checkFieldEdit('attendees', editingCardData.attendees, baseCard.attendees);
    checkFieldEdit('materials_shared', editingCardData.materials_shared, baseCard.materials_shared);

    const finalCard = {
      ...editingCardData,
      metadata_fields: metaFields,
      is_edit_operation: editingCardData.is_edit_operation,
      target_interaction_id: editingCardData.target_interaction_id
    };
    
    setEditingCardId(null);
    setEditingCardData(null);
    handleConfirmPreview(finalCard);
  };

  const handleToggleAudit = (id) => {
    const isExpanded = !!expandedAudits[id];
    setExpandedAudits(prev => ({ ...prev, [id]: !isExpanded }));
    if (!isExpanded) {
      dispatch(fetchAuditLogs(id));
    }
  };

  const filteredInteractions = interactions.filter(i => {
    const q = searchTerm.toLowerCase();
    return (
      (i.hcp && i.hcp.name.toLowerCase().includes(q)) ||
      (i.discussion_notes && i.discussion_notes.toLowerCase().includes(q)) ||
      (i.products && i.products.some(p => p.name.toLowerCase().includes(q)))
    );
  });

  const totalInteractions = interactions.length;
  const positiveSentimentCount = interactions.filter(i => i.sentiment === 'Positive').length;
  const positiveSentimentPct = totalInteractions ? Math.round((positiveSentimentCount / totalInteractions) * 100) : 0;
  const totalSamplesGiven = interactions.reduce((acc, i) => acc + (i.samples ? i.samples.reduce((sum, s) => sum + s.quantity, 0) : 0), 0);
  const pendingFollowups = interactions.filter(i => i.follow_up_required && (!i.follow_up_date || new Date(i.follow_up_date) >= new Date())).length;

  return (
    <div className="app-container">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">L</div>
          <div className="brand-text">LogCRM AI</div>
        </div>

        <nav className="nav-menu">
          <li
            className={`nav-item ${activeView === 'log' ? 'active' : ''}`}
            onClick={() => dispatch(setView('log'))}
          >
            <MessageSquare size={18} />
            Log Interaction
          </li>
          <li
            className={`nav-item ${activeView === 'history' ? 'active' : ''}`}
            onClick={() => dispatch(setView('history'))}
          >
            <History size={18} />
            Visit History & Logs
          </li>
        </nav>

        <div className="sidebar-footer">
          <p>© 2026 LogCRM Portal</p>
          <p style={{ fontSize: '0.7rem', marginTop: '4px' }}>AI-First Logging Engine</p>
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-content">
        <header className="top-nav">
          <h2 className="page-title">
            {activeView === 'log' ? 'Log Interaction' : 'CRM Audit & Visit Logs'}
          </h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {activeView === 'log' && (
              <span className="badge badge-ai" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                AI-Assisted Split Mode
              </span>
            )}

            <button
              type="button"
              className="btn btn-secondary"
              onClick={toggleTheme}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                border: '1px solid var(--surface-border)',
                background: 'var(--surface-color)',
                transition: 'var(--transition-smooth)',
                color: 'var(--text-primary)'
              }}
              title="Toggle Dark/Light Mode"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <div className="pane-container" style={activeView === 'log' ? {
          display: 'grid',
          gridTemplateColumns: '1.1fr 0.9fr',
          gap: '30px',
          height: 'calc(100vh - 70px)',
          padding: '24px 40px',
          overflow: 'hidden'
        } : {}}>
          {activeView === 'log' ? (
            <>
              {/* Left Side: Interaction Details Panel containing a Form */}
              <div style={{ overflowY: 'auto', paddingRight: '12px', height: '100%' }}>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '20px' }}>Log HCP Interaction</h3>
                
                <form className="form-pane" style={{ maxWidth: '100%', margin: 0, padding: '20px' }} onSubmit={(e) => e.preventDefault()}>
                  <div className="form-info-banner" style={{
                    background: 'rgba(139, 92, 246, 0.08)',
                    border: '1px solid rgba(139, 92, 246, 0.2)',
                    borderRadius: 'var(--rounded-md)',
                    padding: '12px 16px',
                    marginBottom: '20px',
                    fontSize: '0.85rem',
                    color: 'var(--primary-color)',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Info size={16} />
                    <span>This form is controlled by the AI Assistant on the right. Write in the chat to fill out or modify these fields.</span>
                  </div>

                  <div className="form-grid">
                    {/* HCP Field */}
                    <div className="form-group">
                      <label>HCP Name</label>
                      <input
                        type="text"
                        placeholder="Search or select HCP..."
                        value={activeDraft ? activeDraft.hcp_name || '' : ''}
                        disabled
                        style={{ opacity: 0.85, cursor: 'not-allowed' }}
                      />
                    </div>

                    {/* Interaction Type */}
                    <div className="form-group">
                      <label>Interaction Type</label>
                      <select
                        value={activeDraft ? activeDraft.type || 'Meeting' : 'Meeting'}
                        disabled
                        style={{ opacity: 0.85, cursor: 'not-allowed' }}
                      >
                        <option value="Meeting">Meeting</option>
                        <option value="Visit">Visit</option>
                        <option value="Call">Call</option>
                        <option value="Email">Email</option>
                        <option value="Sample Drop">Sample Drop</option>
                        <option value="Conference">Conference</option>
                      </select>
                    </div>

                    {/* Date and Time split */}
                    {(() => {
                      const { date: splitDate, time: splitTime } = getSplitDateTime(activeDraft?.datetime);
                      return (
                        <>
                          <div className="form-group">
                            <label>Date</label>
                            <input
                              type="date"
                              value={splitDate}
                              disabled
                              style={{ opacity: 0.85, cursor: 'not-allowed' }}
                            />
                          </div>

                          <div className="form-group">
                            <label>Time</label>
                            <input
                              type="time"
                              value={splitTime}
                              disabled
                              style={{ opacity: 0.85, cursor: 'not-allowed' }}
                            />
                          </div>
                        </>
                      );
                    })()}

                    {/* Attendees */}
                    <div className="form-group full-width">
                      <label>Attendees</label>
                      <input
                        type="text"
                        placeholder="Enter names or search..."
                        value={activeDraft ? activeDraft.attendees || '' : ''}
                        disabled
                        style={{ opacity: 0.85, cursor: 'not-allowed' }}
                      />
                    </div>

                    {/* Topics Discussed */}
                    <div className="form-group full-width">
                      <label>Topics Discussed</label>
                      <textarea
                        placeholder="Enter key discussion points..."
                        value={activeDraft ? activeDraft.discussion_notes || '' : ''}
                        disabled
                        style={{ opacity: 0.85, cursor: 'not-allowed', minHeight: '80px' }}
                      />
                    </div>
                  </div>

                  {/* Voice note simulation */}
                  <div 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '8px', 
                      color: 'var(--primary-color)', 
                      fontSize: '0.85rem', 
                      cursor: 'pointer', 
                      margin: '12px 0 20px 0' 
                    }} 
                    onClick={handleToggleMic}
                  >
                    <Mic size={16} className={isRecording ? 'recording-icon-spin' : ''} />
                    <span style={{ textDecoration: 'underline', fontWeight: 500 }}>
                      {isRecording ? 'Listening... click to stop' : 'Summarize from Voice Note (Requires Consent)'}
                    </span>
                  </div>

                  {/* Materials Shared / Samples Distributed */}
                  <div style={{ borderTop: '1px solid var(--surface-border)', paddingTop: '20px', marginTop: '20px' }}>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                      Materials Shared / Samples Distributed
                    </h4>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                          Materials Shared
                        </label>
                        <div style={{ 
                          padding: '10px 14px', 
                          background: 'var(--surface-color)', 
                          border: '1px solid var(--surface-border)', 
                          borderRadius: 'var(--rounded-md)', 
                          minHeight: '38px', 
                          fontSize: '0.85rem',
                          color: 'var(--text-primary)'
                        }}>
                          {activeDraft && activeDraft.materials_shared ? activeDraft.materials_shared : "No materials added."}
                        </div>
                      </div>
                      
                      <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                          Samples Distributed
                        </label>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {activeDraft && activeDraft.samples && activeDraft.samples.length > 0 ? (
                            activeDraft.samples.map((sample, idx) => (
                              <div key={idx} style={{ 
                                padding: '8px 12px', 
                                background: 'var(--surface-color)', 
                                border: '1px solid var(--surface-border)', 
                                borderRadius: 'var(--rounded-md)', 
                                fontSize: '0.85rem', 
                                display: 'flex', 
                                justifyContent: 'space-between',
                                color: 'var(--text-primary)'
                              }}>
                                <span>{sample.product_name || sample.product?.name}</span>
                                <span style={{ fontWeight: 600 }}>x{sample.quantity}</span>
                              </div>
                            ))
                          ) : (
                            <div style={{ 
                              padding: '10px 14px', 
                              background: 'var(--surface-color)', 
                              border: '1px solid var(--surface-border)', 
                              borderRadius: 'var(--rounded-md)', 
                              minHeight: '38px', 
                              fontSize: '0.85rem', 
                              color: 'var(--text-muted)', 
                              fontStyle: 'italic' 
                            }}>
                              No samples distributed.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Follow-up Section if requested by AI */}
                  {activeDraft && activeDraft.follow_up_required && (
                    <div className="followup-card" style={{ marginTop: '20px' }}>
                      <div className="followup-header" style={{ cursor: 'not-allowed' }}>
                        <input
                          type="checkbox"
                          checked={true}
                          disabled
                        />
                        <label>Follow-up Required (AI Drafted)</label>
                      </div>

                      <div className="form-grid" style={{ marginBottom: 0 }}>
                        <div className="form-group">
                          <label>Follow-up Date</label>
                          <input
                            type="date"
                            value={activeDraft.follow_up_date || ''}
                            disabled
                            style={{ opacity: 0.85, cursor: 'not-allowed' }}
                          />
                        </div>
                        <div className="form-group">
                          <label>Follow-up Notes</label>
                          <input
                            type="text"
                            value={activeDraft.follow_up_notes || ''}
                            disabled
                            style={{ opacity: 0.85, cursor: 'not-allowed' }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: '24px' }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={!activeDraft || !activeDraft.hcp_id}
                      onClick={() => handleConfirmPreview(activeDraft)}
                      style={{ width: '100%', justifyContent: 'center', height: '48px' }}
                    >
                      <Save size={16} /> Confirm & Save Interaction
                    </button>
                  </div>
                </form>
              </div>

              {/* Right Side: AI Assistant Chat Panel */}
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
                <div className="chat-pane" style={{ maxWidth: '100%', margin: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <div className="chat-history" style={{ flex: 1 }}>
                    {chatHistory.map((msg) => (
                      <div key={msg.id} className={`message-bubble ${msg.sender}`}>
                        <span className="message-sender">
                          {msg.sender === 'user' ? 'You' : 'CRM Assistant'}
                        </span>
                        <div className="message-text">
                          {msg.text}
                        </div>

                        {/* Disambiguation Option */}
                        {msg.needs_disambiguation && msg.disambiguation_options && (
                          <div className="disambiguation-box">
                            {msg.disambiguation_options.map((opt) => (
                              <div
                                key={opt.id}
                                className="disambiguation-option"
                                onClick={() => handleSendChat(`Confirming ${opt.name} (${opt.specialty})`)}
                              >
                                <div>
                                  <span className="disambiguation-option-name">{opt.name}</span>
                                  <span className="disambiguation-option-spec"> — {opt.specialty}</span>
                                </div>
                                <Plus size={16} />
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Preview Card */}
                        {msg.preview_card && (
                          <div className="preview-card-container">
                            <div className="preview-card-header">
                              <div className="preview-card-title">
                                <FileText size={18} className="text-violet-400" />
                                <span>Preview Interaction Card</span>
                                {msg.preview_card.is_edit_operation && (
                                  <span className="badge badge-ai" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                                    PROPOSED EDIT
                                  </span>
                                )}
                              </div>
                              <span className="badge badge-ai">AI-Extracted Draft</span>
                            </div>

                            {editingCardId === msg.id ? (
                              /* Inline Edit Mode */
                              <div className="preview-card-body">
                                <div className="preview-row" style={{ position: 'relative' }} ref={cardDropdownRef}>
                                  <span className="preview-label">HCP</span>
                                  <div className="preview-val" style={{ width: '100%' }}>
                                    <input
                                      type="text"
                                      placeholder="Search HCP name..."
                                      value={cardHcpSearchText}
                                      onChange={(e) => {
                                        setCardHcpSearchText(e.target.value);
                                        setIsCardHcpDropdownOpen(true);
                                      }}
                                      onFocus={() => setIsCardHcpDropdownOpen(true)}
                                      style={{ width: '100%', padding: '6px' }}
                                    />
                                    {isCardHcpDropdownOpen && (
                                      <div
                                        style={{
                                          position: 'absolute',
                                          top: '100%',
                                          left: '140px',
                                          right: 0,
                                          backgroundColor: 'var(--preview-card-bg)',
                                          border: '1px solid var(--surface-border)',
                                          borderRadius: 'var(--rounded-md)',
                                          maxHeight: '150px',
                                          overflowY: 'auto',
                                          zIndex: 60,
                                          boxShadow: 'var(--preview-card-shadow)',
                                          marginTop: '2px'
                                        }}
                                      >
                                        {hcps
                                          .filter(h => h.name.toLowerCase().includes(cardHcpSearchText.toLowerCase()))
                                          .map(h => (
                                            <div
                                              key={h.id}
                                              onClick={() => {
                                                handleInlineCardFieldChange({ hcp_id: h.id, hcp_name: h.name });
                                                setCardHcpSearchText(h.name);
                                                setIsCardHcpDropdownOpen(false);
                                              }}
                                              style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--surface-border)' }}
                                              onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(139, 92, 246, 0.12)'}
                                              onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                                            >
                                              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{h.name}</div>
                                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{h.specialty}</div>
                                            </div>
                                          ))}
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Type</span>
                                  <div className="preview-val">
                                    <select
                                      value={editingCardData.type || 'Visit'}
                                      onChange={(e) => handleInlineCardFieldChange({ type: e.target.value })}
                                      style={{ width: '100%', padding: '6px' }}
                                    >
                                      <option value="Visit">Visit</option>
                                      <option value="Call">Call</option>
                                      <option value="Email">Email</option>
                                      <option value="Sample Drop">Sample Drop</option>
                                      <option value="Conference">Conference</option>
                                    </select>
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Sentiment</span>
                                  <div className="preview-val">
                                    <select
                                      value={editingCardData.sentiment || 'Neutral'}
                                      onChange={(e) => handleInlineCardFieldChange({ sentiment: e.target.value })}
                                      style={{ width: '100%', padding: '6px' }}
                                    >
                                      <option value="Positive">Positive</option>
                                      <option value="Neutral">Neutral</option>
                                      <option value="Negative">Negative</option>
                                    </select>
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Products</span>
                                  <div className="preview-val" style={{ gap: '4px' }}>
                                    {products.map(p => {
                                      const isSelected = editingCardData.product_ids.includes(p.id);
                                      return (
                                        <span
                                          key={p.id}
                                          className={`product-option-pill ${isSelected ? 'selected' : ''}`}
                                          onClick={() => handleInlineProductToggle(p.id)}
                                          style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                                        >
                                          {p.name}
                                        </span>
                                      );
                                    })}
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Samples</span>
                                  <div className="preview-val" style={{ flexDirection: 'column', width: '100%', alignItems: 'stretch' }}>
                                    {editingCardData.samples.map((s, idx) => (
                                      <div key={idx} className="sample-row" style={{ marginBottom: '6px' }}>
                                        <select
                                          value={s.product_id}
                                          onChange={(e) => handleInlineSampleChange(idx, 'product_id', e.target.value)}
                                          style={{ padding: '4px' }}
                                        >
                                          {products.map(p => (
                                            <option key={p.id} value={p.id}>{p.name}</option>
                                          ))}
                                        </select>
                                        <input
                                          type="number"
                                          min="1"
                                          value={s.quantity}
                                          onChange={(e) => handleInlineSampleChange(idx, 'quantity', e.target.value)}
                                          style={{ padding: '4px' }}
                                        />
                                        <button
                                          type="button"
                                          className="btn btn-secondary"
                                          onClick={() => handleInlineRemoveSample(idx)}
                                          style={{ padding: '6px' }}
                                        >
                                          <Trash2 size={14} />
                                        </button>
                                      </div>
                                    ))}
                                    <button
                                      type="button"
                                      className="btn btn-secondary"
                                      onClick={handleInlineAddSample}
                                      style={{ padding: '4px 10px', fontSize: '0.8rem', alignSelf: 'flex-start' }}
                                    >
                                      <Plus size={14} /> Add Sample
                                    </button>
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Notes</span>
                                  <div className="preview-val">
                                    <textarea
                                      value={editingCardData.discussion_notes || ''}
                                      onChange={(e) => handleInlineCardFieldChange({ discussion_notes: e.target.value })}
                                      style={{ width: '100%', minHeight: '60px', padding: '6px' }}
                                    />
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Attendees</span>
                                  <div className="preview-val">
                                    <input
                                      type="text"
                                      value={editingCardData.attendees || ''}
                                      onChange={(e) => handleInlineCardFieldChange({ attendees: e.target.value })}
                                      placeholder="Attendees"
                                      style={{ width: '100%', padding: '6px' }}
                                    />
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Materials</span>
                                  <div className="preview-val">
                                    <input
                                      type="text"
                                      value={editingCardData.materials_shared || ''}
                                      onChange={(e) => handleInlineCardFieldChange({ materials_shared: e.target.value })}
                                      placeholder="Materials shared (e.g. brochures)"
                                      style={{ width: '100%', padding: '6px' }}
                                    />
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Follow-up</span>
                                  <div className="preview-val" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginBottom: '8px' }}>
                                      <input
                                        type="checkbox"
                                        checked={editingCardData.follow_up_required}
                                        onChange={(e) => handleInlineCardFieldChange({ follow_up_required: e.target.checked })}
                                      />
                                      Required
                                    </label>
                                    {editingCardData.follow_up_required && (
                                      <>
                                        <input
                                          type="date"
                                          value={editingCardData.follow_up_date || ''}
                                          onChange={(e) => handleInlineCardFieldChange({ follow_up_date: e.target.value })}
                                          style={{ padding: '6px', marginBottom: '8px' }}
                                        />
                                        <input
                                          type="text"
                                          placeholder="Follow-up notes"
                                          value={editingCardData.follow_up_notes || ''}
                                          onChange={(e) => handleInlineCardFieldChange({ follow_up_notes: e.target.value })}
                                          style={{ padding: '6px' }}
                                        />
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ) : (
                              /* Read-only Mode */
                              <div className="preview-card-body">
                                <div className="preview-row">
                                  <span className="preview-label">HCP</span>
                                  <div className="preview-val">
                                    <span style={{ fontWeight: 600 }}>{msg.preview_card.hcp_name || 'Unresolved HCP'}</span>
                                    {msg.preview_card.metadata_fields?.hcp_id?.source === 'ai' && (
                                      <div className="ai-tooltip">AI {Math.round(msg.preview_card.metadata_fields.hcp_id.confidence * 100)}%</div>
                                    )}
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Type</span>
                                  <div className="preview-val">
                                    <span>{msg.preview_card.type}</span>
                                    {msg.preview_card.metadata_fields?.type?.source === 'ai' && (
                                      <div className="ai-tooltip">AI {Math.round(msg.preview_card.metadata_fields.type.confidence * 100)}%</div>
                                    )}
                                  </div>
                                </div>

                                <div className="preview-row">
                                  <span className="preview-label">Sentiment</span>
                                  <div className="preview-val">
                                    <span className={`badge badge-sentiment-${msg.preview_card.sentiment?.toLowerCase() || 'neutral'}`}>
                                      {msg.preview_card.sentiment || 'Neutral'}
                                    </span>
                                    {msg.preview_card.metadata_fields?.sentiment?.source === 'ai' && (
                                      <div className="ai-tooltip">AI {Math.round(msg.preview_card.metadata_fields.sentiment.confidence * 100)}%</div>
                                    )}
                                  </div>
                                </div>

                                {msg.preview_card.products && msg.preview_card.products.length > 0 && (
                                  <div className="preview-row">
                                    <span className="preview-label">Products</span>
                                    <div className="preview-val">
                                      {msg.preview_card.products.map((p, idx) => (
                                        <span key={idx} className="product-tag">{p}</span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {msg.preview_card.samples && msg.preview_card.samples.length > 0 && (
                                  <div className="preview-row">
                                    <span className="preview-label">Samples</span>
                                    <div className="preview-val">
                                      {msg.preview_card.samples.map((s, idx) => (
                                        <span key={idx} className="sample-tag">{s.product_name || s.product?.name} (x{s.quantity})</span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                <div className="preview-row">
                                  <span className="preview-label">Notes</span>
                                  <div className="preview-val">
                                    <p style={{ fontSize: '0.9rem', opacity: 0.95 }}>{msg.preview_card.discussion_notes}</p>
                                  </div>
                                </div>

                                {msg.preview_card.attendees && (
                                  <div className="preview-row">
                                    <span className="preview-label">Attendees</span>
                                    <div className="preview-val">
                                      <span>{msg.preview_card.attendees}</span>
                                      {msg.preview_card.metadata_fields?.attendees?.source === 'ai' && (
                                        <span className="ai-tooltip">AI {Math.round(msg.preview_card.metadata_fields.attendees.confidence * 100)}%</span>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {msg.preview_card.materials_shared && (
                                  <div className="preview-row">
                                    <span className="preview-label">Materials</span>
                                    <div className="preview-val">
                                      <span>{msg.preview_card.materials_shared}</span>
                                      {msg.preview_card.metadata_fields?.materials_shared?.source === 'ai' && (
                                        <span className="ai-tooltip">AI {Math.round(msg.preview_card.metadata_fields.materials_shared.confidence * 100)}%</span>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {msg.preview_card.follow_up_required && (
                                  <div className="preview-row">
                                    <span className="preview-label">Follow-up</span>
                                    <div className="preview-val" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                                      <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                                        Date: {msg.preview_card.follow_up_date || 'TBD'}
                                      </span>
                                      <span style={{ fontSize: '0.85rem', opacity: 0.8 }}>
                                        {msg.preview_card.follow_up_notes}
                                      </span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            <div className="preview-card-actions">
                              {editingCardId === msg.id ? (
                                <>
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => {
                                      setEditingCardId(null);
                                      setEditingCardData(null);
                                    }}
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn-success"
                                    onClick={() => handleSaveInlineCardEdits(msg.id)}
                                  >
                                    <Check size={16} /> Confirm Edits
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => handleStartEditCard(msg.id, msg.preview_card)}
                                  >
                                    <Edit3 size={16} /> Edit Details
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={() => handleConfirmPreview(msg.preview_card)}
                                  >
                                    <Check size={16} /> Save & Log
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="chat-loading-bubble">
                        <div className="dot-pulse" />
                        <div className="dot-pulse" />
                        <div className="dot-pulse" />
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  <div className="chat-input-bar">
                    <button
                      type="button"
                      className={`microphone-btn ${isRecording ? 'recording' : ''}`}
                      onClick={handleToggleMic}
                      title="Simulate Voice-to-Text Recording"
                    >
                      <Mic size={20} />
                    </button>
                    <input
                      type="text"
                      className="chat-textarea"
                      placeholder="Describe your visit (e.g. 'Called Dr. Sharma, positive, discussed CardioX...')"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                      disabled={chatLoading}
                    />
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{ height: '48px', width: '48px', padding: 0, justifyContent: 'center' }}
                      onClick={() => handleSendChat()}
                      disabled={chatLoading || !chatInput.trim()}
                    >
                      <Send size={18} />
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            /* History & Dashboard View */
            <div className="history-pane">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
                <div className="form-pane" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Total Visits
                  </span>
                  <span style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--primary-color)' }}>
                    {totalInteractions}
                  </span>
                </div>
                <div className="form-pane" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Positive Sentiment %
                  </span>
                  <span style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>
                    {positiveSentimentPct}%
                  </span>
                </div>
                <div className="form-pane" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Samples Distributed
                  </span>
                  <span style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f59e0b' }}>
                    {totalSamplesGiven}
                  </span>
                </div>
                <div className="form-pane" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                    Follow-ups Pending
                  </span>
                  <span style={{ fontSize: '1.8rem', fontWeight: 700, color: '#3b82f6' }}>
                    {pendingFollowups}
                  </span>
                </div>
              </div>

              <div className="history-header">
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Recent Log Records</h3>
                <input
                  type="text"
                  placeholder="Search by HCP or product..."
                  className="search-bar"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ width: '280px', padding: '8px 14px', borderRadius: '30px' }}
                />
              </div>

              <div className="interactions-list">
                {filteredInteractions.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No interactions logged yet.
                  </div>
                ) : (
                  filteredInteractions.map((inter) => (
                    <div key={inter.id} className="interaction-card">
                      <div className="interaction-card-header">
                        <div className="hcp-info">
                          <span className="hcp-name-text">{inter.hcp ? inter.hcp.name : 'Unknown HCP'}</span>
                          <span className="hcp-specialty-text">{inter.hcp ? `${inter.hcp.specialty} — ${inter.hcp.address}` : ''}</span>
                        </div>
                        <div className="interaction-meta-top">
                          <span className={`badge badge-sentiment-${inter.sentiment?.toLowerCase() || 'neutral'}`}>
                            {inter.sentiment || 'Neutral'}
                          </span>
                          <span className="badge badge-manual" style={{ textTransform: 'uppercase' }}>
                            {inter.type}
                          </span>
                          <span className="interaction-date-text">
                            {new Date(inter.datetime).toLocaleDateString()} {new Date(inter.datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>

                      {inter.discussion_notes && (
                        <div className="notes-block">
                          <p style={{ opacity: 0.95 }}>{inter.discussion_notes}</p>
                        </div>
                      )}

                      {((inter.products && inter.products.length > 0) || (inter.samples && inter.samples.length > 0)) && (
                        <div className="products-discussed-block">
                          {inter.products && inter.products.map((p) => (
                            <span key={p.id} className="product-tag">{p.name}</span>
                          ))}
                          {inter.samples && inter.samples.map((s) => (
                            <span key={s.id} className="sample-tag">{s.product?.name || s.product_name} (x{s.quantity})</span>
                          ))}
                        </div>
                      )}

                      {inter.follow_up_required && (
                        <div style={{ background: 'rgba(59, 130, 246, 0.05)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', gap: '12px' }}>
                           <Calendar size={16} className="text-blue-400" />
                          <span style={{ fontSize: '0.85rem' }}>
                            <strong>Follow-up scheduled:</strong> {inter.follow_up_date ? new Date(inter.follow_up_date).toLocaleDateString() : 'TBD'} — {inter.follow_up_notes}
                          </span>
                        </div>
                      )}

                      <div className="audit-trail-section">
                        <button
                          type="button"
                          className="audit-trail-toggle"
                          onClick={() => handleToggleAudit(inter.id)}
                        >
                          <Info size={14} />
                          {expandedAudits[inter.id] ? 'Hide Audit History' : 'View Audit History'}
                        </button>

                        {expandedAudits[inter.id] && (
                          <div className="audit-timeline">
                            {auditLogs[inter.id] ? (
                              auditLogs[inter.id].map((log) => (
                                <div key={log.id} className="audit-item">
                                  <div className="audit-time">
                                    {new Date(log.timestamp).toLocaleString()} — Changed by {log.changed_by}
                                  </div>
                                  <div className="audit-desc">
                                    {log.action === 'CREATE' ? (
                                      <span>Record created</span>
                                    ) : (
                                      <span>
                                        Field <strong>{log.field_name}</strong> updated from "<em>{log.old_value || 'None'}</em>" to "<em>{log.new_value}</em>"
                                      </span>
                                    )}
                                  </div>
                                  <div className="audit-badge-row">
                                    <span className={`badge ${log.source === 'ai' ? 'badge-ai' : 'badge-manual'}`} style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                                      Source: {log.source.toUpperCase()}
                                    </span>
                                    {log.source === 'ai' && log.confidence_score && (
                                      <span style={{ fontSize: '0.65rem', color: 'var(--primary-color)', fontWeight: 600 }}>
                                        Confidence: {Math.round(log.confidence_score * 100)}%
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '8px' }}>
                                <RefreshCw size={12} className="animate-spin" /> Loading audit history...
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Toast Notification Container */}
        <div 
          style={{
            position: 'fixed',
            top: '24px',
            right: '24px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            maxWidth: '350px'
          }}
        >
          {toasts.map(t => (
            <div
              key={t.id}
              style={{
                padding: '14px 20px',
                backgroundColor: t.type === 'success' ? '#10b981' : t.type === 'error' ? '#ef4444' : '#3b82f6',
                color: '#ffffff',
                borderRadius: 'var(--rounded-md)',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                animation: 'slideIn 0.3s ease forwards',
                fontSize: '0.875rem',
                fontWeight: 500
              }}
            >
              <span>{t.message}</span>
              <button
                onClick={() => setToasts(prev => prev.filter(item => item.id !== t.id))}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#ffffff',
                  cursor: 'pointer',
                  opacity: 0.8,
                  fontSize: '1.2rem',
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
