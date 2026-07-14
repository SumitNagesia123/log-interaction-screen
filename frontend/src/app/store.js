import { configureStore } from '@reduxjs/toolkit';
import interactionsReducer from '../features/interactions/interactionsSlice';
import chatReducer from '../features/chat/chatSlice';

export const store = configureStore({
  reducer: {
    interactions: interactionsReducer,
    chat: chatReducer
  }
});
