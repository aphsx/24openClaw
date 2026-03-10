import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from './features/dashboard/DashboardPage';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  );
}

export default App;
