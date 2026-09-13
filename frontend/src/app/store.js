import { configureStore } from '@reduxjs/toolkit';
import complaintReducer from '../features/complaint/complaintSlice';
import copilotReducer from '../features/copilot/copilotSlice';

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
    copilot: copilotReducer,
  },
  devTools: import.meta.env.DEV,
});
