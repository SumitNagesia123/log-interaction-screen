import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE = 'http://localhost:8000/api';

// Async Thunks
export const sendChatMessage = createAsyncThunk('chat/sendChatMessage', async ({ message, history }, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });
    if (!response.ok) throw new Error('Failed to get chat response');
    return await response.json();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const confirmChatDraft = createAsyncThunk('chat/confirmChatDraft', async ({ previewCard, sessionId }, { dispatch, rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/chat/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId || 'default', preview_card: previewCard }),
    });
    if (!response.ok) throw new Error('Failed to confirm draft');
    const result = await response.json();
    
    // Dynamically import and refresh the interactions list
    const { fetchInteractions } = await import('../interactions/interactionsSlice');
    dispatch(fetchInteractions());
    
    return result;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const initialState = {
  chatHistory: [
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Hello! I'm your CRM assistant. You can log a new interaction by typing details like: 'Met Dr. Ananya Sharma today, discussed CardioX and gave 2 boxes.' or edit an existing one. How can I help you?",
      timestamp: new Date().toISOString()
    }
  ],
  chatLoading: false
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addChatMessage: (state, action) => {
      state.chatHistory.push(action.payload);
    },
    clearChatHistory: (state) => {
      state.chatHistory = initialState.chatHistory;
    }
  },
  extraReducers: (builder) => {
    builder
      // Send Chat Message
      .addCase(sendChatMessage.pending, (state) => {
        state.chatLoading = true;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatLoading = false;
        state.chatHistory.push({
          id: Date.now().toString(),
          sender: 'assistant',
          text: action.payload.response,
          preview_card: action.payload.preview_card,
          needs_disambiguation: action.payload.needs_disambiguation,
          disambiguation_options: action.payload.disambiguation_options,
          timestamp: new Date().toISOString()
        });
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatLoading = false;
        state.chatHistory.push({
          id: Date.now().toString(),
          sender: 'assistant',
          text: `Sorry, I encountered an error: ${action.payload || 'Failed to connect to backend.'}`,
          timestamp: new Date().toISOString()
        });
      })

      // Confirm Chat Draft
      .addCase(confirmChatDraft.pending, (state) => {
        state.chatLoading = true;
      })
      .addCase(confirmChatDraft.fulfilled, (state, action) => {
        state.chatLoading = false;
        state.chatHistory.push({
          id: Date.now().toString(),
          sender: 'assistant',
          text: action.payload.response,
          timestamp: new Date().toISOString()
        });
      })
      .addCase(confirmChatDraft.rejected, (state, action) => {
        state.chatLoading = false;
        state.chatHistory.push({
          id: Date.now().toString(),
          sender: 'assistant',
          text: `Failed to confirm draft: ${action.payload || 'Unknown error.'}`,
          timestamp: new Date().toISOString()
        });
      });
  }
});

export const { addChatMessage, clearChatHistory } = chatSlice.actions;
export default chatSlice.reducer;
