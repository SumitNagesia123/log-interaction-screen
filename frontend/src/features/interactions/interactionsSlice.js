import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE = 'http://localhost:8000/api';

// Async Thunks
export const fetchHCPs = createAsyncThunk('interactions/fetchHCPs', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/hcps`);
    if (!response.ok) throw new Error('Failed to fetch HCPs');
    return await response.json();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const fetchProducts = createAsyncThunk('interactions/fetchProducts', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/products`);
    if (!response.ok) throw new Error('Failed to fetch products');
    return await response.json();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const fetchInteractions = createAsyncThunk('interactions/fetchInteractions', async (_, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/interactions`);
    if (!response.ok) throw new Error('Failed to fetch interactions');
    return await response.json();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const fetchAuditLogs = createAsyncThunk('interactions/fetchAuditLogs', async (id, { rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/interactions/${id}/audit`);
    if (!response.ok) throw new Error('Failed to fetch audit logs');
    return { id, logs: await response.json() };
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const saveInteraction = createAsyncThunk('interactions/saveInteraction', async ({ data, source, confidence }, { dispatch, rejectWithValue }) => {
  try {
    const url = new URL(`${API_BASE}/interactions`);
    if (source) url.searchParams.append('source', source);
    if (confidence !== undefined) url.searchParams.append('confidence', confidence.toString());

    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to save interaction');
    const saved = await response.json();
    dispatch(fetchInteractions());
    return saved;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const updateInteraction = createAsyncThunk('interactions/updateInteraction', async ({ id, data }, { dispatch, rejectWithValue }) => {
  try {
    const response = await fetch(`${API_BASE}/interactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update interaction');
    const updated = await response.json();
    dispatch(fetchInteractions());
    return updated;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const initialState = {
  hcps: [],
  products: [],
  interactions: [],
  auditLogs: {}, // key: interaction_id, value: array of audit logs
  activeTab: 'chat', // 'form' or 'chat'
  activeView: 'log', // 'log' or 'history'
  loading: false,
  error: null,
  currentFormState: {
    hcp_id: '',
    type: 'Visit',
    datetime: new Date().toISOString().substring(0, 16),
    discussion_notes: '',
    sentiment: 'Neutral',
    product_ids: [],
    samples: [], // [{product_id, quantity}]
    follow_up_required: false,
    follow_up_date: '',
    follow_up_notes: ''
  }
};

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    setTab: (state, action) => {
      state.activeTab = action.payload;
    },
    setView: (state, action) => {
      state.activeView = action.payload;
    },
    updateFormState: (state, action) => {
      state.currentFormState = { ...state.currentFormState, ...action.payload };
    },
    resetFormState: (state) => {
      state.currentFormState = initialState.currentFormState;
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch HCPs
      .addCase(fetchHCPs.pending, (state) => { state.loading = true; })
      .addCase(fetchHCPs.fulfilled, (state, action) => {
        state.loading = false;
        state.hcps = action.payload;
      })
      .addCase(fetchHCPs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Fetch Products
      .addCase(fetchProducts.fulfilled, (state, action) => {
        state.products = action.payload;
      })
      
      // Fetch Interactions
      .addCase(fetchInteractions.pending, (state) => { state.loading = true; })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false;
        state.interactions = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Fetch Audit Logs
      .addCase(fetchAuditLogs.fulfilled, (state, action) => {
        state.auditLogs[action.payload.id] = action.payload.logs;
      })

      // Save / Update Interaction
      .addCase(saveInteraction.pending, (state) => { state.loading = true; })
      .addCase(saveInteraction.fulfilled, (state) => {
        state.loading = false;
        state.currentFormState = initialState.currentFormState;
      })
      .addCase(saveInteraction.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const { setTab, setView, updateFormState, resetFormState } = interactionsSlice.actions;
export default interactionsSlice.reducer;
